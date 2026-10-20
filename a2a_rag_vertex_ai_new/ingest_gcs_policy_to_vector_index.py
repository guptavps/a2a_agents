import argparse
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlparse

from google import genai
from google.cloud import aiplatform
from google.cloud.aiplatform_v1.types.index import IndexDatapoint
from google.cloud import storage
from pypdf import PdfReader

from pipeline_config import load_pipeline_config


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    source_uri: str
    page_number: int
    text: str


ResourceT = TypeVar("ResourceT")


def _parse_gs_uri(bucket_uri: str) -> str:
    parsed = urlparse(bucket_uri)
    if parsed.scheme != "gs" or not parsed.netloc or parsed.path.strip("/"):
        raise ValueError("gcs.bucket_uri must be a bucket-only URI such as gs://bucket-name")
    return parsed.netloc


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    text = re.sub(r"\s+(?=(?:\d+(?:\.\d+)*\s+)[A-Z])", "\n\n", text)
    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_length = 0
            chunks.extend(_split_long_paragraph(paragraph, chunk_size, chunk_overlap))
            continue

        candidate_length = current_length + len(paragraph) + (2 if current else 0)
        if current and candidate_length > chunk_size:
            chunks.append("\n\n".join(current))
            overlap = current[-1] if chunk_overlap and len(current[-1]) <= chunk_overlap else ""
            current = [overlap, paragraph] if overlap else [paragraph]
            current_length = sum(len(item) for item in current) + (2 * (len(current) - 1))
        else:
            current.append(paragraph)
            current_length = candidate_length

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_long_paragraph(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        candidate_length = current_length + len(word) + (1 if current else 0)
        if current and candidate_length > chunk_size:
            chunk = " ".join(current)
            chunks.append(chunk)
            overlap_words: list[str] = []
            overlap_length = 0
            for previous_word in reversed(current):
                if overlap_length + len(previous_word) + (1 if overlap_words else 0) > chunk_overlap:
                    break
                overlap_words.insert(0, previous_word)
                overlap_length += len(previous_word) + (1 if len(overlap_words) > 1 else 0)
            current = overlap_words
            current_length = len(" ".join(current))
        current.append(word)
        current_length = len(" ".join(current))
    if current:
        chunks.append(" ".join(current))
    return chunks


def _extract_page_text(page, page_number: int) -> str:
    """Extract readable text while removing predictable PDF layout artifacts."""
    raw_text = page.extract_text(extraction_mode="layout") or ""
    cleaned_lines: list[str] = []
    skip_split_header_tail = False
    skip_page_number = False
    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            cleaned_lines.append("")
            continue
        if line.startswith("Loan Closure Policy | Controlled document Page"):
            skip_page_number = True
            continue
        if skip_page_number and line == str(page_number):
            skip_page_number = False
            continue
        skip_page_number = False
        if line in {"Loan Closure Policy | Controlled document", f"Page {page_number}"}:
            continue
        if line == "Contro":
            skip_split_header_tail = True
            continue
        if skip_split_header_tail and line == "l":
            skip_split_header_tail = False
            continue
        skip_split_header_tail = False
        if line == "Contro Required action":
            skip_split_header_tail = True
            continue
        if line in {"Control", "Required action"}:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _section_ranges(page_texts: list[tuple[int, str]]) -> list[tuple[int, str]]:
    combined_parts: list[str] = []
    page_starts: list[tuple[int, int]] = []
    current_offset = 0
    for page_number, text in page_texts:
        page_starts.append((current_offset, page_number))
        combined_parts.append(text)
        current_offset += len(text) + 2
    combined = "\n\n".join(combined_parts)

    heading_matches = list(
        re.finditer(r"(?m)^(?:(?:\d+\.\s+)|(?:\d+(?:\.\d+)+\s+))[^\n]+$", combined)
    )
    boundaries = [0] + [match.start() for match in heading_matches] + [len(combined)]
    sections: list[tuple[int, str]] = []
    for start, end in zip(boundaries, boundaries[1:]):
        section_text = combined[start:end].strip()
        if not section_text:
            continue
        page_number = next(
            page for offset, page in reversed(page_starts) if offset <= start
        )
        sections.append((page_number, section_text))
    return sections


def _read_and_chunk_gcs_policy(config_path: str | Path) -> list[PolicyChunk]:
    config = load_pipeline_config(config_path)
    bucket_name = _parse_gs_uri(config.gcs.bucket_uri)
    source_uri = f"gs://{bucket_name}/{config.gcs.object_name}"
    client = storage.Client(project=config.project_id)
    pdf_bytes = client.bucket(bucket_name).blob(config.gcs.object_name).download_as_bytes()
    reader = PdfReader(io.BytesIO(pdf_bytes))

    page_texts: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = _extract_page_text(page, page_number)
        if page_text:
            page_texts.append((page_number, page_text))

    chunks: list[PolicyChunk] = []
    chunk_number = 0
    for page_number, section_text in _section_ranges(page_texts):
        section_chunks = _chunk_text(
            section_text,
            config.rag.chunk_size,
            config.rag.chunk_overlap,
        )
        for text in section_chunks:
            chunk_number += 1
            chunks.append(
                PolicyChunk(
                    chunk_id=f"loan-closure-policy-p{page_number:03d}-c{chunk_number:03d}",
                    source_uri=source_uri,
                    page_number=page_number,
                    text=text,
                )
            )
    return chunks


def _find_unique_by_display_name(
    resources: list[ResourceT], display_name: str, kind: str
) -> ResourceT:
    matches = [resource for resource in resources if resource.display_name == display_name]
    if not matches:
        raise ValueError(f"No {kind} found with display name: {display_name}")
    if len(matches) > 1:
        raise ValueError(f"Multiple {kind}s found with display name: {display_name}")
    return matches[0]


def _embed_chunks(config, chunks: list[PolicyChunk]) -> list[list[float]]:
    client = genai.Client(
        vertexai=True,
        project=config.project_id,
        location=config.region,
    )
    response = client.models.embed_content(
        model=config.rag.embedding_model,
        contents=[chunk.text for chunk in chunks],
        config={"output_dimensionality": config.vector_search.index_dimensions},
    )
    embeddings = [list(embedding.values) for embedding in response.embeddings]
    if len(embeddings) != len(chunks):
        raise RuntimeError(
            f"Embedding count mismatch: chunks={len(chunks)}, embeddings={len(embeddings)}"
        )
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        if len(embedding) != config.vector_search.index_dimensions:
            raise ValueError(
                f"Embedding for {chunk.chunk_id} has {len(embedding)} dimensions; "
                f"expected {config.vector_search.index_dimensions}"
            )
    return embeddings


def _to_datapoints(chunks: list[PolicyChunk], embeddings: list[list[float]]) -> list[IndexDatapoint]:
    return [
        IndexDatapoint(
            datapoint_id=chunk.chunk_id,
            feature_vector=embedding,
            restricts=[
                {"namespace": "source_uri", "allow_list": [chunk.source_uri]},
                {"namespace": "page_number", "allow_list": [str(chunk.page_number)]},
            ],
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]


def _upload_manifest(config, chunks: list[PolicyChunk]) -> str:
    bucket_name = _parse_gs_uri(config.gcs.bucket_uri)
    manifest = "".join(
        json.dumps(
            {
                "chunk_id": chunk.chunk_id,
                "source_uri": chunk.source_uri,
                "page_number": chunk.page_number,
                "text": chunk.text,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
        for chunk in chunks
    )
    client = storage.Client(project=config.project_id)
    client.bucket(bucket_name).blob(config.gcs.manifest_object_name).upload_from_string(
        manifest,
        content_type="application/jsonl",
    )
    return f"gs://{bucket_name}/{config.gcs.manifest_object_name}"


def ingest_gcs_policy_to_vector_index(
    config_path: str | Path = "pipeline_config.yaml",
) -> int:
    """Read from GCS, chunk and embed in memory, then upsert vectors to the index."""
    config = load_pipeline_config(config_path)
    chunks = _read_and_chunk_gcs_policy(config_path)
    if not chunks:
        raise ValueError("No text chunks were extracted from the configured GCS PDF")

    embeddings = _embed_chunks(config, chunks)
    datapoints = _to_datapoints(chunks, embeddings)

    aiplatform.init(project=config.project_id, location=config.region)
    index = _find_unique_by_display_name(
        aiplatform.MatchingEngineIndex.list(),
        config.vector_search.index_display_name,
        "Vector Search index",
    )
    index.upsert_datapoints(datapoints)
    manifest_uri = _upload_manifest(config, chunks)
    print(f"Uploaded chunk manifest: {manifest_uri}")
    return len(datapoints)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read a GCS PDF, embed in memory, and upload vectors."
    )
    parser.add_argument("--config", type=Path, default=Path("pipeline_config.yaml"))
    args = parser.parse_args()
    count = ingest_gcs_policy_to_vector_index(args.config)
    print(f"Uploaded {count} policy embeddings to Vector Search")


if __name__ == "__main__":
    main()