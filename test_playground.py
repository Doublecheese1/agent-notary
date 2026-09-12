import copy
import hashlib
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient
import legacy
import main
import playground


class PlaygroundTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        legacy.DEALS_DB.clear()
        playground.engine.DEALS_DB.clear()
        for engine in (legacy, playground.engine):
            for key in ("total_settled_volume_usd", "total_commission_earned_usd", "total_transactions"):
                engine.PLATFORM_TREASURY[key] = 0
        self.body = dict(buyer_agent_id="buyer", seller_agent_id="seller", amount_usd=1, criteria="50 items required")

    def lock(self, prefix="/sandbox", **updates):
        return self.client.post(prefix + "/v1/deals/lock", json=self.body | updates)

    def settle(self, deal, payload, prefix="/sandbox", seller="seller"):
        return self.client.post(prefix + "/v1/deals/settle", json=dict(deal_id=deal, seller_agent_id=seller, deliverable=payload))

    def test_success_and_isolation(self):
        treasury = copy.deepcopy(legacy.PLATFORM_TREASURY)
        locked = self.lock()
        self.assertEqual(locked.status_code, 201)
        self.assertEqual(locked.json()["locked_amount_usd"], 1.005)
        payload = {"result": "Valid result"}
        result = self.settle(locked.json()["deal_id"], payload).json()
        self.assertEqual(result["decision"], "APPROVED")
        self.assertEqual(result["seller_payout_usd"], .985)
        self.assertEqual(result["protocol_fee_usd"], .020)
        self.assertEqual(result["refund_to_buyer_usd"], 0)
        self.assertEqual(result["proof_hash"], hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
        self.assertEqual(legacy.DEALS_DB, {})
        self.assertEqual(legacy.PLATFORM_TREASURY, treasury)

    def test_failure_retains_fixed_fee(self):
        deal = self.lock().json()["deal_id"]
        response = self.settle(deal, {"status": "COMPLETED", "records": 50})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["decision"], "REJECTED")
        self.assertEqual(result["protocol_fee_usd"], .005)
        self.assertEqual(result["refund_to_buyer_usd"], 1)
        self.assertEqual(result["seller_payout_usd"], 0)

    def test_legacy_schema_unchanged(self):
        original = legacy.app.openapi()
        current = main.app.openapi()
        for path, schema in original["paths"].items():
            self.assertEqual(schema, current["paths"][path])
        self.assertEqual(original["components"], current["components"])

    def test_legacy_sandbox_parity(self):
        for amount in (1, .001, .1, 10, 1.23456):
            for payload in ({}, {"records": 50}, {"result": "abc"}, {"data": []}, {"result": []}, {"result": None}, {"result": "long enough"}, {"data": [1]}):
                with self.subTest(amount=amount, payload=payload):
                    real = self.lock("", amount_usd=amount).json()
                    demo = self.lock(amount_usd=amount).json()
                    self.assertEqual(real["locked_amount_usd"], demo["locked_amount_usd"])
                    self.assertEqual(self.settle(real["deal_id"], payload, "").json(), self.settle(demo["deal_id"], payload).json())

    def test_ownership_missing_finalized_and_cross_store(self):
        deal = self.lock().json()["deal_id"]
        self.assertEqual(self.settle(deal, {}, seller="other").status_code, 403)
        self.assertEqual(self.settle(deal, {}, "").status_code, 404)
        self.assertEqual(self.settle("missing", {}).status_code, 404)
        self.settle(deal, {})
        self.assertEqual(self.settle(deal, {}).status_code, 400)
        live = self.lock("").json()["deal_id"]
        self.assertEqual(self.settle(live, {}).status_code, 404)

    def test_bad_requests(self):
        for amount in (0, -1):
            self.assertEqual(self.lock(amount_usd=amount).status_code, 422)
        self.assertEqual(self.client.post("/sandbox/v1/deals/lock", json={}).status_code, 422)
        self.assertEqual(self.client.post("/sandbox/v1/deals/settle", json={}).status_code, 422)

    def test_retention_and_capacity(self):
        deal = self.lock().json()["deal_id"]
        with patch.object(playground, "MAX_DEALS", 1):
            self.assertEqual(self.lock().status_code, 429)
        playground.engine.DEALS_DB[deal]["created_at"] -= 901
        self.assertEqual(self.settle(deal, {}).status_code, 404)
        self.assertEqual(self.lock().status_code, 201)

    def test_concurrent_settlement_only_counts_once(self):
        deal = self.lock().json()["deal_id"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(lambda _: self.settle(deal, {"result": "Valid result"}).status_code, range(4)))
        self.assertEqual(sorted(codes), [200, 400, 400, 400])
        self.assertEqual(playground.engine.PLATFORM_TREASURY["total_transactions"], 1)

    def test_page_and_assets(self):
        self.assertEqual(self.client.get("/play").status_code, 200)
        self.assertIn("Buyer", self.client.get("/play").text.upper().title())
        self.assertEqual(self.client.get("/play/app.js").status_code, 200)
        self.assertFalse(self.client.get("/sandbox/health").json()["real_money"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
