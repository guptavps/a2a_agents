import argparse
from pathlib import Path

from google.cloud import aiplatform

from create_empty_vector_index import create_empty_vector_index
from create_vector_index_endpoint import create_vector_index_endpoint
from deploy_vector_index import deploy_vector_index
from pipeline_config import load_pipeline_config


def _find_unique(resources, display_name: str, kind: str):
    matches = [resource for resource in resources if resource.display_name == display_name]
    if len(matches) > 1:
        raise ValueError(f"Multiple {kind}s found with display name: {display_name}")
    return matches[0] if matches else None


def reset_vector_search_resources(
    config_path: str | Path = "pipeline_config.yaml", *, wait: bool = True
) -> None:
    """Delete and recreate the configured endpoint and index as a clean pair."""
    config = load_pipeline_config(config_path)
    aiplatform.init(project=config.project_id, location=config.region)

    endpoint = _find_unique(
        aiplatform.MatchingEngineIndexEndpoint.list(),
        config.vector_search.endpoint_display_name,
        "Vector Search index endpoint",
    )
    if endpoint is not None:
        endpoint.delete(force=True, sync=True)
        print(f"Deleted endpoint: {endpoint.resource_name}")

    index = _find_unique(
        aiplatform.MatchingEngineIndex.list(),
        config.vector_search.index_display_name,
        "Vector Search index",
    )
    if index is not None:
        index.delete(sync=True)
        print(f"Deleted index: {index.resource_name}")

    new_index = create_empty_vector_index(config_path)
    print(f"Created clean index: {new_index.resource_name}")
    new_endpoint = create_vector_index_endpoint(config_path)
    print(f"Created clean endpoint: {new_endpoint.resource_name}")
    deployed_endpoint = deploy_vector_index(config_path, wait=wait)
    state = "completed" if wait else "submitted"
    print(f"Clean deployment {state}: {deployed_endpoint.resource_name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Destructively recreate the configured Vector Search resources."
    )
    parser.add_argument("--config", type=Path, default=Path("pipeline_config.yaml"))
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Confirm deletion and recreation of the configured endpoint and index.",
    )
    parser.set_defaults(wait=True)
    parser.add_argument(
        "--async",
        dest="wait",
        action="store_false",
        help="Submit the new deployment without waiting.",
    )
    args = parser.parse_args()
    if not args.confirm_reset:
        parser.error("Pass --confirm-reset to delete and recreate Vector Search resources")
    reset_vector_search_resources(args.config, wait=args.wait)


if __name__ == "__main__":
    main()
