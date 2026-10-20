import unittest
from types import SimpleNamespace

from google.genai import types

from intent_detection.intent_detector_agent import IntentName
from intent_detection.intent_routing_workflow import (
    LOAN_CLOSURE_AGENT_NAME,
    build_loan_closure_context,
    clarification_response,
    intent_routing_workflow,
    loan_closure_agent_node,
    route_intent,
    unsupported_response,
)


class IntentRoutingWorkflowTests(unittest.TestCase):
    def test_loan_closure_route_targets_remote_a2a_agent(self):
        context = SimpleNamespace(
            state={
                "intent_decision": {
                    "intent": IntentName.LOAN_CLOSURE.value,
                    "confidence": 0.96,
                    "rationale": "The user clearly asked to close a loan.",
                }
            }
        )

        route_event = route_intent(context)

        self.assertEqual(route_event.author, "route_intent")
        self.assertEqual(route_event.actions.route, IntentName.LOAN_CLOSURE.value)
        self.assertEqual(
            intent_routing_workflow.graph.get_next_pending_nodes(
                "route_intent", route_event.actions.route
            ),
            [LOAN_CLOSURE_AGENT_NAME],
        )
        self.assertTrue(
            loan_closure_agent_node._config.forward_session_id_as_context_id
        )

    def test_remote_agent_receives_recent_user_context_and_intent_decision(self):
        decision = {
            "intent": IntentName.LOAN_CLOSURE.value,
            "confidence": 0.96,
            "rationale": "The user asked to close their loan.",
        }
        context = SimpleNamespace(
            session=SimpleNamespace(
                id="workflow-session-123",
                state={"intent_decision": decision},
                events=[
                    SimpleNamespace(
                        author="user",
                        content=types.Content(
                            role="user",
                            parts=[types.Part(text="Please close loan LN-123.")],
                        ),
                    ),
                    SimpleNamespace(
                        author="intent_detector_agent",
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="internal classifier output")],
                        ),
                    ),
                ],
            ),
            user_content=types.Content(
                role="user",
                parts=[types.Part(text="Please close loan LN-123.")],
            ),
        )

        parts, context_id = build_loan_closure_context(
            context, LOAN_CLOSURE_AGENT_NAME, lambda part: part.text
        )

        self.assertIsNone(context_id)
        self.assertEqual(len(parts), 1)
        self.assertIn("Please close loan LN-123.", parts[0])
        self.assertIn('"intent":"loan_closure"', parts[0])
        self.assertNotIn("internal classifier output", parts[0])

    def test_unsupported_intent_routes_to_safe_response(self):
        context = SimpleNamespace(
            state={
                "intent_decision": {
                    "intent": IntentName.UNSUPPORTED.value,
                    "confidence": 0.91,
                    "rationale": "The request is unrelated to loan closure.",
                }
            }
        )

        route_event = route_intent(context)
        response_event = unsupported_response(context)

        self.assertEqual(route_event.actions.route, IntentName.UNSUPPORTED.value)
        self.assertEqual(
            intent_routing_workflow.graph.get_next_pending_nodes(
                "route_intent", route_event.actions.route
            ),
            ["unsupported_response"],
        )
        self.assertTrue(response_event.turn_complete)
        self.assertIn("only route loan-closure", response_event.content.parts[0].text)

    def test_low_confidence_or_invalid_decision_routes_to_clarification(self):
        context = SimpleNamespace(
            state={
                "intent_decision": {
                    "intent": IntentName.LOAN_CLOSURE.value,
                    "confidence": 0.2,
                    "rationale": "Weak evidence.",
                }
            }
        )

        route_event = route_intent(context)
        response_event = clarification_response(context)

        self.assertEqual(
            route_event.actions.route,
            IntentName.NEEDS_CLARIFICATION.value,
        )
        self.assertEqual(
            intent_routing_workflow.graph.get_next_pending_nodes(
                "route_intent", route_event.actions.route
            ),
            ["clarification_response"],
        )
        self.assertEqual(
            context.state["intent_decision"]["intent"],
            IntentName.NEEDS_CLARIFICATION.value,
        )
        self.assertTrue(response_event.turn_complete)
        self.assertIn("clarify", response_event.content.parts[0].text)


if __name__ == "__main__":
    unittest.main()
