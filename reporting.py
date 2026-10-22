"""Read-only Arbitrum reporting and SMTP delivery. No wallet or signing key is used."""
from __future__ import annotations

import html
import hashlib
import hmac
import os
import secrets
import smtplib
import time as clock
from datetime import datetime, time, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, Cookie, Header, HTTPException, Request, Response
from web3 import Web3

from mainnet import connection
from ai_review import attention_queue as ai_attention_queue

router = APIRouter(prefix="/internal/reporting", tags=["Internal reporting"])
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5
USDC = 10**6
STATES = ["NONE", "PROPOSED", "LOCKED", "DELIVERED", "DISPUTED", "PAID", "REFUNDED", "FINALIZED_SPLIT"]
TOKEN_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
]


def reporting_enabled() -> bool:
    return os.getenv("REPORTING_ENABLED", "false").lower() == "true"


def scheduled_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return the last completed 09:00/20:00 Europe/Istanbul report interval."""
    zone = ZoneInfo(os.getenv("REPORT_TIMEZONE", "Europe/Istanbul"))
    local = (now or datetime.now(timezone.utc)).astimezone(zone)
    today = local.date()
    nine = datetime.combine(today, time(9), zone)
    twenty = datetime.combine(today, time(20), zone)
    if local >= twenty:
        return nine, twenty
    if local >= nine:
        return datetime.combine(today - timedelta(days=1), time(20), zone), nine
    return datetime.combine(today - timedelta(days=1), time(9), zone), datetime.combine(today - timedelta(days=1), time(20), zone)


def _first_block_at_or_after(w3: Web3, timestamp: int, floor: int, ceiling: int) -> int:
    low, high = floor, ceiling
    while low < high:
        mid = (low + high) // 2
        if int(w3.eth.get_block(mid)["timestamp"]) < timestamp:
            low = mid + 1
        else:
            high = mid
    return low


def _last_block_at_or_before(w3: Web3, timestamp: int, floor: int, ceiling: int) -> int:
    low, high = floor, ceiling
    while low < high:
        mid = (low + high + 1) // 2
        if int(w3.eth.get_block(mid)["timestamp"]) <= timestamp:
            low = mid
        else:
            high = mid - 1
    return low


def _logs(event, start: int, end: int):
    return event.get_logs(from_block=start, to_block=end) if start <= end else []


def _amount(value: int) -> str:
    return f"{value / USDC:,.2f}"


def _deployment_block() -> int:
    value = int(os.getenv("MAINNET_DEPLOYMENT_BLOCK", "0"))
    if value <= 0:
        raise HTTPException(503, "Configure MAINNET_DEPLOYMENT_BLOCK before enabling reports.")
    return value


def _token_contract(w3: Web3, contract):
    return w3.eth.contract(address=contract.functions.token().call(), abi=TOKEN_ABI)


def _owner_payout_address() -> str | None:
    value = os.getenv("REPORT_OWNER_PAYOUT_ADDRESS", "").strip()
    if not value:
        return None
    if not Web3.is_address(value):
        raise HTTPException(503, "REPORT_OWNER_PAYOUT_ADDRESS is not a valid address.")
    return Web3.to_checksum_address(value)


def _withdrawal_logs(token, treasury: str, owner: str | None, start: int, end: int):
    if not owner or start > end:
        return []
    return token.events.Transfer().get_logs(
        from_block=start,
        to_block=end,
        argument_filters={"from": Web3.to_checksum_address(treasury), "to": owner},
    )


def _session_secret() -> bytes:
    value = os.getenv("REPORT_SESSION_SECRET", "")
    if len(value) < 32:
        raise HTTPException(503, "Configure a REPORT_SESSION_SECRET of at least 32 characters.")
    return value.encode("utf-8")


def _make_session(now: int | None = None) -> str:
    expires = int(now or clock.time()) + 12 * 60 * 60
    payload = str(expires)
    signature = hmac.new(_session_secret(), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _authorize_session(value: str | None, now: int | None = None) -> None:
    if not reporting_enabled() or not value:
        raise HTTPException(401, "Sign in required")
    try:
        expires_text, signature = value.split(".", 1)
        expires = int(expires_text)
    except (ValueError, AttributeError):
        raise HTTPException(401, "Sign in required") from None
    expected = hmac.new(_session_secret(), expires_text.encode("ascii"), hashlib.sha256).hexdigest()
    if expires < int(now or clock.time()) or not secrets.compare_digest(signature, expected):
        raise HTTPException(401, "Session expired")


def _login_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_login_limit(key: str, now: float | None = None) -> None:
    current = float(now if now is not None else clock.monotonic())
    recent = [item for item in _LOGIN_ATTEMPTS.get(key, []) if current - item < LOGIN_WINDOW_SECONDS]
    _LOGIN_ATTEMPTS[key] = recent
    if len(recent) >= LOGIN_MAX_FAILURES:
        raise HTTPException(429, "Too many login attempts. Try again later.")


def _record_login_failure(key: str, now: float | None = None) -> None:
    _check_login_limit(key, now)
    _LOGIN_ATTEMPTS.setdefault(key, []).append(float(now if now is not None else clock.monotonic()))


def _period_start_blocks(w3: Web3, deployment_block: int, latest: int, now_local: datetime) -> dict[str, int]:
    zone = now_local.tzinfo
    starts = {
        "today": datetime.combine(now_local.date(), time.min, zone),
        "week": datetime.combine(now_local.date() - timedelta(days=now_local.weekday()), time.min, zone),
        "month": datetime(now_local.year, now_local.month, 1, tzinfo=zone),
        "year": datetime(now_local.year, 1, 1, tzinfo=zone),
    }
    deployment_time = int(w3.eth.get_block(deployment_block)["timestamp"])
    latest_time = int(w3.eth.get_block(latest)["timestamp"])
    result = {"all": deployment_block}
    for name, start in starts.items():
        timestamp = int(start.timestamp())
        if timestamp <= deployment_time:
            result[name] = deployment_block
        elif timestamp > latest_time:
            result[name] = latest + 1
        else:
            result[name] = _first_block_at_or_after(w3, timestamp, deployment_block, latest)
    return result


def collect_dashboard(now: datetime | None = None) -> dict:
    w3, contract = connection()
    deployment_block = _deployment_block()
    latest = w3.eth.block_number
    zone = ZoneInfo(os.getenv("REPORT_TIMEZONE", "Europe/Istanbul"))
    now_local = (now or datetime.now(timezone.utc)).astimezone(zone)
    starts = _period_start_blocks(w3, deployment_block, latest, now_local)
    proposed = _logs(contract.events.DealProposed(), deployment_block, latest)
    disputed = _logs(contract.events.DealDisputed(), deployment_block, latest)
    closed = _logs(contract.events.DealClosed(), deployment_block, latest)
    treasury = contract.functions.treasurySafe().call(block_identifier=latest)
    token = _token_contract(w3, contract)
    owner = _owner_payout_address()
    withdrawals = _withdrawal_logs(token, treasury, owner, deployment_block, latest)

    def period(first_block: int) -> dict:
        period_proposed = [item for item in proposed if int(item["blockNumber"]) >= first_block]
        period_disputed = [item for item in disputed if int(item["blockNumber"]) >= first_block]
        period_closed = [item for item in closed if int(item["blockNumber"]) >= first_block]
        period_withdrawals = [item for item in withdrawals if int(item["blockNumber"]) >= first_block]
        return {
            "volume": _amount(sum(int(item["args"]["amount"]) for item in period_proposed)),
            "earned": _amount(sum(int(item["args"]["treasuryAmount"]) for item in period_closed)),
            "withdrawn": _amount(sum(int(item["args"]["value"]) for item in period_withdrawals)),
            "deals": len(period_proposed),
            "closed": len(period_closed),
            "disputes": len(period_disputed),
        }

    open_ids = {log["args"]["id"] for log in proposed} - {log["args"]["id"] for log in closed}
    unresolved = []
    for deal_id in open_ids:
        deal = contract.functions.deals(deal_id).call(block_identifier=latest)
        if int(deal[4]) == 4:
            unresolved.append(Web3.to_hex(deal_id))
    return {
        "generated_at": now_local.isoformat(),
        "escrow": contract.address,
        "treasury": treasury,
        "owner_payout": owner,
        "owner_payout_configured": owner is not None,
        "treasury_balance": _amount(int(token.functions.balanceOf(treasury).call(block_identifier=latest))),
        "currently_escrowed": _amount(int(contract.functions.totalEscrowed().call(block_identifier=latest))),
        "open_deals": len(open_ids),
        "unresolved_disputes": unresolved,
        "ai_attention": ai_attention_queue(),
        "periods": {name: period(first_block) for name, first_block in starts.items()},
    }


def collect_report(now: datetime | None = None) -> dict:
    w3, contract = connection()
    deployment_block = _deployment_block()
    start_local, end_local = scheduled_window(now)
    latest = w3.eth.block_number
    start_block = _first_block_at_or_after(w3, int(start_local.timestamp()), deployment_block, latest)
    end_timestamp = min(int(end_local.timestamp()), int(w3.eth.get_block(latest)["timestamp"]))
    end_block = _last_block_at_or_before(w3, end_timestamp, deployment_block, latest)

    proposed = _logs(contract.events.DealProposed(), start_block, end_block)
    accepted = _logs(contract.events.DealAccepted(), start_block, end_block)
    delivered = _logs(contract.events.DealDelivered(), start_block, end_block)
    disputed = _logs(contract.events.DealDisputed(), start_block, end_block)
    validations = _logs(contract.events.ValidationRecorded(), start_block, end_block)
    closed = _logs(contract.events.DealClosed(), start_block, end_block)

    all_proposed = _logs(contract.events.DealProposed(), deployment_block, end_block)
    all_closed = _logs(contract.events.DealClosed(), deployment_block, end_block)
    open_ids = {log["args"]["id"] for log in all_proposed} - {log["args"]["id"] for log in all_closed}
    unresolved_disputes = []
    for deal_id in open_ids:
        deal = contract.functions.deals(deal_id).call(block_identifier=end_block)
        if int(deal[4]) == 4:
            unresolved_disputes.append(Web3.to_hex(deal_id))

    seller_paid = sum(int(log["args"]["sellerAmount"]) for log in closed)
    buyer_paid = sum(int(log["args"]["buyerAmount"]) for log in closed)
    fees = sum(int(log["args"]["treasuryAmount"]) for log in closed)
    resolver_paid = sum(int(log["args"]["resolverAmount"]) for log in closed)
    lifetime_fees = sum(int(log["args"]["treasuryAmount"]) for log in all_closed)
    proposed_volume = sum(int(log["args"]["amount"]) for log in proposed)
    token = _token_contract(w3, contract)
    treasury = contract.functions.treasurySafe().call(block_identifier=end_block)
    owner = _owner_payout_address()
    period_withdrawals = _withdrawal_logs(token, treasury, owner, start_block, end_block)
    lifetime_withdrawals = _withdrawal_logs(token, treasury, owner, deployment_block, end_block)
    tx_hashes = {log["transactionHash"].hex() for group in (proposed, accepted, delivered, disputed, validations, closed) for log in group}
    return {
        "window_start": start_local.isoformat(), "window_end": end_local.isoformat(),
        "start_block": start_block, "end_block": end_block,
        "transactions": len(tx_hashes), "proposed": len(proposed), "accepted": len(accepted),
        "delivered": len(delivered), "disputed": len(disputed), "closed": len(closed),
        "validations": len(validations), "open_deals": len(open_ids),
        "unresolved_disputes": unresolved_disputes,
        "ai_attention": ai_attention_queue(),
        "proposed_volume": _amount(proposed_volume), "seller_paid": _amount(seller_paid),
        "buyer_paid": _amount(buyer_paid), "protocol_fees": _amount(fees),
        "resolver_paid": _amount(resolver_paid), "lifetime_protocol_fees": _amount(lifetime_fees),
        "owner_withdrawn": _amount(sum(int(log["args"]["value"]) for log in period_withdrawals)),
        "lifetime_owner_withdrawn": _amount(sum(int(log["args"]["value"]) for log in lifetime_withdrawals)),
        "owner_payout_configured": owner is not None,
        "total_escrowed": _amount(int(contract.functions.totalEscrowed().call(block_identifier=end_block))),
        "treasury_balance": _amount(int(token.functions.balanceOf(treasury).call(block_identifier=end_block))),
        "escrow": contract.address, "treasury": treasury,
    }


def render_text(report: dict) -> str:
    attention = "None" if not report["unresolved_disputes"] else "\n".join(f"- {item}" for item in report["unresolved_disputes"])
    ai_attention = "None" if not report["ai_attention"] else "\n".join(
        f"- {item['deal_id']} — {item['status']} — {item.get('reason') or 'Awaiting AI evaluations'}"
        for item in report["ai_attention"]
    )
    return f"""AgentSolis Report
