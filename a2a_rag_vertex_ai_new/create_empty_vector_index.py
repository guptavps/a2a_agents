import argparse
from pathlib import Path

import vertexai
from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine.matching_engine_index_config import (
    DistanceMeasureType,
)

from pipeline_config import load_pipeline_config


def create_empty_vector_index(config_path: str | Path = "pipeline_config.yaml"):
    """Create an empty stream-update Vector Search index from YAML settings."""
    config = load_pipeline_config(config_path)
    vector_config = config.vector_search

    vertexai.init(project=config.project_id, location=config.region)
    aiplatform.init(project=config.project_id, location=config.region)

    distance_measure = DistanceMeasureType[vector_config.distance_measure]
    return aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=vector_config.index_display_name,
        contents_delta_uri=None,
        dimensions=vector_config.index_dimensions,
        approximate_neighbors_count=vector_config.approximate_neighbors_count,
        leaf_node_embedding_count=vector_config.leaf_node_embedding_count,
        distance_measure_type=distance_measure,
        index_update_method="STREAM_UPDATE",
        shard_size=vector_config.shard_size,
        sync=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an empty Vertex AI Vector Search index.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pipeline_config.yaml"),
        help="Path to the YAML pipeline configuration.",
    )
    args = parser.parse_args()
    index = create_empty_vector_index(args.config)
    print(f"Created empty Vector Search index: {index.resource_name}")


if __name__ == "__main__":
    main()