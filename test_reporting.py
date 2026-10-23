import os
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from unittest.mock import MagicMock

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
import launch_analytics


class ReportingTest(unittest.TestCase):
    def tearDown(self):
        reporting._LOGIN_ATTEMPTS.clear()

    def test_morning_window_uses_midnight(self):
        now = datetime(2026, 9, 20, 5, 5, tzinfo=timezone.utc)  # 08:05 Istanbul
        with patch.dict(os.environ, {"REPORT_TIMEZONE": "Europe/Istanbul"}, clear=False):
            start, end = reporting.scheduled_window(now)
        self.assertEqual(start.isoformat(), "2026-09-20T00:00:00+03:00")
        self.assertEqual(end.isoformat(), "2026-09-20T08:00:00+03:00")

    def test_midnight_window_uses_previous_morning(self):
        now = datetime(2026, 9, 19, 21, 5, tzinfo=timezone.utc)  # 00:05 Istanbul
        with patch.dict(os.environ, {"REPORT_TIMEZONE": "Europe/Istanbul"}, clear=False):
            start, end = reporting.scheduled_window(now)
        self.assertEqual(start.isoformat(), "2026-09-19T08:00:00+03:00")
        self.assertEqual(end.isoformat(), "2026-09-20T00:00:00+03:00")

    def test_dashboard_windows_include_requested_comparisons(self):
        now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        windows = reporting._dashboard_windows(now)
        for key in ("today", "yesterday", "last_7_days", "previous_7_days",
                    "last_21_days", "previous_21_days", "month", "previous_month",
                    "year", "previous_year_same_period", "all"):
            self.assertIn(key, windows)

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

    def test_dashboard_path_requires_a_long_matching_secret(self):
        with patch.dict(os.environ, {"REPORT_DASHBOARD_PATH": "private-path-key-that-is-long-enough"}, clear=False):
            self.assertTrue(reporting._dashboard_path_matches("private-path-key-that-is-long-enough"))
            self.assertFalse(reporting._dashboard_path_matches("wrong"))

    def test_login_failures_are_rate_limited(self):
        for second in range(reporting.LOGIN_MAX_FAILURES):
            reporting._record_login_failure("test-client", now=float(second))
        with self.assertRaises(HTTPException) as limited:
            reporting._check_login_limit("test-client", now=10.0)
        self.assertEqual(limited.exception.status_code, 429)

    def test_render_text_contains_money_and_attention_items(self):
        report = {
            "window_start": "2026-09-19T08:00:00+03:00",
            "window_end": "2026-09-20T00:00:00+03:00",
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

    def test_visitor_analytics_stores_no_ip_and_reports_country(self):
        path = os.path.join(os.path.dirname(__file__), ".test-tmp", "analytics-reporting-test.sqlite3")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass
        with patch.dict(os.environ, {
            "ANALYTICS_ENABLED": "true",
            "ANALYTICS_DB_PATH": path,
            "ANALYTICS_COUNTRY_HEADER": "cf-ipcountry",
            "ANALYTICS_RETENTION_DAYS": "760",
        }, clear=False):
            request = MagicMock()
            request.client.host = "203.0.113.9"
            request.headers = {"cf-ipcountry": "TR"}
            launch_analytics.record_launch_event(launch_analytics.LaunchEvent(
                event="page_view", path="/mainnet", session_id="session1234"
            ), request)
            launch_analytics.record_launch_event(launch_analytics.LaunchEvent(
                event="page_exit", path="/mainnet", session_id="session1234", duration_seconds=42
            ), request)
            summary = launch_analytics.analytics_summary()
            self.assertTrue(summary["available"])
            self.assertEqual(summary["periods"]["all"]["visitors"], 1)
            self.assertEqual(summary["periods"]["all"]["average_session_seconds"], 42)
            self.assertEqual(summary["countries"][0], {"country": "TR", "visitors": 1})
            db = launch_analytics._connect()
            try:
                columns = {row[1] for row in db.execute("PRAGMA table_info(analytics_events)")}
            finally:
                db.close()
            self.assertNotIn("ip", columns)
            self.assertNotIn("wallet", columns)
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass

    def test_disabled_analytics_writes_nothing(self):
        path = os.path.join(os.path.dirname(__file__), ".test-tmp", "analytics-disabled.sqlite3")
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        request = MagicMock()
        request.client.host = "203.0.113.10"
        request.headers = {"cf-ipcountry": "TR"}
        with patch.dict(os.environ, {
            "ANALYTICS_ENABLED": "false",
            "ANALYTICS_DB_PATH": path,
            "ANALYTICS_COUNTRY_HEADER": "cf-ipcountry",
        }, clear=False):
            response = launch_analytics.record_launch_event(launch_analytics.LaunchEvent(
                event="page_view", path="/", session_id="disabled123"
            ), request)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(os.path.exists(path))

    def test_country_header_is_ignored_until_explicitly_trusted(self):
        request = MagicMock()
        request.headers = {"cf-ipcountry": "TR"}
        with patch.dict(os.environ, {"ANALYTICS_COUNTRY_HEADER": ""}, clear=False):
            self.assertIsNone(launch_analytics._country(request))
        with patch.dict(os.environ, {"ANALYTICS_COUNTRY_HEADER": "cf-ipcountry"}, clear=False):
            self.assertEqual(launch_analytics._country(request), "TR")

    def test_analytics_retention_removes_expired_events(self):
        path = os.path.join(os.path.dirname(__file__), ".test-tmp", "analytics-retention.sqlite3")
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass
        request = MagicMock()
        request.client.host = "203.0.113.11"
        request.headers = {}
        now = 2_000_000_000
        with patch.dict(os.environ, {
            "ANALYTICS_ENABLED": "true",
            "ANALYTICS_DB_PATH": path,
            "ANALYTICS_RETENTION_DAYS": "30",
        }, clear=False):
            db = launch_analytics._connect()
            db.execute(
                "INSERT INTO analytics_events (session_id,event,path,language,campaign,country,duration_seconds,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                ("oldsession", "page_view", "/", "en", "", None, 0, now - 31 * 86_400),
            )
            db.commit()
            db.close()
            with patch("launch_analytics.time.time", return_value=now):
                launch_analytics.record_launch_event(launch_analytics.LaunchEvent(
                    event="page_view", path="/", session_id="newsession"
                ), request)
            db = launch_analytics._connect()
            rows = db.execute("SELECT session_id FROM analytics_events ORDER BY session_id").fetchall()
            db.close()
        self.assertEqual(rows, [("newsession",)])
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
