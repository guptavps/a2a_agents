import argparse
from pathlib import Path

from google.cloud import aiplatform

from pipeline_config import load_pipeline_config


def create_vector_index_endpoint(config_path: str | Path = "pipeline_config.yaml"):
    """Create a Vector Search index endpoint from YAML settings."""
    config = load_pipeline_config(config_path)
    vector_config = config.vector_search

    aiplatform.init(project=config.project_id, location=config.region)

    return aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=vector_config.endpoint_display_name,
        public_endpoint_enabled=vector_config.public_endpoint_enabled,
        sync=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Vertex AI Vector Search index endpoint."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pipeline_config.yaml"),
        help="Path to the YAML pipeline configuration.",
    )
    args = parser.parse_args()
    endpoint = create_vector_index_endpoint(args.config)
    print(f"Created Vector Search index endpoint: {endpoint.resource_name}")
    if endpoint.public_endpoint_domain_name:
        print(f"Public endpoint domain: {endpoint.public_endpoint_domain_name}")


if __name__ == "__main__":
    main()