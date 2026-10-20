"""Send the local mixed-content PDF to both configured Document AI processors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.protobuf.json_format import MessageToDict


DEFAULT_CONFIG_PATH = Path("processor_config.local.json")
DEFAULT_INPUT_PATH = Path("output/sample_mixed_document.pdf")
DEFAULT_OUTPUT_DIR = Path("output/document_ai_responses")
MAX_ONLINE_FILE_SIZE = 20 * 1024 * 1024


def _load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"Processor config not found: {path}. Run processor_setup.py first.") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"Processor config is not valid JSON: {path}") from error

    for key in ("project_id", "location", "processors"):
        if key not in config:
            raise SystemExit(f"Processor config is missing {key!r}: {path}")
    for processor_key in ("layout_parser", "form_parser"):
        if processor_key not in config["processors"]:
            raise SystemExit(f"Processor config is missing processors.{processor_key}: {path}")
    return config


def _text_from_layout(layout: Any, document_text: str) -> str:
    anchor = layout.text_anchor
    if anchor.content:
        return anchor.content.strip()

    pieces = []
    for segment in anchor.text_segments:
        start = int(segment.start_index) if segment.start_index else 0
        end = int(segment.end_index)
        pieces.append(document_text[start:end])
    return "".join(pieces).strip()


def _layout_block_summary(document: Any) -> list[dict[str, Any]]:
    summary = []

    def visit(blocks: Any) -> None:
        for block in blocks:
            page_span = block.page_span
            page_range = None
            if page_span.page_start or page_span.page_end:
                page_range = [page_span.page_start, page_span.page_end]
            item: dict[str, Any] = {"block_id": block.block_id}
            if page_range:
                item["page_range"] = page_range
            if block.text_block:
                item.update(kind="text", type=block.text_block.type_, text=block.text_block.text)
                visit(block.text_block.blocks)
            elif block.table_block:
                item.update(
                    kind="table",
                    header_rows=len(block.table_block.header_rows),
                    body_rows=len(block.table_block.body_rows),
                )
            elif block.list_block:
                item.update(kind="list", entries=len(block.list_block.list_entries))
            elif block.image_block:
                item["kind"] = "image"
            else:
                item["kind"] = "unknown"

            summary.append(item)

    visit(document.document_layout.blocks)
    return summary


def _layout_page_numbers(document: Any) -> list[int]:
    page_numbers: set[int] = set()

    def visit(blocks: Any) -> None:
        for block in blocks:
            if block.page_span.page_start:
                page_numbers.update(
                    range(block.page_span.page_start, block.page_span.page_end + 1)
                )
            if block.text_block:
                visit(block.text_block.blocks)

    visit(document.document_layout.blocks)
    return sorted(page_numbers)


def _layout_text(document: Any) -> str:
    lines: list[str] = []

    def visit(blocks: Any) -> None:
        for block in blocks:
            if block.text_block:
                text = block.text_block.text.strip()
                if text:
                    lines.append(text)
                visit(block.text_block.blocks)

    visit(document.document_layout.blocks)
    return "\n".join(lines)


def _form_fields(document: Any) -> list[dict[str, Any]]:
    fields = []
    for page in document.pages:
        for form_field in page.form_fields:
            fields.append(
                {
                    "page": page.page_number,
                    "name": _text_from_layout(form_field.field_name, document.text),
                    "value": _text_from_layout(form_field.field_value, document.text),
                    "confidence": form_field.field_value.confidence,
                    "value_type": form_field.value_type or None,
                }
            )
    return fields


def _save_document(document: Any, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = MessageToDict(document._pb, preserving_proto_field_name=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _process_processor(
    client: documentai.DocumentProcessorServiceClient,
    *,
    processor_name: str,
    processor_key: str,
    config: dict[str, Any],
    pdf_content: bytes,
    output_dir: Path,
) -> None:
    processor_info = config["processors"][processor_key]
    if processor_info.get("state") != "ENABLED":
        raise SystemExit(
            f"Processor {processor_info.get('id', processor_key)} is not ENABLED; "
            "rerun processor_setup.py or check its state in Google Cloud Console."
        )

    print(f"\nSubmitting PDF to {processor_name} ({processor_info['id']})...")
    request = documentai.ProcessRequest(
        name=processor_info["name"],
        raw_document=documentai.RawDocument(content=pdf_content, mime_type="application/pdf"),
    )
    response = client.process_document(request=request)
    document = response.document
    output_path = output_dir / f"{processor_key}_response.json"
    _save_document(document, output_path)
    if document.pages:
        print(f"Processed pages: {len(document.pages)}")
    elif processor_key == "layout_parser":
        page_numbers = _layout_page_numbers(document)
        if page_numbers:
            print(f"Layout spans pages: {', '.join(map(str, page_numbers))}")
    print(f"Full Document AI response: {output_path}")

    if processor_key == "layout_parser":
        print("\n--- Layout Parser recognized text ---")
        recognized_text = document.text.strip() or _layout_text(document)
        print(recognized_text or "(no text returned)")
        blocks = _layout_block_summary(document)
        print(f"\n--- Layout Parser blocks ({len(blocks)}) ---")
        for block in blocks:
            kind = block["kind"]
            detail = block.get("text", "")
            if kind == "table":
                detail = f"header_rows={block['header_rows']}, body_rows={block['body_rows']}"
            elif kind == "list":
                detail = f"entries={block['entries']}"
            page_info = f"page {block['page_range'][0]}" if block.get("page_range") else "page unknown"
            print(f"{page_info} {kind}: {detail}")
    else:
        print("\n--- Form Parser key-value fields ---")
        fields = _form_fields(document)
        if not fields:
            print("(no form fields returned)")
        for field in fields:
            print(
                f"page {field['page']}: {field['name']} = {field['value']} "
                f"(confidence {field['confidence']:.2f}"
                f"{', type ' + field['value_type'] if field['value_type'] else ''})"
            )
        print(f"\nRecognized text length: {len(document.text)} characters")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--confirm-processing",
        action="store_true",
        help="Submit the PDF to both processors; this uses billable Document AI processing.",
    )
    args = parser.parse_args()

    config = _load_config(args.config)
    if not args.input.is_file():
        raise SystemExit(f"Input PDF not found: {args.input}. Run generate_sample_pdf.py first.")
    file_size = args.input.stat().st_size
    if file_size > MAX_ONLINE_FILE_SIZE:
        raise SystemExit(
            f"Input is {file_size} bytes; online processing supports up to 20 MB. "
            "Use batch processing for larger files."
        )

    processors = config["processors"]
    for key, expected_type in (
        ("layout_parser", "LAYOUT_PARSER_PROCESSOR"),
        ("form_parser", "FORM_PARSER_PROCESSOR"),
    ):
        if processors[key].get("type") != expected_type:
            raise SystemExit(f"processors.{key} must have type {expected_type}")

    print(f"Project: {config['project_id']}")
    print(f"Location: {config['location']}")
    print(f"Input: {args.input} ({file_size:,} bytes)")
    print("Processors: Layout Parser and Form Parser")
    if not args.confirm_processing:
        print("No request sent. Add --confirm-processing to run two billable online processor requests.")
        return

    pdf_content = args.input.read_bytes()
    with documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(
            api_endpoint=f"{config['location']}-documentai.googleapis.com"
        )
    ) as client:
        _process_processor(
            client,
            processor_name="Layout Parser",
            processor_key="layout_parser",
            config=config,
            pdf_content=pdf_content,
            output_dir=args.output_dir,
        )
        _process_processor(
            client,
            processor_name="Form Parser",
            processor_key="form_parser",
            config=config,
            pdf_content=pdf_content,
            output_dir=args.output_dir,
        )


if __name__ == "__main__":
    main()