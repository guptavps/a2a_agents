import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from document_pipeline import DocumentChunk


@dataclass(frozen=True)
class VectorRecord:
    id: str
    embedding: list[float]
    restricts: list[dict[str, list[str]]]
    metadata: dict[str, str | int]


def build_vector_records(
    chunks: Iterable[DocumentChunk], embeddings: Iterable[list[float]]
) -> list[VectorRecord]:
    records: list[VectorRecord] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        records.append(
            VectorRecord(
                id=chunk.chunk_id,
                embedding=embedding,
                restricts=[
                    {"namespace": "source_uri", "allow": [chunk.source_uri]},
                ],
                metadata={
                    "source_uri": chunk.source_uri,
                    "chunk_index": chunk.chunk_index,
                },
            )
        )
    return records


def write_jsonl(records: Iterable[VectorRecord], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")
