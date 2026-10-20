import tempfile
import unittest
from pathlib import Path

from document_pipeline import DocumentParser, ParsedDocument, chunk_document


class DocumentPipelineTests(unittest.TestCase):
    def test_parses_text_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.txt"
            path.write_text("Title\n\nFirst rule.", encoding="utf-8")

            document = DocumentParser().parse(path)

        self.assertEqual(document.text, "Title\n\nFirst rule.")
        self.assertEqual(document.source_uri, str(path))

    def test_rejects_unknown_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.csv"
            path.write_text("rule", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported document type"):
                DocumentParser().parse(path)

    def test_chunks_with_stable_ids_and_overlap(self) -> None:
        document = ParsedDocument("policy.txt", "Paragraph one.\n\nParagraph two.\n\nParagraph three.")

        chunks = chunk_document(document, max_chars=25, overlap_chars=5)

        self.assertGreater(len(chunks), 1)
        self.assertEqual([chunk.chunk_index for chunk in chunks], list(range(len(chunks))))
        self.assertEqual(chunks[0].chunk_id, "policy-0000")
        self.assertTrue(any(
            chunks[index].text.rstrip()[-4:] in chunks[index + 1].text
            for index in range(len(chunks) - 1)
        ))

    def test_rejects_invalid_chunk_settings(self) -> None:
        document = ParsedDocument("policy.txt", "text")

        with self.assertRaises(ValueError):
            chunk_document(document, max_chars=0)
        with self.assertRaises(ValueError):
            chunk_document(document, max_chars=10, overlap_chars=10)


if __name__ == "__main__":
    unittest.main()
