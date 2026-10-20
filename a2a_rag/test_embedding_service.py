import unittest

from embedding_service import VertexEmbeddingService
from rag_config import RagSettings


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.calls = []

    def embed_content(self, *, model, contents, config):
        self.calls.append((model, contents, config))
        return type("Response", (), {"embeddings": [type("Embedding", (), {"values": [1.0, 2.0]})() for _ in contents]})()


class EmbeddingServiceTests(unittest.TestCase):
    def test_embeds_texts_with_configured_model_and_dimensions(self) -> None:
        fake_model = FakeEmbeddingModel()
        settings = RagSettings(
            project_id="demo-project",
            location="us-central1",
            embedding_model="gemini-embedding-001",
            embedding_dimensions=2,
        )

        embeddings = VertexEmbeddingService(settings, fake_model).embed(["first", "second"])

        self.assertEqual(embeddings, [[1.0, 2.0], [1.0, 2.0]])
        self.assertEqual(
            fake_model.calls,
            [("gemini-embedding-001", ["first", "second"], {"output_dimensionality": 2})],
        )

    def test_empty_input_does_not_call_model(self) -> None:
        fake_model = FakeEmbeddingModel()
        settings = RagSettings(project_id="demo-project")

        self.assertEqual(VertexEmbeddingService(settings, fake_model).embed([]), [])
        self.assertEqual(fake_model.calls, [])


if __name__ == "__main__":
    unittest.main()