Period: {report['window_start']} — {report['window_end']}
Blocks: {report['start_block']} — {report['end_block']}

Transactions: {report['transactions']}
New deals: {report['proposed']}
Accepted: {report['accepted']}
Delivered: {report['delivered']}
Closed: {report['closed']}
New disputes: {report['disputed']}
Validator decisions: {report['validations']}
Open deals: {report['open_deals']}

Proposed volume: {report['proposed_volume']} USDC
Seller payments: {report['seller_paid']} USDC
Buyer payments/refunds: {report['buyer_paid']} USDC
Protocol fees this period: {report['protocol_fees']} USDC
Lifetime protocol fees: {report['lifetime_protocol_fees']} USDC
Owner withdrawals this period: {report['owner_withdrawn']} USDC
Lifetime owner withdrawals: {report['lifetime_owner_withdrawn']} USDC
Resolver payments: {report['resolver_paid']} USDC
Currently escrowed: {report['total_escrowed']} USDC
Treasury balance: {report['treasury_balance']} USDC

Human attention — unresolved disputes:
{attention}

AI review queue requiring attention:
{ai_attention}

Escrow: {report['escrow']}
Treasury: {report['treasury']}
This is a read-only operational report. It does not move funds or sign transactions.
"""


def send_email(report: dict) -> None:
    recipient = os.getenv("REPORT_RECIPIENT", "").strip()
    sender = os.getenv("REPORT_SMTP_USER", "").strip()
    password = os.getenv("REPORT_SMTP_APP_PASSWORD", "")
    host = os.getenv("REPORT_SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("REPORT_SMTP_PORT", "465"))
    if not recipient or not sender or not password:
        raise HTTPException(503, "Configure report recipient and SMTP credentials.")
    message = EmailMessage()
    message["Subject"] = f"AgentSolis report — {report['window_end'][0:16]}"
    message["From"], message["To"] = sender, recipient
    text = render_text(report)
    message.set_content(text)
    message.add_alternative(f"<html><body><pre style='font:14px/1.5 system-ui;white-space:pre-wrap'>{html.escape(text)}</pre></body></html>", subtype="html")
    with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def _authorize(token: str | None) -> None:
    expected = os.getenv("REPORT_TRIGGER_TOKEN", "")
    if not reporting_enabled() or not expected or not token or not secrets.compare_digest(token, expected):
        raise HTTPException(404, "Not found")


@router.post("/send", include_in_schema=False)
def send_scheduled_report(x_agentnotary_report_token: str | None = Header(default=None)):
    _authorize(x_agentnotary_report_token)
    report = collect_report()
    send_email(report)
    return {"sent": True, "window_start": report["window_start"], "window_end": report["window_end"]}


@router.post("/login", include_in_schema=False)
def dashboard_login(request: Request, response: Response, payload: dict = Body(...)):
    key = _login_key(request)
    _check_login_limit(key)
    expected = os.getenv("REPORT_DASHBOARD_PASSWORD", "")
    supplied = str(payload.get("password", ""))
    if not reporting_enabled() or len(expected) < 12 or not secrets.compare_digest(supplied, expected):
        _record_login_failure(key)
        raise HTTPException(401, "Wrong password")
    _LOGIN_ATTEMPTS.pop(key, None)
    response.set_cookie(
        "agentnotary_report_session",
        _make_session(),
        max_age=12 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"signed_in": True}


@router.post("/logout", include_in_schema=False)
def dashboard_logout(response: Response):
    response.delete_cookie("agentnotary_report_session", path="/")
    return {"signed_in": False}


@router.get("/data", include_in_schema=False)
def dashboard_data(agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_session(agentnotary_report_session)
    return collect_dashboard()
