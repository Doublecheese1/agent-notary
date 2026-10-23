import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_review


TOKEN = "x" * 40


class AIReviewTriageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = dict(os.environ)
        os.environ.update({
            "AI_REVIEW_ENABLED": "true",
            "AI_REVIEW_DB_PATH": str(Path(self.temp.name) / "reviews.db"),
            "AI_REVIEW_TRIGGER_TOKEN": TOKEN,
            "AI_REVIEW_MIN_CONFIDENCE_BPS": "8500",
            "AI_REVIEW_AUTOMATIC_CAP_UNITS": "250000000",
        })

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.temp.cleanup()

    def case(self, amount=100_000_000):
        request = ai_review.ReviewCase(
            deal_id="0x" + "11" * 32,
            amount_units=amount,
            terms="Deliver a 40x40 cm print in PNG and include the checksum.",
            delivery="Delivered PNG, dimensions and checksum.",
            buyer_claim="The dimensions are not correct.",
            evidence_manifest=[{"name": "image", "sha256": "22" * 32}],
        )
        return ai_review.create_case(request, f"Bearer {TOKEN}")["case_id"]

    def test_two_of_three_high_confidence_is_ready_for_signing(self):
        case_id = self.case()
        answers = {
            "A": ai_review.Evaluation(decision="SELLER_WINS", confidence_bps=9300, flags=[], explanation="Terms met."),
            "B": ai_review.Evaluation(decision="SELLER_WINS", confidence_bps=8900, flags=[], explanation="Terms met."),
            "C": ai_review.Evaluation(decision="BUYER_WINS", confidence_bps=8800, flags=[], explanation="Different reading."),
        }
        with patch.object(ai_review, "_evaluate_remote", side_effect=lambda provider, package: answers[provider]):
            result = ai_review.run_case(case_id, f"Bearer {TOKEN}")
        self.assertEqual(result["status"], "READY_FOR_SIGNING")
        self.assertEqual(result["decision"], "SELLER_WINS")
        self.assertEqual(result["confidence_bps"], 8900)

    def test_disagreement_and_escalation_go_to_human(self):
        case_id = self.case()
        answers = {
            "A": ai_review.Evaluation(decision="SELLER_WINS", confidence_bps=9200, flags=[], explanation="Seller case."),
            "B": ai_review.Evaluation(decision="BUYER_WINS", confidence_bps=9200, flags=[], explanation="Buyer case."),
            "C": ai_review.Evaluation(decision="ESCALATE", confidence_bps=5000, flags=[], explanation="Ambiguous."),
        }
        with patch.object(ai_review, "_evaluate_remote", side_effect=lambda provider, package: answers[provider]):
            result = ai_review.run_case(case_id, f"Bearer {TOKEN}")
        self.assertEqual(result["status"], "HUMAN_REVIEW")

    def test_prompt_injection_flag_forces_human_review(self):
        case_id = self.case()
        answers = {
            key: ai_review.Evaluation(
                decision="SELLER_WINS", confidence_bps=9500,
                flags=["PROMPT_INJECTION"] if key == "A" else [], explanation="Flagged evidence.",
            ) for key in ai_review.PROVIDERS
        }
        with patch.object(ai_review, "_evaluate_remote", side_effect=lambda provider, package: answers[provider]):
            result = ai_review.run_case(case_id, f"Bearer {TOKEN}")
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertIn("PROMPT_INJECTION", result["reason"])

    def test_high_value_case_forces_human_review(self):
        case_id = self.case(amount=300_000_000)
        answer = ai_review.Evaluation(decision="SELLER_WINS", confidence_bps=9700, flags=[], explanation="Terms met.")
        with patch.object(ai_review, "_evaluate_remote", return_value=answer):
            result = ai_review.run_case(case_id, f"Bearer {TOKEN}")
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertIn("cap", result["reason"])

    def test_unknown_provider_flag_is_rejected(self):
        with self.assertRaisesRegex(Exception, "unsupported review flag"):
            ai_review._parse_evaluation({
                "choices": [{"message": {"content": {
                    "decision": "SELLER_WINS",
                    "confidence_bps": 9900,
                    "flags": ["MADE_UP_FLAG"],
                    "explanation": "Unsupported flag must fail closed.",
                }}}],
            })

    def test_automatic_execution_is_closed_by_default(self):
        os.environ.pop("AI_REVIEW_AUTOMATIC_EXECUTION", None)
        with patch("mainnet.connection") as connection:
            self.assertEqual(ai_review._advance_ready_cases(), [])
        connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
