"""Discover and create or reuse the sample's Document AI processors."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.api_core.client_options import ClientOptions
from google.cloud import documentai


PROCESSOR_SPECS = (
    ("layout_parser", "LAYOUT_PARSER_PROCESSOR", "google-doc-ai-layout-sample"),
    ("form_parser", "FORM_PARSER_PROCESSOR", "google-doc-ai-form-sample"),
)
DEFAULT_PROJECT_ID = "genai-ai-agents-project"
DEFAULT_LOCATION = "us"
DEFAULT_CONFIG_PATH = Path("processor_config.local.json")


def get_available_processor_types(client: Any, parent: str) -> dict[str, Any]:
    return {processor_type.type_: processor_type for processor_type in client.list_processor_types(parent=parent)}


def ensure_processor(
    client: Any,
    *,
    parent: str,
    processor_type: str,
    display_name: str,
    available_types: dict[str, Any],
    dry_run: bool = False,
) -> tuple[Any | None, str]:
    type_info = available_types.get(processor_type)
    if type_info is None:
        raise RuntimeError(f"{processor_type} is not available in {parent} for this project/account")
    if not type_info.allow_creation:
        raise RuntimeError(f"{processor_type} is not currently creatable in {parent}")

    available_locations = {item.location_id for item in type_info.available_locations}
    location = parent.rsplit("/", maxsplit=1)[-1]
    if location not in available_locations:
        raise RuntimeError(f"{processor_type} is not available in location {location}")

    matches = [
        processor
        for processor in client.list_processors(parent=parent)
        if processor.display_name == display_name
    ]
    if len(matches) > 1:
        names = ", ".join(processor.name for processor in matches)
        raise RuntimeError(
            f"Multiple processors have display name {display_name!r}: {names}. "
            "Resolve the duplicate manually; no new processor was created."
        )
    if matches:
        existing = matches[0]
        if existing.type_ != processor_type:
            raise RuntimeError(
                f"Processor {existing.name} is named {display_name!r} but has type "
                f"{existing.type_}, expected {processor_type}; no new processor was created."
            )
        return existing, "reused"

    if dry_run:
        return None, "would-create"

    created = client.create_processor(
        parent=parent,
        processor=documentai.Processor(type_=processor_type, display_name=display_name),
    )
    return created, "created"


def write_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            json.dump(config, temporary_file, indent=2)
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT_ID))
    parser.add_argument("--location", default=os.getenv("DOCUMENT_AI_LOCATION", DEFAULT_LOCATION))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check availability and report planned creates without creating processors.",
    )
    args = parser.parse_args()

    endpoint = f"{args.location}-documentai.googleapis.com"
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=endpoint)
    )
    parent = f"projects/{args.project}/locations/{args.location}"
    available_types = get_available_processor_types(client, parent)

    config: dict[str, Any] = {
        "project_id": args.project,
        "location": args.location,
        "processors": {},
    }
    for config_key, processor_type, display_name in PROCESSOR_SPECS:
        processor_type_info = available_types.get(processor_type)
        locations = (
            sorted(item.location_id for item in processor_type_info.available_locations)
            if processor_type_info
            else []
        )
        print(
            f"{processor_type}: available={processor_type_info is not None}, "
            f"creatable={processor_type_info.allow_creation if processor_type_info else False}, "
            f"locations={locations}"
        )
        processor, action = ensure_processor(
            client,
            parent=parent,
            processor_type=processor_type,
            display_name=display_name,
            available_types=available_types,
            dry_run=args.dry_run,
        )
        if processor is None:
            print(f"{display_name}: {action}")
            continue
        config["processors"][config_key] = {
            "name": processor.name,
            "id": processor.name.rsplit("/", maxsplit=1)[-1],
            "type": processor.type_,
            "display_name": processor.display_name,
            "state": documentai.Processor.State(processor.state).name,
        }
        print(
            f"{display_name}: {action}; id={config['processors'][config_key]['id']}; "
            f"state={config['processors'][config_key]['state']}"
        )

    if not args.dry_run:
        write_config(args.config, config)
        print(f"Processor config written to {args.config}")
    else:
        print("Dry run complete; no processors were created and no config was written.")


if __name__ == "__main__":
    main()