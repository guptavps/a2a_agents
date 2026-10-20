import os
from enum import Enum
from typing import Any

from google.adk.agents import LlmAgent
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class IntentName(str, Enum):
    LOAN_CLOSURE = "loan_closure"
    UNSUPPORTED = "unsupported"
    NEEDS_CLARIFICATION = "needs_clarification"


class IntentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: IntentName = Field(
        description="The single best-supported intent from the allowed intent values."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the classification, from 0.0 through 1.0.",
    )
    rationale: str = Field(
        description="A brief explanation grounded in the user's request and conversation context."
    )


INTENT_DETECTION_MODEL = os.getenv(
    "INTENT_DETECTION_MODEL",
    os.getenv("LOAN_CLOSURE_MODEL", "gemini-3.8-flash"),
)
MIN_ROUTING_CONFIDENCE = 0.75

IntentDetectorAgent = LlmAgent

intent_detector_agent = LlmAgent(
    name="intent_detector_agent",
    model=INTENT_DETECTION_MODEL,
    description="Classifies a user's request before any domain agent is invoked.",
    output_key="intent_decision",
    instruction=(
        "Classify the user's current request using the conversation context available to you. "
        "Return exactly one structured decision using the required schema. Choose loan_closure "
        "only when the current request clearly asks to close a loan or is an unambiguous follow-up "
        "to an established loan-closure request. Choose unsupported when the user clearly requests "
        "another task. Choose needs_clarification when the intent or required context is ambiguous. "
        "Never execute tools, claim a loan was changed, or infer missing facts. A prior topic alone "
        "does not make a new unrelated request a loan-closure request."
    ),
    output_schema=IntentDecision,
)


def _clarification_decision(reason: str) -> IntentDecision:
    return IntentDecision(
        intent=IntentName.NEEDS_CLARIFICATION,
        confidence=0.0,
        rationale=reason,
    )


def parse_intent_decision(
    value: Any,
    *,
    minimum_confidence: float = MIN_ROUTING_CONFIDENCE,
) -> IntentDecision:
    """Validate classifier output; fail closed to clarification on bad/weak output."""
    try:
        if isinstance(value, IntentDecision):
            decision = value
        elif isinstance(value, str):
            decision = IntentDecision.model_validate_json(value)
        else:
            decision = IntentDecision.model_validate(value)
    except (ValidationError, ValueError, TypeError):
        return _clarification_decision("Intent output was missing or invalid.")

    if decision.confidence < minimum_confidence:
        return _clarification_decision(
            "Intent confidence is below the safe routing threshold. "
            f"Classifier rationale: {decision.rationale}"
        )
    return decision
