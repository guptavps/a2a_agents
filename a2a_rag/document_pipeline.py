from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedDocument:
    source_uri: str
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_uri: str
    text: str
    chunk_index: int


class DocumentParser:
    def parse(self, path: str | Path) -> ParsedDocument:
        document_path = Path(path)
        suffix = document_path.suffix.lower()
        if suffix == ".pdf":
            text = "\n\n".join(page.extract_text() or "" for page in PdfReader(document_path).pages)
        elif suffix in {".txt", ".md"}:
            text = document_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported document type: {suffix or '<none>'}")

        normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if not normalized:
            raise ValueError(f"Document is empty: {document_path}")
        return ParsedDocument(source_uri=str(document_path), text=normalized)


def chunk_document(
    document: ParsedDocument,
    *,
    max_chars: int = 1000,
    overlap_chars: int = 100,
) -> list[DocumentChunk]:
    if max_chars < 1:
        raise ValueError("max_chars must be greater than zero")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")

    paragraphs = [paragraph.strip() for paragraph in document.text.split("\n\n") if paragraph.strip()]
    chunks: list[DocumentChunk] = []
    current = ""
    chunk_index = 0

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if current and len(candidate) > max_chars:
            chunks.append(_make_chunk(document, current, chunk_index))
            chunk_index += 1
            overlap = current[-overlap_chars:] if overlap_chars else ""
            current = f"{overlap}\n\n{paragraph}" if overlap else paragraph
        else:
            current = candidate

        while len(current) > max_chars:
            chunks.append(_make_chunk(document, current[:max_chars], chunk_index))
            chunk_index += 1
            start = max_chars - overlap_chars
            current = current[start:]

    if current:
        chunks.append(_make_chunk(document, current, chunk_index))
    return chunks


def _make_chunk(document: ParsedDocument, text: str, index: int) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"{Path(document.source_uri).stem}-{index:04d}",
        source_uri=document.source_uri,
        text=text.strip(),
        chunk_index=index,
    )
