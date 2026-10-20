import os

from google.adk.agents import Agent

from policy_search import build_policy_search_tool
from rag_config import RagSettings

def policy_agent_instruction(ctx) -> str:
    return (
        "You are a loan policy question-answering agent. "
        "Use the loan policy search tool for every policy question. "
        "Answer only from retrieved policy documents and clearly state when the documents do not contain enough information. "
        "Include the relevant policy source or citation when the search result provides one. "
        "Do not invent requirements, deadlines, fees, or exceptions."
    )


def build_policy_agent(settings: RagSettings) -> Agent:
    return Agent(
        name="loan_policy_agent",
        model=os.getenv("LOAN_POLICY_MODEL", "gemini-2.5-flash"),
        description="Answers loan servicing policy questions using indexed policy documents.",
        instruction=policy_agent_instruction,
        tools=[build_policy_search_tool(settings)],
    )
