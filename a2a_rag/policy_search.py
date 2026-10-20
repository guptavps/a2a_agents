import json
import subprocess
from typing import Any

import httpx
from google.adk.tools import FunctionTool, VertexAiSearchTool
from google.auth import default
from google.auth.transport.requests import Request

from embedding_service import VertexEmbeddingService
from rag_config import RagSettings, load_settings


def _get_access_token() -> str:
    try:
        credentials, _ = default()
        if credentials is None:
            raise RuntimeError("No Google ADC credentials configured")
        credentials.refresh(Request())
        return credentials.token
    except Exception:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


def _normalize_index_name(settings: RagSettings, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Vertex AI index ID is required for live vector search.")
    if cleaned.startswith("projects/"):
        return cleaned
    return f"projects/{settings.project_id}/locations/{settings.location}/indexes/{cleaned}"


def _extract_neighbors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("nearestNeighbors", "nearest_neighbor", "neighbors", "nearest_neighbours"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    for value in payload.values():
        if isinstance(value, dict):
            nested = _extract_neighbors(value)
            if nested:
                return nested
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = _extract_neighbors(item)
                    if nested:
                        return nested
    return []


def search_policy_index(question: str, max_results: int | None = None) -> str:
    """Search the live Vertex AI vector index for the most relevant loan policy passages."""
    settings = load_settings()
    if not settings.index_id:
        raise ValueError("VERTEX_INDEX_ID is required to search the live loan policy vector index.")

    index_name = _normalize_index_name(settings, settings.index_id)
    if not settings.index_endpoint_id:
        raise ValueError("VERTEX_INDEX_ENDPOINT_ID is required to search the live loan policy vector index.")
    endpoint_name = settings.index_endpoint_id
    if not endpoint_name.startswith("projects/"):
        endpoint_name = (
            f"projects/{settings.project_id}/locations/{settings.location}/"
            f"indexEndpoints/{endpoint_name}"
        )
    query_embedding = VertexEmbeddingService(settings).embed([question])[0]
    request_payload = {
        "deployedIndexId": os.getenv("VERTEX_DEPLOYED_INDEX_ID", "loan_policy_stream_deployed"),
        "queries": [
            {
                "datapoint": {"featureVector": query_embedding},
                "neighborCount": max_results or settings.max_results,
            }
        ]
    }
    response = httpx.post(
        f"https://{settings.index_endpoint_domain or f'{settings.location}-aiplatform.googleapis.com'}"
        f"/v1/{endpoint_name}:findNeighbors",
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Content-Type": "application/json; charset=utf-8",
        },
        content=json.dumps(request_payload),
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()

    neighbors = _extract_neighbors(payload)
    if not neighbors:
        return "No policy passages matched the question."

    snippets: list[str] = []
    for item in neighbors:
        candidate = item
        if isinstance(item, dict):
            nested = item.get("neighbor") if isinstance(item.get("neighbor"), dict) else item
            datapoint = nested.get("datapoint", {}) if isinstance(nested, dict) else {}
            metadata = datapoint.get("metadata", {}) if isinstance(datapoint, dict) else {}
            source = metadata.get("source_uri") or metadata.get("source") or "loan policy document"
            text = (
                metadata.get("text")
                or metadata.get("chunk_text")
                or metadata.get("content")
                or metadata.get("page_content")
                or ""
            )
            if not text:
                text = str(metadata) if metadata else ""
            if text:
                snippets.append(f"[{source}] {text[:1800]}")

    if not snippets:
        return json.dumps(payload, ensure_ascii=False)[:4000]
    return "\n\n".join(snippets)


def build_policy_search_tool(settings: RagSettings | None = None) -> VertexAiSearchTool:
    resolved_settings = settings or load_settings()
    if resolved_settings.index_id:
        return FunctionTool(func=search_policy_index)
    if resolved_settings.data_store_id:
        return VertexAiSearchTool(
            data_store_id=resolved_settings.data_store_id,
            max_results=resolved_settings.max_results,
        )
    return VertexAiSearchTool(
        data_store_id=resolved_settings.data_store_id,
        max_results=resolved_settings.max_results,
    )
