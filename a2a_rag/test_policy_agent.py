import unittest

from policy_agent import build_policy_agent
from rag_config import RagSettings


class PolicyAgentTests(unittest.TestCase):
    def test_builds_independent_policy_agent(self) -> None:
        settings = RagSettings(
            project_id="demo-project",
            data_store_id="projects/demo/locations/global/collections/default_collection/dataStores/policies",
            max_results=3,
        )

        agent = build_policy_agent(settings)

        self.assertEqual(agent.name, "loan_policy_agent")
        self.assertEqual(len(agent.tools), 1)
        self.assertEqual(agent.tools[0].data_store_id, settings.data_store_id)


if __name__ == "__main__":
    unittest.main()
