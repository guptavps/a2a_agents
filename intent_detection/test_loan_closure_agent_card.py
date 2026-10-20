import os
import unittest
from unittest.mock import patch

from intent_detection.loan_closure_agent.agent_card import build_agent_card


class LoanClosureAgentCardTests(unittest.TestCase):
    def test_local_card_url_matches_localhost_fetch_origin(self):
        with patch.dict(
            os.environ,
            {
                "APP_URL": "",
                "GOOGLE_CLOUD_AGENT_ENGINE_ID": "",
                "GOOGLE_CLOUD_PROJECT": "",
            },
        ):
            card = build_agent_card(
                name="loan_closure_agent",
                description="Loan closure test agent.",
                port=8094,
            )

        self.assertEqual(
            [interface.url for interface in card.supported_interfaces],
            ["http://localhost:8094/", "http://localhost:8094/"],
        )


if __name__ == "__main__":
    unittest.main()