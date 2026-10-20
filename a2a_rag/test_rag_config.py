import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rag_config
from rag_config import load_settings


class RagSettingsTests(unittest.TestCase):
    def test_loads_required_settings(self) -> None:
        values = {
            "GOOGLE_CLOUD_PROJECT": "demo-project",
            "VERTEX_AI_SEARCH_DATA_STORE_ID": "projects/demo/locations/global/collections/default_collection/dataStores/policies",
            "LOAN_POLICY_SEARCH_MAX_RESULTS": "7",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = load_settings()

        self.assertEqual(settings.project_id, "demo-project")
        self.assertEqual(settings.data_store_id, values["VERTEX_AI_SEARCH_DATA_STORE_ID"])
        self.assertEqual(settings.max_results, 7)
        self.assertEqual(settings.embedding_model, "gemini-embedding-001")
        self.assertEqual(settings.embedding_dimensions, 768)

    def test_loads_values_from_yaml_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "rag_config.yaml"
            config_path.write_text(
                """
project_id: demo-project-yaml
location: us-central1
max_results: 9
embedding_model: text-embedding-005
embedding_dimensions: 512
""".strip(),
                encoding="utf-8",
            )
            with patch.object(rag_config, "load_dotenv"), patch.dict(
                os.environ, {"RAG_CONFIG_PATH": str(config_path)}, clear=True
            ):
                settings = load_settings()

        self.assertEqual(settings.project_id, "demo-project-yaml")
        self.assertEqual(settings.location, "us-central1")
        self.assertEqual(settings.max_results, 9)
        self.assertEqual(settings.embedding_model, "text-embedding-005")
        self.assertEqual(settings.embedding_dimensions, 512)

    def test_rejects_missing_project(self) -> None:
        with patch.object(rag_config, "load_dotenv"), patch.dict(
            os.environ, {"RAG_CONFIG_PATH": "/tmp/does-not-exist.yaml"}, clear=True
        ):
            with self.assertRaisesRegex(ValueError, "GOOGLE_CLOUD_PROJECT"):
                load_settings()

    def test_rejects_invalid_max_results(self) -> None:
        values = {
            "GOOGLE_CLOUD_PROJECT": "demo-project",
            "VERTEX_AI_SEARCH_DATA_STORE_ID": "store",
            "LOAN_POLICY_SEARCH_MAX_RESULTS": "zero",
        }
        with patch.object(rag_config, "load_dotenv"), patch.dict(
            os.environ, values, clear=True
        ):
            with self.assertRaisesRegex(ValueError, "must be an integer"):
                load_settings()


if __name__ == "__main__":
    unittest.main()
