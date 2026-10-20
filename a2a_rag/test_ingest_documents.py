import json
import tempfile
import unittest
from pathlib import Path

from ingest_documents import ingest_directory


class FakeEmbeddingService:
    def embed(self, texts):
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


class IngestDocumentsTests(unittest.TestCase):
    def test_ingests_supported_documents_to_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "docs"
            source.mkdir()
            (source / "policy.txt").write_text("Title\n\nPolicy text.", encoding="utf-8")
            output = Path(directory) / "vectors.jsonl"

            count = ingest_directory(source, output, embedding_service=FakeEmbeddingService())
            rows = [json.loads(line) for line in output.read_text().splitlines()]

        self.assertEqual(count, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "policy-0000")
        self.assertEqual(rows[0]["embedding"], [0.0, 1.0])

    def test_rejects_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "No supported documents"):
                ingest_directory(directory, Path(directory) / "vectors.jsonl", embedding_service=FakeEmbeddingService())


if __name__ == "__main__":
    unittest.main()
