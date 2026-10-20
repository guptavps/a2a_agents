import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from pipeline_config import PipelineConfig, load_pipeline_config
from query_vector_search import query_vector_search


def policy_agent_instruction(ctx) -> str:
    return (
        "You are a loan policy question-answering agent. "
        "Use the search_loan_policy tool for every loan-policy question. "
        "Answer only from the retrieved policy passages. "
        "Cite the page number for each material policy statement. "
        "If the passages do not support an answer, say that clearly. "
        "Do not add recommendations, assumptions, or general advice that is not in the passages. "
        "Do not invent requirements, deadlines, fees, or exceptions."
    )


def search_loan_policy(question: str) -> str:
    """Find relevant loan-policy passages in the configured Vector Search index."""
    results = query_vector_search(question)
    if not results:
        return "No matching policy passages were retrieved."
    return "\n\n".join(
        f"Source: {result['source_uri']} page {result['page_number']} "
        f"(chunk {result['chunk_id']})\n{result['text']}"
        for result in results
    )


def build_policy_agent(config: PipelineConfig | None = None) -> Agent:
    resolved_config = config or load_pipeline_config()
    return Agent(
        name="loan_policy_vertex_agent",
        model=os.getenv("LOAN_POLICY_MODEL", resolved_config.gemini.model),
        description="Answers loan servicing policy questions using Vertex AI Vector Search.",
        instruction=policy_agent_instruction,
        tools=[FunctionTool(func=search_loan_policy)],
    )
