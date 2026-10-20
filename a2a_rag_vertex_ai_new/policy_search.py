from google.adk.tools import VertexAiSearchTool

from rag_config import RagSettings, load_settings


def build_policy_search_tool(settings: RagSettings | None = None) -> VertexAiSearchTool:
    resolved_settings = settings or load_settings()
    return VertexAiSearchTool(
        data_store_id=resolved_settings.data_store_id,
        max_results=resolved_settings.max_results,
    )
