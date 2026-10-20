import argparse
from pathlib import Path
from typing import TypeVar

from google.cloud import aiplatform

from pipeline_config import load_pipeline_config


ResourceT = TypeVar("ResourceT")


def _find_unique_by_display_name(resources: list[ResourceT], display_name: str, kind: str) -> ResourceT:
    matches = [resource for resource in resources if resource.display_name == display_name]
    if not matches:
        raise ValueError(f"No {kind} found with display name: {display_name}")
    if len(matches) > 1:
        raise ValueError(f"Multiple {kind}s found with display name: {display_name}")
    return matches[0]


def deploy_vector_index(
    config_path: str | Path = "pipeline_config.yaml", *, wait: bool = True
):
    """Deploy the index and wait for serving infrastructure by default."""
    config = load_pipeline_config(config_path)
    vector_config = config.vector_search

    aiplatform.init(project=config.project_id, location=config.region)

    index = _find_unique_by_display_name(
        aiplatform.MatchingEngineIndex.list(),
        vector_config.index_display_name,
        "Vector Search index",
    )
    endpoint = _find_unique_by_display_name(
        aiplatform.MatchingEngineIndexEndpoint.list(),
        vector_config.endpoint_display_name,
        "Vector Search index endpoint",
    )

    return endpoint.deploy_index(
        index=index,
        deployed_index_id=vector_config.deployed_index_id,
        display_name=vector_config.deployed_index_id,
        min_replica_count=vector_config.min_replica_count,
        max_replica_count=vector_config.max_replica_count,
        sync=wait,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy a Vertex AI Vector Search index to an endpoint."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pipeline_config.yaml"),
        help="Path to the YAML pipeline configuration.",
    )
    parser.set_defaults(wait=True)
    parser.add_argument(
        "--async",
        dest="wait",
        action="store_false",
        help="Submit deployment without waiting for serving infrastructure.",
    )
    args = parser.parse_args()
    endpoint = deploy_vector_index(args.config, wait=args.wait)
    action = "completed" if args.wait else "submitted"
    print(f"Index deployment {action} on endpoint: {endpoint.resource_name}")


if __name__ == "__main__":
    main()