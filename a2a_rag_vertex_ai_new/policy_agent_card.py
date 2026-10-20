import os

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


def build_agent_card() -> AgentCard:
    port = int(os.getenv("A2A_RAG_PORT", "8090"))
    url = os.getenv("A2A_RAG_URL", f"http://localhost:{port}")
    return AgentCard(
        name="loan_policy_vertex_agent",
        description="Answers loan policy questions using Vertex AI Search.",
        supported_interfaces=[
            AgentInterface(
                url=url,
                protocol_binding="HTTP+JSON",
                protocol_version="1.0",
            )
        ],
        version="1.0.0",
        capabilities=AgentCapabilities(),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="loan_policy_search",
                name="Search loan policies",
                description="Finds policy requirements and procedures in Vertex AI Search documents.",
                tags=["loan policy", "servicing", "compliance"],
                examples=[
                    "What documents are required to close a loan?",
                    "What is the policy for a prepayment request?",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            )
        ],
    )
