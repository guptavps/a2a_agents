import os
import logging

from google.adk.a2a.agent import A2aRemoteAgentConfig, RemoteA2aAgent
from google.adk.agents.context import Context
from google.adk.workflow import START, FunctionNode, Workflow
from google.adk.events import Event
from google.genai import types

from intent_detection.intent_detector_agent import (
    IntentName,
    intent_detector_agent,
    parse_intent_decision,
)

LOAN_CLOSURE_AGENT_NAME = "loan_closure_remote_agent"
LOAN_CLOSURE_AGENT_URL = os.getenv(
    "LOAN_CLOSURE_AGENT_CARD_URL",
    f"{os.getenv('LOAN_CLOSURE_AGENT_URL', 'http://localhost:8090').rstrip('/')}/.well-known/agent-card.json",
)
logger = logging.getLogger(__name__)


def route_intent(ctx: Context) -> Event:
    decision = _decision_from_state(ctx)
    logger.info(
        "%s: validated intent decision: %s",
        route_intent.__name__,
        decision.model_dump(mode="json"),
    )
    return Event(
        author="route_intent",
        route=decision.intent.value,
        output=decision.model_dump(mode="json"),
    )


def build_loan_closure_context(ctx, agent_name, part_converter):
    log_source = f"{os.path.basename(__file__)}:{build_loan_closure_context.__name__}"
    decision = parse_intent_decision(ctx.session.state.get("intent_decision"))
    events = list(ctx.session.events)
    logger.info(
        "%s: preparing remote context for intent=%s across %d session events",
        log_source,
        decision.intent.value,
        len(events),
    )
    last_handoff_index = max(
        (
            index
            for index, event in enumerate(events)
            if event.author == LOAN_CLOSURE_AGENT_NAME
        ),
        default=-1,
    )
    logger.info(
        "%s: last remote-agent event index=%d",
        log_source,
        last_handoff_index,
    )

    user_turns = [
        text
        for event in events[last_handoff_index + 1 :]
        if event.author == "user"
        if (text := _event_text(event))
    ]
    current_request = _content_text(ctx.user_content)
    if current_request and (not user_turns or user_turns[-1] != current_request):
        user_turns.append(current_request)
    logger.info(
        "%s: collected %d user turns; current request available=%s",
        log_source,
        len(user_turns),
        bool(current_request),
    )
    logger.info("%s: user_turns=%s", log_source, user_turns)

    conversation = "\n".join(
        f"User: {text}" for text in user_turns
    ) or "No user message was available in the workflow session."
    prompt = (
        "Handle the delegated loan-closure request using the conversation and "
        "validated workflow decision below. Extract the loan ID from the "
        "current request and use the loan-closure tool only when the required "
        "loan ID is present.\n\n"
        f"Workflow conversation since the previous handoff:\n{conversation}\n\n"
        f"Validated workflow decision: {decision.model_dump_json()}"
    )
    converted = part_converter(types.Part(text=prompt))
    if isinstance(converted, list):
        message_parts = converted
    elif converted is None:
        message_parts = []
    else:
        message_parts = [converted]
    logger.debug(
        "%s: prepared %d A2A message parts",
        log_source,
        len(message_parts),
    )
    return message_parts, None


def _content_text(content) -> str:
    if content is None:
        return ""
    return "\n".join(
        part.text for part in content.parts or [] if getattr(part, "text", None)
    ).strip()


def _event_text(event) -> str:
    return _content_text(event.content)


def unsupported_response(ctx: Context) -> Event:
    decision = _decision_from_state(ctx)
    return _final_response(
        author="unsupported_response",
        intent=IntentName.UNSUPPORTED,
        decision=decision,
        text="I can only route loan-closure requests right now.",
    )


def clarification_response(ctx: Context) -> Event:
    decision = _decision_from_state(ctx)
    return _final_response(
        author="clarification_response",
        intent=IntentName.NEEDS_CLARIFICATION,
        decision=decision,
        text="Could you clarify whether you want to close a loan?",
    )


def _decision_from_state(ctx: Context):
    decision = parse_intent_decision(ctx.state.get("intent_decision"))
    ctx.state["intent_decision"] = decision.model_dump(mode="json")
    return decision


def _final_response(*, author: str, intent: IntentName, decision, text: str) -> Event:
    rendered_text = (
        f"Intent: {decision.intent.value} (confidence {decision.confidence:.2f}). "
        f"Rationale: {decision.rationale}\n\n{text}"
    )
    return Event(
        author=author,
        content=types.Content(
            role="model",
            parts=[types.Part(text=rendered_text)],
        ),
        output={
            "intent": intent.value,
            "response": text,
            "decision": decision.model_dump(mode="json"),
        },
        turn_complete=True,
    )


intent_router_node = FunctionNode(func=route_intent, name="route_intent")
loan_closure_agent_node = RemoteA2aAgent(
    name=LOAN_CLOSURE_AGENT_NAME,
    description="Executes validated loan-closure requests through the loan-closure A2A agent.",
    agent_card=LOAN_CLOSURE_AGENT_URL,
    context_builder=build_loan_closure_context,
    config=A2aRemoteAgentConfig(forward_session_id_as_context_id=True),
)
unsupported_response_node = FunctionNode(func=unsupported_response)
clarification_response_node = FunctionNode(func=clarification_response)

intent_routing_workflow = Workflow(
    name="intent_routing_workflow",
    description="Classifies a request and routes it to a safe intent-specific outcome.",
    edges=[
        (START, intent_detector_agent, intent_router_node),
        (
            intent_router_node,
            {
                IntentName.LOAN_CLOSURE.value: loan_closure_agent_node,
                IntentName.UNSUPPORTED.value: unsupported_response_node,
                IntentName.NEEDS_CLARIFICATION.value: clarification_response_node,
            },
        ),
    ],
)
