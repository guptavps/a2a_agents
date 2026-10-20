import os
import sys

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.agents.readonly_context import ReadonlyContext

load_dotenv()

USER_ID="user_1"
APP_NAME="loan_closure_agent_app"
MODEL = os.getenv("LOAN_CLOSURE_MODEL", "gemini-3.6-flash")

def loan_agent_instruction(ctx: ReadonlyContext) -> str:
    loan_app_id=ctx.state.get("loan_app_id")
    last_status=ctx.state.get("close_loan_status")
    return("You are a loan servicing agent with tool access. For loan closure requests you must call "
    "close_loan first and use the tool result. If tool status is exactly success, confirm closure succeeded. "
    " Otherwise say closure failed."
    " Never claim success or failure without a tool response. " 
    f"Loan Application ID: {loan_app_id}, Close Loan Status: {last_status} ")

def before_tool_callback(tool, args, context=None, tool_context=None, **kwargs):
    active_context=context or tool_context
    if active_context is None:
        return
    if getattr(tool, "name", "") == "close_loan":
        active_context.state["last_action"] = "close_loan_requested"
        active_context.state["loan_app_id"] = args.get("loan_app_id")

def after_tool_callback(tool, args, context=None, tool_context=None, result=None, tool_response=None, **kwargs):
    active_context=context or tool_context
    payload = result or tool_response or {}
    if active_context is None:
        return
    if getattr(tool, "name", "") == "close_loan":
        structured_content = payload.get("structured_content", {})
        active_context.state["close_loan_status"] = structured_content.get("status")
        active_context.state["close_loan_message"] = structured_content.get("message")
        active_context.state["last_action"] = "close_loan_completed"



def build_loan_closure_agent() -> Agent:
    mcp_tool_set = McpToolset(
        errlog=sys.stderr,
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", "tool"],
            )
        )
    )

    # Initialize and configure the loan closure agent here
    agent = Agent(
        name="loan_closure_agent",
        model=MODEL,
        description="Agent responsible for handling loan closure processes.",
        instruction=loan_agent_instruction,
        tools=[mcp_tool_set],
        before_tool_callback=before_tool_callback,
        after_tool_callback=after_tool_callback)
    # Add necessary setup for the agent 
    return agent

loan_closure_agent = build_loan_closure_agent()




