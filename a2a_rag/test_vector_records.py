import json
import tempfile
import unittest
from pathlib import Path

from document_pipeline import DocumentChunk
from vector_records import build_vector_records, write_jsonl


class VectorRecordTests(unittest.TestCase):
    def test_builds_metadata_and_embedding_records(self) -> None:
        chunks = [
            DocumentChunk("policy-0000", "policy.txt", "first", 0),
            DocumentChunk("policy-0001", "policy.txt", "second", 1),
        ]

        records = build_vector_records(chunks, [[0.1, 0.2], [0.3, 0.4]])

        self.assertEqual(records[0].id, "policy-0000")
        self.assertEqual(records[0].embedding, [0.1, 0.2])
        self.assertEqual(records[1].metadata["chunk_index"], 1)
        self.assertEqual(records[0].restricts[0]["namespace"], "source_uri")

    def test_rejects_mismatched_chunk_and_embedding_counts(self) -> None:
        chunks = [DocumentChunk("policy-0000", "policy.txt", "first", 0)]

        with self.assertRaises(ValueError):
            build_vector_records(chunks, [])

    def test_writes_vertex_search_jsonl(self) -> None:
        records = build_vector_records(
            [DocumentChunk("policy-0000", "policy.txt", "first", 0)],
            [[0.1, 0.2]],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vectors.jsonl"
            write_jsonl(records, path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["id"], "policy-0000")
        self.assertEqual(payload["embedding"], [0.1, 0.2])
        self.assertEqual(payload["metadata"]["source_uri"], "policy.txt")

    def test_creates_parent_directories_for_jsonl_output(self) -> None:
        records = build_vector_records(
            [DocumentChunk("policy-0000", "policy.txt", "first", 0)],
            [[0.1, 0.2]],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "vectors.jsonl"
            write_jsonl(records, path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["id"], "policy-0000")
        self.assertEqual(payload["embedding"], [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
