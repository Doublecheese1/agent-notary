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
            "AI_REVIEW_PROVIDER_A_URL": "https://api.openai.com/v1/responses",
            "AI_REVIEW_PROVIDER_A_MODEL": "model-a",
            "AI_REVIEW_PROVIDER_A_API_KEY": "key-a",
            "AI_REVIEW_PROVIDER_A_STYLE": "openai_responses",
            "AI_REVIEW_PROVIDER_B_URL": "https://api.x.ai/v1/chat/completions",
            "AI_REVIEW_PROVIDER_B_MODEL": "model-b",
            "AI_REVIEW_PROVIDER_B_API_KEY": "key-b",
            "AI_REVIEW_PROVIDER_B_STYLE": "openai_chat",
            "AI_REVIEW_PROVIDER_C_URL": "https://api.anthropic.com/v1/messages",
            "AI_REVIEW_PROVIDER_C_MODEL": "model-c",
            "AI_REVIEW_PROVIDER_C_API_KEY": "key-c",
            "AI_REVIEW_PROVIDER_C_STYLE": "anthropic_messages",
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

    def test_provider_envelopes_are_parsed(self):
        expected = {"decision": "SELLER_WINS", "confidence_bps": 9000, "flags": [], "explanation": "Terms met."}
        payloads = [
            {"choices": [{"message": {"content": expected}}]},
            {"output": [{"content": [{"type": "output_text", "text": __import__("json").dumps(expected)}]}]},
            {"content": [{"type": "text", "text": __import__("json").dumps(expected)}]},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.assertEqual(ai_review._parse_evaluation(payload).decision, "SELLER_WINS")

    def test_provider_styles_send_strict_schema(self):
        class Response:
            def raise_for_status(self): pass
            def json(self):
                return {"choices": [{"message": {"content": {
                    "decision": "ESCALATE", "confidence_bps": 5000,
                    "flags": ["AMBIGUOUS_TERMS"], "explanation": "Needs human review.",
                }}}]}

        for style in ai_review.PROVIDER_STYLES:
            with self.subTest(style=style), patch.dict(os.environ, {
                "AI_REVIEW_PROVIDER_A_URL": "https://provider.example/v1/review",
                "AI_REVIEW_PROVIDER_A_MODEL": "review-model",
                "AI_REVIEW_PROVIDER_A_API_KEY": "secret",
                "AI_REVIEW_PROVIDER_A_STYLE": style,
            }), patch.object(ai_review.httpx, "post", return_value=Response()) as post:
                ai_review._evaluate_remote("A", {"deal_id": "0x" + "11" * 32})
                request = post.call_args.kwargs
                if style == "openai_responses":
                    self.assertEqual(request["headers"]["Authorization"], "Bearer secret")
                    self.assertEqual(request["json"]["text"]["format"]["type"], "json_schema")
                elif style == "anthropic_messages":
                    self.assertEqual(request["headers"]["x-api-key"], "secret")
                    self.assertNotIn("Authorization", request["headers"])
                    self.assertEqual(request["json"]["output_config"]["format"]["type"], "json_schema")
                    self.assertIn("anthropic-version", request["headers"])
                else:
                    self.assertEqual(request["headers"]["Authorization"], "Bearer secret")
                    self.assertEqual(request["json"]["response_format"]["type"], "json_schema")

    def test_automatic_execution_is_closed_by_default(self):
        os.environ.pop("AI_REVIEW_AUTOMATIC_EXECUTION", None)
        with patch("mainnet.connection") as connection:
            self.assertEqual(ai_review._advance_ready_cases(), [])
        connection.assert_not_called()

    def test_readiness_requires_three_distinct_provider_services(self):
        status = ai_review.configuration_status()
        self.assertTrue(status["evaluation_ready"])
        self.assertFalse(status["execution_ready"])
        with patch.dict(os.environ, {"AI_REVIEW_PROVIDER_B_URL": "https://api.openai.com/v1/chat/completions"}):
            status = ai_review.configuration_status()
        self.assertFalse(status["evaluation_ready"])
        self.assertIn("AI providers must use three distinct service hosts.", status["reasons"])

    def test_readiness_never_exposes_secrets(self):
        status = ai_review.readiness(f"Bearer {TOKEN}")
        rendered = __import__("json").dumps(status)
        self.assertNotIn("key-a", rendered)
        self.assertNotIn(TOKEN, rendered)


if __name__ == "__main__":
    unittest.main()
