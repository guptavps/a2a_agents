import argparse
from pathlib import Path

from document_pipeline import DocumentParser, chunk_document
from embedding_service import VertexEmbeddingService
from rag_config import load_settings
from vector_records import build_vector_records, write_jsonl


def ingest_directory(
    source_directory: str | Path,
    output_path: str | Path,
    *,
    embedding_service=None,
    max_chars: int = 1000,
    overlap_chars: int = 100,
) -> int:
    parser = DocumentParser()
    paths = sorted(
        path
        for path in Path(source_directory).rglob("*")
        if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}
    )
    chunks = [
        chunk
        for path in paths
        for chunk in chunk_document(
            parser.parse(path),
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
    ]
    if not chunks:
        raise ValueError(f"No supported documents found in {source_directory}")

    service = embedding_service or VertexEmbeddingService(load_settings())
    embeddings = service.embed([chunk.text for chunk in chunks])
    records = build_vector_records(chunks, embeddings)
    write_jsonl(records, output_path)
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse, chunk, embed, and export RAG documents.")
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--max-chars", type=int, default=1000)
    parser.add_argument("--overlap-chars", type=int, default=100)
    args = parser.parse_args()
    count = ingest_directory(
        args.source_directory,
        args.output_path,
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
    )
    print(f"Wrote {count} vector records to {args.output_path}")


if __name__ == "__main__":
    main()
