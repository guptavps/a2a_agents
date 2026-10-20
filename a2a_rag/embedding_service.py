from collections.abc import Sequence
from typing import Protocol

from google import genai

from rag_config import RagSettings, load_settings


class EmbeddingModel(Protocol):
    def embed_content(self, *, model: str, contents: Sequence[str], config: dict): ...


class VertexEmbeddingService:
    def __init__(self, settings: RagSettings | None = None, model: EmbeddingModel | None = None) -> None:
        resolved_settings = settings or load_settings()
        self._settings = resolved_settings
        if model is not None:
            self._model = model
            self._client = None
        else:
            self._client = genai.Client(
                vertexai=True,
                project=resolved_settings.project_id,
                location=resolved_settings.location,
            )
            self._model = self._client.models

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._model.embed_content(
            model=self._settings.embedding_model,
            contents=list(texts),
            config={"output_dimensionality": self._settings.embedding_dimensions},
        )
        return [list(embedding.values) for embedding in response.embeddings]