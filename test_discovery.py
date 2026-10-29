import json
import unittest

from fastapi import HTTPException

from discovery import a2a_send_message, agent_card, llms_txt, protocol_status, router


def decoded(response):
    return json.loads(response.body.decode("utf-8"))


class DiscoveryTests(unittest.TestCase):
    def test_routes_are_registered(self):
        paths = {route.path for route in router.routes}
        self.assertEqual(
            paths,
            {"/v1/protocol/status", "/.well-known/agent-card.json", "/a2a/message:send", "/llms.txt"},
        )

    def test_public_status_is_truthful_and_read_only(self):
        body = protocol_status()
        self.assertEqual(body["public_launch_date"], "2026-10-23")
        self.assertFalse(body["production"]["enabled"])
        self.assertFalse(body["production"]["accepting_funds"])
        self.assertTrue(body["sandbox"]["enabled"])
        self.assertFalse(body["sandbox"]["real_money"])
        self.assertFalse(body["capabilities"]["public_money_movement_tools"])
        self.assertFalse(body["capabilities"]["x402_payments"])

    def test_agent_card_only_advertises_working_read_only_skills(self):
        response = agent_card()
        body = decoded(response)
        self.assertEqual(body["supportedInterfaces"], [])
        self.assertEqual({skill["id"] for skill in body["skills"]}, {"protocol_status", "sandbox_demo"})
        self.assertNotIn("release_escrow", response.body.decode().casefold())
        self.assertNotIn("create_escrow", response.body.decode().casefold())

    def test_a2a_status_and_sandbox_messages(self):
        status = decoded(
            a2a_send_message(
                {"message": {"role": "ROLE_USER", "messageId": "m1", "parts": [{"text": "Is mainnet accepting funds?"}]}},
                "1.0",
            )
        )
        self.assertEqual(status["task"]["status"]["state"], "TASK_STATE_COMPLETED")
        data = status["task"]["artifacts"][0]["parts"][1]["data"]
        self.assertFalse(data["production"]["accepting_funds"])

        demo = decoded(
            a2a_send_message(
                {"message": {"role": "ROLE_USER", "messageId": "m2", "parts": [{"text": "Show wallet-free demo"}]}},
                "1.0",
            )
        )
        demo_data = demo["task"]["artifacts"][0]["parts"][1]["data"]
        self.assertEqual(demo_data["skill"], "sandbox_demo")
        self.assertFalse(demo_data["real_money"])

    def test_a2a_rejects_bad_version_and_missing_text(self):
        unsupported = decoded(
            a2a_send_message({"message": {"parts": [{"text": "status"}]}}, "0.3")
        )
        self.assertEqual(unsupported["status"], 400)
        self.assertEqual(unsupported["supportedVersions"], ["1.0"])
        with self.assertRaises(HTTPException):
            a2a_send_message({}, "1.0")
        with self.assertRaises(HTTPException):
            a2a_send_message({"message": {"parts": [{"data": {}}]}}, "1.0")

    def test_llms_file_is_truthful(self):
        response = llms_txt()
        text = response.body.decode("utf-8")
        self.assertIn("Public launch: 23 October 2026", text)
        self.assertIn("Public mainnet funding:", text)
        self.assertNotIn("Mainnet deposits: closed", text)
        self.assertIn("/.well-known/agent-card.json", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
