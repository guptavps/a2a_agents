import unittest

from policy_search import build_policy_search_tool
from rag_config import RagSettings


class PolicySearchTests(unittest.TestCase):
    def test_builds_vertex_ai_search_tool(self) -> None:
        settings = RagSettings(
            project_id="demo-project",
            data_store_id="projects/demo/locations/global/collections/default_collection/dataStores/policies",
            max_results=4,
        )

        tool = build_policy_search_tool(settings)

        self.assertEqual(tool.data_store_id, settings.data_store_id)
        self.assertEqual(tool.max_results, settings.max_results)

    def test_builds_custom_vector_index_tool_when_data_store_is_absent(self) -> None:
        settings = RagSettings(
            project_id="demo-project",
            location="us-central1",
            index_id="123456789",
            max_results=4,
        )

        tool = build_policy_search_tool(settings)

        self.assertEqual(tool.name, "search_policy_index")
        self.assertTrue(callable(tool.func))


if __name__ == "__main__":
    unittest.main()
