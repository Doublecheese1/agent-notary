import os
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
HAS_WEB3 = importlib.util.find_spec("web3") is not None
HAS_MAINNET = importlib.util.find_spec("mainnet") is not None

if not HAS_FASTAPI:
    fastapi_stub = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code, self.detail = status_code, detail

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return lambda function: function

        def get(self, *args, **kwargs):
            return lambda function: function

    class Response:
        pass

    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.APIRouter = APIRouter
    fastapi_stub.Header = lambda default=None: default
    fastapi_stub.Body = lambda default=None: default
    fastapi_stub.Cookie = lambda default=None: default
    fastapi_stub.Response = Response
    sys.modules["fastapi"] = fastapi_stub
else:
    from fastapi import HTTPException

if not HAS_WEB3:
    web3_stub = types.ModuleType("web3")
    web3_stub.Web3 = type("Web3", (), {})
    sys.modules["web3"] = web3_stub

if not HAS_MAINNET or not HAS_FASTAPI or not HAS_WEB3:
    mainnet_stub = types.ModuleType("mainnet")
    mainnet_stub.connection = lambda: (_ for _ in ()).throw(RuntimeError("not used in unit tests"))
    sys.modules["mainnet"] = mainnet_stub

import reporting


class ReportingTest(unittest.TestCase):
    def tearDown(self):
        reporting._LOGIN_ATTEMPTS.clear()

    def test_morning_window_uses_previous_evening(self):
        now = datetime(2026, 9, 20, 6, 5, tzinfo=timezone.utc)  # 09:05 Istanbul
        with patch.dict(os.environ, {"REPORT_TIMEZONE": "Europe/Istanbul"}, clear=False):
            start, end = reporting.scheduled_window(now)
        self.assertEqual(start.isoformat(), "2026-09-19T20:00:00+03:00")
        self.assertEqual(end.isoformat(), "2026-09-20T09:00:00+03:00")

    def test_evening_window_uses_same_day_morning(self):
        now = datetime(2026, 9, 20, 17, 5, tzinfo=timezone.utc)  # 20:05 Istanbul
        with patch.dict(os.environ, {"REPORT_TIMEZONE": "Europe/Istanbul"}, clear=False):
            start, end = reporting.scheduled_window(now)
        self.assertEqual(start.isoformat(), "2026-09-20T09:00:00+03:00")
        self.assertEqual(end.isoformat(), "2026-09-20T20:00:00+03:00")

    def test_authorization_requires_enabled_matching_token(self):
        with patch.dict(os.environ, {
            "REPORTING_ENABLED": "true",
            "REPORT_TRIGGER_TOKEN": "correct-token",
        }, clear=False):
            reporting._authorize("correct-token")
            with self.assertRaises(HTTPException) as wrong:
                reporting._authorize("wrong-token")
            self.assertEqual(wrong.exception.status_code, 404)

    def test_authorization_stays_closed_when_disabled(self):
        with patch.dict(os.environ, {
            "REPORTING_ENABLED": "false",
            "REPORT_TRIGGER_TOKEN": "correct-token",
        }, clear=False):
            with self.assertRaises(HTTPException) as disabled:
                reporting._authorize("correct-token")
            self.assertEqual(disabled.exception.status_code, 404)

    def test_dashboard_session_expires_and_rejects_tampering(self):
        with patch.dict(os.environ, {
            "REPORTING_ENABLED": "true",
            "REPORT_SESSION_SECRET": "a-secure-test-secret-that-is-long-enough",
        }, clear=False):
            session = reporting._make_session(now=1_000)
            reporting._authorize_session(session, now=1_001)
            with self.assertRaises(HTTPException):
                reporting._authorize_session(session + "bad", now=1_001)
            with self.assertRaises(HTTPException):
                reporting._authorize_session(session, now=50_000)

    def test_login_failures_are_rate_limited(self):
        for second in range(reporting.LOGIN_MAX_FAILURES):
            reporting._record_login_failure("test-client", now=float(second))
        with self.assertRaises(HTTPException) as limited:
            reporting._check_login_limit("test-client", now=10.0)
        self.assertEqual(limited.exception.status_code, 429)

    def test_render_text_contains_money_and_attention_items(self):
        report = {
            "window_start": "2026-09-19T20:00:00+03:00",
            "window_end": "2026-09-20T09:00:00+03:00",
            "start_block": 1, "end_block": 2, "transactions": 3,
            "proposed": 1, "accepted": 1, "delivered": 1, "closed": 1,
            "disputed": 1, "validations": 2, "open_deals": 1,
            "proposed_volume": "100.00", "seller_paid": "98.50",
            "buyer_paid": "0.00", "protocol_fees": "1.50",
            "lifetime_protocol_fees": "4.50", "resolver_paid": "0.00",
            "total_escrowed": "10.00", "treasury_balance": "4.50",
            "owner_withdrawn": "1.00", "lifetime_owner_withdrawn": "2.00",
            "owner_payout_configured": True,
            "unresolved_disputes": ["0xabc"], "escrow": "0xescrow",
            "ai_attention": [{"deal_id": "0xdef", "status": "HUMAN_REVIEW", "reason": "AI reviewers disagreed"}],
            "treasury": "0xtreasury",
        }
        text = reporting.render_text(report)
        self.assertIn("Protocol fees this period: 1.50 USDC", text)
        self.assertIn("0xabc", text)
        self.assertIn("0xdef", text)
        self.assertIn("does not move funds or sign transactions", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
