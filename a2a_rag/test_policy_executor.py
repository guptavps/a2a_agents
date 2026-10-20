import unittest

from policy_executor import PolicyExecutor
from rag_config import RagSettings


class PolicyExecutorTests(unittest.TestCase):
    def test_builds_runner_without_cloud_call(self) -> None:
        executor = PolicyExecutor(
            RagSettings(
                project_id="demo-project",
                data_store_id="projects/demo/locations/global/collections/default_collection/dataStores/policies",
            )
        )

        self.assertIsNotNone(executor._runner)


if __name__ == "__main__":
    unittest.main()
