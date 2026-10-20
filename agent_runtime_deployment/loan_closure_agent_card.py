import os

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


def _public_agent_url(port: int) -> str:
    if app_url := os.getenv("APP_URL"):
        return app_url.rstrip("/") + "/"

    agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-central1")
    if agent_engine_id and project:
        return (
            f"https://{location}-aiplatform.googleapis.com/reasoningEngines/v1"
            f"/projects/{project}/locations/{location}"
            f"/reasoningEngines/{agent_engine_id}/api/"
        )
    return f"http://127.0.0.1:{port}/"


def build_agent_card(*, name: str, description: str, port: int) -> AgentCard:
    """Build the A2A card for local use or an Agent Runtime deployment."""
    public_url = _public_agent_url(port)
    return AgentCard(
        name=name,
        description=description,
        supported_interfaces=[
            AgentInterface(
                url=public_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            ),
            AgentInterface(
                url=public_url,
                protocol_binding="JSONRPC",
                protocol_version="0.3",
            ),
        ],
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="loan-closure",
                name="Loan closure",
                description="Extract a loan ID and close the loan through the MCP tool.",
                tags=["loan", "closure"],
            )
        ],
    )
