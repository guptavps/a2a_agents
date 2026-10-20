import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class RagSettings:
    project_id: str
    data_store_id: str = ""
    index_id: str = ""
    index_endpoint_id: str = ""
    index_endpoint_domain: str = ""
    max_results: int = 5
    location: str = "global"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768


def _load_yaml_config(path: str | Path) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as config_file:
        parsed = yaml.safe_load(config_file) or {}

    if not isinstance(parsed, dict):
        raise ValueError(f"RAG config file must contain a mapping: {config_path}")
    return parsed


def load_settings() -> RagSettings:
    load_dotenv()

    config_path = os.getenv("RAG_CONFIG_PATH")
    yaml_config: dict = {}
    if config_path:
        yaml_config = _load_yaml_config(config_path)
    else:
        default_config = Path(__file__).with_name("rag_config.yaml")
        if default_config.exists():
            yaml_config = _load_yaml_config(default_config)

    project_id = (
        os.getenv("GOOGLE_CLOUD_PROJECT")
        or str(yaml_config.get("project_id") or yaml_config.get("project") or "")
    ).strip()
    data_store_id = (
        os.getenv("VERTEX_AI_SEARCH_DATA_STORE_ID")
        or str(yaml_config.get("data_store_id") or yaml_config.get("datastore_id") or "")
    ).strip()
    index_id = (
        os.getenv("VERTEX_INDEX_ID")
        or os.getenv("VERTEX_VECTOR_INDEX_ID")
        or os.getenv("VERTEX_AI_INDEX_ID")
        or str(
            yaml_config.get("index_id")
            or yaml_config.get("index")
            or yaml_config.get("vector_index_id")
            or yaml_config.get("vertex_index_id")
            or ""
        )
    ).strip()
    index_endpoint_id = (
        os.getenv("VERTEX_INDEX_ENDPOINT_ID")
        or os.getenv("VERTEX_VECTOR_INDEX_ENDPOINT_ID")
        or os.getenv("VERTEX_AI_INDEX_ENDPOINT_ID")
        or str(
            yaml_config.get("index_endpoint_id")
            or yaml_config.get("endpoint_id")
            or yaml_config.get("vector_index_endpoint_id")
            or yaml_config.get("vertex_index_endpoint_id")
            or ""
        )
    ).strip()
    index_endpoint_domain = (
        os.getenv("VERTEX_INDEX_ENDPOINT_DOMAIN")
        or str(yaml_config.get("index_endpoint_domain") or "")
    ).strip()
    max_results_text = (
        os.getenv("LOAN_POLICY_SEARCH_MAX_RESULTS")
        or str(yaml_config.get("max_results") or "5")
    ).strip()
    location = (
        os.getenv("GOOGLE_CLOUD_LOCATION")
        or str(yaml_config.get("location") or yaml_config.get("region") or "global")
    ).strip()
    embedding_model = (
        os.getenv("RAG_EMBEDDING_MODEL")
        or str(yaml_config.get("embedding_model") or "gemini-embedding-001")
    ).strip()
    dimensions_text = (
        os.getenv("RAG_EMBEDDING_DIMENSIONS")
        or str(yaml_config.get("embedding_dimensions") or "768")
    ).strip()

    missing = []
    if not project_id:
        missing.append("GOOGLE_CLOUD_PROJECT")
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")

    try:
        max_results = int(max_results_text)
    except ValueError as exc:
        raise ValueError("LOAN_POLICY_SEARCH_MAX_RESULTS must be an integer") from exc
    if max_results < 1:
        raise ValueError("LOAN_POLICY_SEARCH_MAX_RESULTS must be greater than zero")
    try:
        embedding_dimensions = int(dimensions_text)
    except ValueError as exc:
        raise ValueError("RAG_EMBEDDING_DIMENSIONS must be an integer") from exc
    if embedding_dimensions < 1:
        raise ValueError("RAG_EMBEDDING_DIMENSIONS must be greater than zero")

    return RagSettings(
        project_id=project_id,
        data_store_id=data_store_id,
        index_id=index_id,
        index_endpoint_id=index_endpoint_id,
        index_endpoint_domain=index_endpoint_domain,
        max_results=max_results,
        location=location,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
    )
