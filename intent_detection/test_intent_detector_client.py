import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

from intent_detection.intent_detector_client import _print_response


class StreamingResponse:
    def __init__(self, *, status_update=None, artifact_update=None):
        self.message = None
        self.task = None
        self.status_update = status_update
        self.artifact_update = artifact_update

    def HasField(self, field):
        return getattr(self, field) is not None


class IntentDetectorClientTests(unittest.TestCase):
    def test_print_response_displays_user_text_not_intermediate_decision(self):
        decision = (
            '{"intent":"loan_closure","confidence":0.98,'
            '"rationale":"The user explicitly requests loan closure."}'
        )
        response = StreamingResponse(
            status_update=SimpleNamespace(
                status=SimpleNamespace(
                    message=SimpleNamespace(parts=[SimpleNamespace(text=decision)])
                )
            ),
            artifact_update=SimpleNamespace(
                artifact=SimpleNamespace(
                    parts=[SimpleNamespace(text="The loan-closure agent is not connected yet.")]
                )
            ),
        )
        printed_texts = set()
        output = StringIO()

        with redirect_stdout(output):
            first_printed = _print_response(response, printed_texts)
            second_printed = _print_response(response, printed_texts)

        self.assertTrue(first_printed)
        self.assertFalse(second_printed)
        self.assertEqual(
            output.getvalue(),
            "Agent: The loan-closure agent is not connected yet.\n",
        )


if __name__ == "__main__":
    unittest.main()