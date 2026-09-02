import unittest
from unittest.mock import patch
import json

from assistant import MGCAssistant


class RequiredQuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = MGCAssistant()

    def test_base_price(self):
        answer = self.bot.ask("What's the base price of a 2-bed in Block B?")
        self.assertIn("PKR 22,425,000", answer.text)
        self.assertTrue(answer.evidence)

    def test_stacked_premiums(self):
        answer = self.bot.ask("What's the total for a Margalla-facing corner unit on floor 15, 2-bed Block B?")
        self.assertIn("PKR 25,340,250", answer.text)
        self.assertIn("13%", answer.text)
        self.assertGreaterEqual(len(answer.evidence), 4)

    def test_transfer_fee_conflict(self):
        answer = self.bot.ask("What's the transfer fee?")
        self.assertIn("conflict", answer.text)
        self.assertIn("2%", answer.text)
        self.assertIn("2.5%", answer.text)
        self.assertEqual(len(answer.evidence), 2)

    def test_rental_yield_refusal(self):
        answer = self.bot.ask("What's the rental yield on a 1-bed?")
        self.assertIn("does not publish", answer.text)
        self.assertIn("must not", answer.text)

    def test_anchor_tenant_unconfirmed(self):
        answer = self.bot.ask("Who is the anchor tenant?")
        self.assertIn("No anchor tenant has been confirmed", answer.text)

    def test_unknown_question_is_not_invented(self):
        # Gemini is responsible for general questions; verify its grounded JSON and
        # source-ID mapping without making a network request in the test suite.
        api_response = {
            "candidates": [{"content": {"parts": [{"text": json.dumps({
                "answer": "Two-level basement parking provides 640 slots.",
                "source_ids": ["S3"],
            })}]}}]
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps(api_response).encode()

        bot = MGCAssistant(api_key="test-key")
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            answer = bot.ask("How many parking slots are there?")
        self.assertIn("640", answer.text)
        self.assertTrue(answer.evidence)


if __name__ == "__main__":
    unittest.main()
