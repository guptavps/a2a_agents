from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class VectorSearchConfig:
    index_display_name: str
    index_dimensions: int
    distance_measure: str
    approximate_neighbors_count: int
    shard_size: str
    leaf_node_embedding_count: int
    endpoint_display_name: str
    public_endpoint_enabled: bool
    deployed_index_id: str
    retrieval_neighbors: int
    min_replica_count: int
    max_replica_count: int


@dataclass(frozen=True)
class RagConfig:
    corpus_display_name: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int


@dataclass(frozen=True)
class GeminiConfig:
    model: str
    temperature: float
    max_output_tokens: int


@dataclass(frozen=True)
class GcsConfig:
    bucket_uri: str
    object_name: str
    manifest_object_name: str
    overwrite_existing: bool


@dataclass(frozen=True)
class PipelineConfig:
    project_id: str
    region: str
    staging_bucket: str
    gcs: GcsConfig
    vector_search: VectorSearchConfig
    rag: RagConfig
    gemini: GeminiConfig


def _require(mapping: dict[str, Any], key: str, section: str) -> Any:
    value = mapping.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required configuration: {section}.{key}")
    return value


def load_pipeline_config(path: str | Path = "pipeline_config.yaml") -> PipelineConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file) or {}

    if not isinstance(raw, dict):
        raise ValueError("Pipeline configuration must contain a YAML mapping")

    vector_raw = _require(raw, "vector_search", "root")
    gcs_raw = _require(raw, "gcs", "root")
    rag_raw = _require(raw, "rag", "root")
    gemini_raw = _require(raw, "gemini", "root")
    if not all(isinstance(section, dict) for section in (vector_raw, gcs_raw, rag_raw, gemini_raw)):
        raise ValueError("gcs, vector_search, rag, and gemini must be YAML mappings")

    chunk_size = int(_require(rag_raw, "chunk_size", "rag"))
    chunk_overlap = int(_require(rag_raw, "chunk_overlap", "rag"))
    if chunk_size < 1 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("rag.chunk_overlap must be non-negative and smaller than rag.chunk_size")

    return PipelineConfig(
        project_id=str(_require(raw, "project_id", "root")),
        region=str(_require(raw, "region", "root")),
        staging_bucket=str(_require(raw, "staging_bucket", "root")),
        gcs=GcsConfig(
            bucket_uri=str(_require(gcs_raw, "bucket_uri", "gcs")),
            object_name=str(_require(gcs_raw, "object_name", "gcs")),
            manifest_object_name=str(_require(gcs_raw, "manifest_object_name", "gcs")),
            overwrite_existing=bool(_require(gcs_raw, "overwrite_existing", "gcs")),
        ),
        vector_search=VectorSearchConfig(
            index_display_name=str(_require(vector_raw, "index_display_name", "vector_search")),
            index_dimensions=int(_require(vector_raw, "index_dimensions", "vector_search")),
            distance_measure=str(_require(vector_raw, "distance_measure", "vector_search")),
            approximate_neighbors_count=int(_require(vector_raw, "approximate_neighbors_count", "vector_search")),
            shard_size=str(_require(vector_raw, "shard_size", "vector_search")),
            leaf_node_embedding_count=int(_require(vector_raw, "leaf_node_embedding_count", "vector_search")),
            endpoint_display_name=str(_require(vector_raw, "endpoint_display_name", "vector_search")),
            public_endpoint_enabled=bool(_require(vector_raw, "public_endpoint_enabled", "vector_search")),
            deployed_index_id=str(_require(vector_raw, "deployed_index_id", "vector_search")),
            retrieval_neighbors=int(_require(vector_raw, "retrieval_neighbors", "vector_search")),
            min_replica_count=int(_require(vector_raw, "min_replica_count", "vector_search")),
            max_replica_count=int(_require(vector_raw, "max_replica_count", "vector_search")),
        ),
        rag=RagConfig(
            corpus_display_name=str(_require(rag_raw, "corpus_display_name", "rag")),
            embedding_model=str(_require(rag_raw, "embedding_model", "rag")),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        gemini=GeminiConfig(
            model=str(_require(gemini_raw, "model", "gemini")),
            temperature=float(_require(gemini_raw, "temperature", "gemini")),
            max_output_tokens=int(_require(gemini_raw, "max_output_tokens", "gemini")),
        ),
    )