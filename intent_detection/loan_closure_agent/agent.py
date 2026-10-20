import logging
import os
import sys
import warnings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,
)

# Must run before ADK imports so its experimental-feature warnings are hidden from the logs.
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]", category=UserWarning)

from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent, LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.genai import types
from mcp import StdioServerParameters
from pydantic import BaseModel, Field

from .agent_card import build_agent_card

load_dotenv()
logger = logging.getLogger(__name__)

APP_NAME = "loan_closure_agent_app"
MODEL = os.getenv("LOAN_CLOSURE_MODEL", "gemini-3.8-flash")
PORT = int(os.getenv("LOAN_CLOSURE_AGENT_PORT", "8090"))
MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")


class LoanIdExtractionResult(BaseModel):
    loan_id: str | None = Field(
        default=None,
        description="The loan identifier extracted from the prompt, or null if not found.",
    )
    missing: bool = Field(
        default=False,
        description="True when the prompt does not contain a loan ID.",
    )


loan_id_extractor_agent = LlmAgent(
    name="loan_id_extractor",
    model=MODEL,
    instruction=(
        "Extract the loan ID from the user's prompt. Return only the required structured "
        "fields. Set loan_id to null and missing to true if no loan ID is present."
    ),
    output_schema=LoanIdExtractionResult,
)


async def _extract_loan_id_async(prompt: str) -> LoanIdExtractionResult:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=loan_id_extractor_agent,
        app_name="loan_id_extractor_app",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="loan_id_extractor_app",
        user_id="loan_id_extractor",
    )
    response_text = ""
    async for event in runner.run_async(
        user_id="loan_id_extractor",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Extract the loan ID from this prompt:\n\n{prompt}")],
        ),
    ):
        for part in getattr(getattr(event, "content", None), "parts", []) or []:
            if getattr(part, "text", None):
                response_text += part.text

    if not response_text.strip():
        return LoanIdExtractionResult(loan_id=None, missing=True)
    try:
        result = LoanIdExtractionResult.model_validate_json(response_text)
        logger.info(
            "Loan ID extraction completed; identifier_present=%s",
            bool(result.loan_id),
        )
        return result
    except Exception:
        logger.warning("Loan ID extraction returned an invalid structured response")
        return LoanIdExtractionResult(loan_id=None, missing=True)


async def extract_loan_id(prompt: str) -> LoanIdExtractionResult:
    """Extract a loan ID with the fixed structured response schema."""
    logger.info("Starting loan ID extraction")
    return await _extract_loan_id_async(prompt)


def loan_agent_instruction(context: ReadonlyContext) -> str:
    return (
        "For a loan closure request, call extract_loan_id first. If missing is true, ask for "
        "the loan ID. Otherwise call close_loan using the extracted ID. Confirm success only "
        "when the tool returns status exactly 'success'. Never claim a result without a tool "
        "response."
    )


def before_tool_callback(tool, args, tool_context=None, **kwargs):
    if tool_context and getattr(tool, "name", "") == "close_loan":
        logger.info("Starting close_loan tool call")
        tool_context.state["loan_app_id"] = args.get("loan_app_id")
        tool_context.state["last_action"] = "close_loan_requested"


def after_tool_callback(tool, args, tool_context=None, result=None, **kwargs):
    if tool_context and getattr(tool, "name", "") == "close_loan":
        payload = result or {}
        structured = payload.get("structured_content", {})
        tool_context.state["close_loan_status"] = structured.get("status")
        tool_context.state["close_loan_message"] = structured.get("message")
        tool_context.state["last_action"] = "close_loan_completed"
        logger.info(
            "close_loan tool call completed; status=%s",
            structured.get("status", "unknown"),
        )


mcp_toolset = McpToolset(
    errlog=sys.stderr,
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[MCP_SERVER_PATH],
            env=os.environ.copy(),
        )
    ),
)

root_agent = Agent(
    name="loan_closure_agent",
    model=MODEL,
    description="Agent that extracts a loan ID and invokes the MCP loan-closure tool.",
    instruction=loan_agent_instruction,
    tools=[FunctionTool(extract_loan_id), mcp_toolset],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)

app = App(name=APP_NAME, root_agent=root_agent)


def _create_session_service():
    agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
    if not agent_engine_id:
        return InMemorySessionService()

    from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService

    return VertexAiSessionService(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-central1"),
        agent_engine_id=agent_engine_id,
    )


agent_card = build_agent_card(
    name=root_agent.name,
    description=root_agent.description,
    port=PORT,
)

runner = Runner(
    app=app,
    session_service=_create_session_service(),
    artifact_service=InMemoryArtifactService(),
)
a2a_app = to_a2a(
    root_agent,
    host="0.0.0.0",
    port=PORT,
    runner=runner,
    protocol="http",
    agent_card=agent_card,
)


def main() -> None:
    import uvicorn

    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
