import unittest

from pydantic import ValidationError

from intent_detection.intent_detector_agent import (
    IntentDecision,
    IntentName,
    intent_detector_agent,
    parse_intent_decision,
)


class IntentDecisionTests(unittest.TestCase):
    def test_detector_has_fixed_schema(self):
        self.assertEqual(intent_detector_agent.output_schema, IntentDecision)
        self.assertEqual(
            set(IntentDecision.model_fields),
            {"intent", "confidence", "rationale"},
        )

    def test_valid_loan_closure_decision_is_preserved(self):
        result = parse_intent_decision(
            '{"intent":"loan_closure","confidence":0.96,'
            '"rationale":"User explicitly asks to close a loan."}'
        )
        self.assertEqual(result.intent, IntentName.LOAN_CLOSURE)
        self.assertEqual(result.confidence, 0.96)

    def test_low_confidence_fails_closed(self):
        result = parse_intent_decision(
            {
                "intent": "loan_closure",
                "confidence": 0.51,
                "rationale": "The request may be a follow-up.",
            }
        )
        self.assertEqual(result.intent, IntentName.NEEDS_CLARIFICATION)
        self.assertEqual(result.confidence, 0.0)

    def test_malformed_json_fails_closed(self):
        result = parse_intent_decision("not-json")
        self.assertEqual(result.intent, IntentName.NEEDS_CLARIFICATION)

    def test_unknown_intent_or_out_of_range_confidence_fails_closed(self):
        for payload in (
            {"intent": "close_everything", "confidence": 0.99, "rationale": "bad label"},
            {"intent": "loan_closure", "confidence": 1.4, "rationale": "bad score"},
            {"intent": "unsupported", "confidence": 0.9},
        ):
            with self.subTest(payload=payload):
                result = parse_intent_decision(payload)
                self.assertEqual(result.intent, IntentName.NEEDS_CLARIFICATION)

    def test_schema_rejects_extra_fields(self):
        with self.assertRaises(ValidationError):
            IntentDecision.model_validate(
                {
                    "intent": "loan_closure",
                    "confidence": 0.9,
                    "rationale": "Explicit closure request.",
                    "execute": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
