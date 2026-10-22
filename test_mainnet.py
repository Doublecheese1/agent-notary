import os
import inspect
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app
from mainnet import mainnet_units, prepare_action, transaction


class MainnetRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_mainnet_page_and_disabled_config_are_safe(self):
        with patch.dict(os.environ, {"MAINNET_ENABLED": "false", "MAINNET_ACCEPTING_FUNDS": "false"}):
            page = self.client.get("/mainnet")
            self.assertEqual(page.status_code, 200)
            self.assertIn("Public interface preview", page.text)
            self.assertNotIn('id="resolverRole"', page.text)
            response = self.client.get("/mainnet/config")
        body = response.json()
        self.assertFalse(body["enabled"])
        self.assertFalse(body["accepting_funds"])
        self.assertEqual(body["protocol_fee_bps"], 150)
        self.assertEqual(body["protocol_fee_cap_units"], 50_000_000)

    def test_funding_cannot_be_prepared_while_gate_is_closed(self):
        with patch.dict(os.environ, {"MAINNET_ACCEPTING_FUNDS": "false"}):
            response = self.client.post("/mainnet/prepare-proposal", json={
                "buyer": "0x0000000000000000000000000000000000000001",
                "seller": "0x0000000000000000000000000000000000000002",
                "mode": "automatic", "amount": "10", "salt": "0x" + "11" * 32,
                "manifest": "{}", "policy_hash": "0x" + "22" * 32,
                "fallback_seller_bps": 0, "acceptance_window": 3600,
                "delivery_window": 3600, "decision_window": 3600, "arbitration_window": 3600,
            })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Mainnet deposits are not open yet.")

    def test_browser_code_never_contains_a_private_key_field(self):
        response = self.client.get("/mainnet/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("privateKey", response.text)

    def test_validator_console_uses_wallet_signatures_without_private_keys(self):
        page = self.client.get("/mainnet/validator")
        script = self.client.get("/mainnet/validator.js")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(script.status_code, 200)
        self.assertIn("eth_signTypedData_v4", script.text)
        self.assertNotIn("privateKey", page.text + script.text)

    def test_closing_new_deposits_does_not_disable_existing_deal_actions(self):
        self.assertNotIn("require_accepting()", inspect.getsource(prepare_action))

    def test_mainnet_transaction_uses_arbitrum_one_chain_id(self):
        prepared = transaction(
            "0x0000000000000000000000000000000000000001",
            "0x0000000000000000000000000000000000000002",
            "0x1234",
        )
        self.assertEqual(prepared["chainId"], "0xa4b1")
        self.assertNotEqual(prepared["chainId"], "0x66eee")

    def test_mainnet_amount_parser_has_no_1000_usdc_cap(self):
        self.assertEqual(mainnet_units("5000"), 5_000_000_000)

    def test_public_mainnet_disclosures_are_available(self):
        self.assertEqual(self.client.get("/terms").status_code, 200)
        self.assertEqual(self.client.get("/privacy").status_code, 200)
        offer = self.client.get("/mainnet/founding50")
        self.assertEqual(offer.status_code, 200)
        self.assertIn("30 days", offer.text)
        self.assertIn("protocol fee", offer.text)

    def test_founder_deployment_gate_is_closed_by_default(self):
        with patch.dict(os.environ, {"MAINNET_DEPLOYMENT_UI": "false"}):
            page = self.client.get("/mainnet/setup")
            status = self.client.get("/mainnet/setup-status")
            prepared = self.client.post("/mainnet/prepare-quorum-deployment", json={
                "deployer": "0x0000000000000000000000000000000000000001",
                "signer_a": "0x0000000000000000000000000000000000000002",
                "signer_b": "0x0000000000000000000000000000000000000003",
                "signer_c": "0x0000000000000000000000000000000000000004",
            })
        self.assertEqual(page.status_code, 404)
        self.assertFalse(status.json()["enabled"])
        self.assertEqual(prepared.status_code, 503)

    def test_founder_deployment_is_locked_to_the_approved_wallet(self):
        approved = "0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD"
        request = {
            "deployer": "0x0000000000000000000000000000000000000001",
            "signer_a": "0x0000000000000000000000000000000000000002",
            "signer_b": "0x0000000000000000000000000000000000000003",
            "signer_c": "0x0000000000000000000000000000000000000004",
        }
        with patch.dict(os.environ, {
            "MAINNET_DEPLOYMENT_UI": "true",
            "MAINNET_DEPLOYER_ADDRESS": approved,
        }):
            status = self.client.get("/mainnet/setup-status")
            wrong = self.client.post("/mainnet/prepare-quorum-deployment", json=request)
            request["deployer"] = approved
            correct = self.client.post("/mainnet/prepare-quorum-deployment", json=request)
        self.assertTrue(status.json()["enabled"])
        self.assertEqual(status.json()["deployer"], approved)
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(correct.status_code, 200)
        self.assertEqual(correct.json()["transaction"]["from"], approved)

    def test_founder_operations_gate_is_closed_by_default(self):
        self.assertEqual(self.client.get("/mainnet/operations").status_code, 200)
        with patch.dict(os.environ, {"MAINNET_OPERATIONS_UI": "false"}):
            status = self.client.get("/mainnet/operations-status")
            prepared = self.client.post("/mainnet/prepare-operations-action", json={
                "action": "admitFoundingBuyer",
                "buyer": "0x0000000000000000000000000000000000000001",
            })
        self.assertFalse(status.json()["enabled"])
        self.assertEqual(prepared.status_code, 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
