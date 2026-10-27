"""Public Founding 50 applications with wallet ownership proof."""
from __future__ import annotations

import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from web3 import Web3

from mainnet import ROOT, connection

router = APIRouter(prefix="/mainnet/founding50", tags=["Founding 50"])
CHALLENGE_TTL = 10 * 60


def applications_open() -> bool:
    return os.getenv("FOUNDING50_APPLICATIONS_OPEN", "false").lower() == "true"


def _db_path() -> Path:
    explicit = os.getenv("FOUNDING50_DB_PATH", "").strip()
    if explicit:
        return Path(explicit)
    review_value = os.getenv("AI_REVIEW_DB_PATH", "").strip()
    review = Path(review_value) if review_value else ROOT / "data" / "ai_review.sqlite3"
    return review.with_name("founding50.sqlite3")


@contextmanager
def _db():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS founding_challenges (
            wallet TEXT PRIMARY KEY, nonce TEXT NOT NULL, expires_at INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer'
        );
        CREATE TABLE IF NOT EXISTS founding_applications (
            wallet TEXT PRIMARY KEY, use_case TEXT NOT NULL, created_at INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', role TEXT NOT NULL DEFAULT 'buyer'
        );
    """)
    for table, definition in (("founding_challenges", "role TEXT NOT NULL DEFAULT 'buyer'"), ("founding_applications", "role TEXT NOT NULL DEFAULT 'buyer'")):
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _wallet(raw: str) -> str:
    if not Web3.is_address(raw):
        raise HTTPException(422, "Enter a valid EVM wallet address.")
    return Web3.to_checksum_address(raw)


def _role(raw: str) -> str:
    value = (raw or "buyer").strip().lower()
    if value not in {"buyer", "seller", "both"}:
        raise HTTPException(422, "Choose buyer, seller or both.")
    return value


def _message(wallet: str, nonce: str, expires_at: int, role: str = "buyer") -> str:
    return (
        "AgentSolis Founding 50 application\n\n"
        f"Wallet: {wallet}\nRole: {role}\nNonce: {nonce}\nExpires: {expires_at}\n\n"
        "This signature proves wallet ownership. It does not move funds or approve token spending."
    )


class WalletRequest(BaseModel):
    wallet: str
    role: Literal["buyer", "seller", "both"] = "buyer"


class ApplicationRequest(BaseModel):
    wallet: str
    nonce: str = Field(min_length=32, max_length=128)
    signature: str = Field(min_length=100, max_length=1024)
    use_case: str = Field(min_length=10, max_length=500)
    role: Literal["buyer", "seller", "both"] = "buyer"
    accepted_terms: bool


@router.get("", include_in_schema=False)
def page():
    return FileResponse(ROOT / "static/founding50-mainnet.html", headers={"Cache-Control": "no-store"})


@router.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(ROOT / "static/founding50-mainnet.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@router.get("/status")
def status(wallet: str | None = None):
    _, contract = connection()
    count = int(contract.functions.foundingSeatCount().call())
    result = {"applications_open": applications_open(), "approved_places": count, "limit": 50}
    if wallet:
        who = _wallet(wallet)
        result["founding_state"] = int(contract.functions.foundingSeats(who).call())
        with _db() as db:
            row = db.execute("SELECT status, created_at FROM founding_applications WHERE wallet = ?", (who.lower(),)).fetchone()
        result["application"] = dict(row) if row else None
    return result


@router.post("/challenge")
def challenge(req: WalletRequest):
    if not applications_open():
        raise HTTPException(503, "Founding 50 applications are not open.")
    wallet = _wallet(req.wallet)
    role = _role(req.role)
    nonce, expires_at = secrets.token_hex(24), int(time.time()) + CHALLENGE_TTL
    with _db() as db:
        db.execute(
            "INSERT OR REPLACE INTO founding_challenges(wallet, nonce, expires_at, role) VALUES(?,?,?,?)",
            (wallet.lower(), nonce, expires_at, role),
        )
    return {"wallet": wallet, "role": role, "nonce": nonce, "expires_at": expires_at, "message": _message(wallet, nonce, expires_at, role)}


@router.post("/apply")
def apply(req: ApplicationRequest):
    if not applications_open():
        raise HTTPException(503, "Founding 50 applications are not open.")
    if not req.accepted_terms:
        raise HTTPException(422, "Accept the Founding 50 terms before applying.")
    wallet = _wallet(req.wallet)
    now = int(time.time())
    with _db() as db:
        row = db.execute(
            "SELECT nonce, expires_at, role FROM founding_challenges WHERE wallet = ?", (wallet.lower(),)
        ).fetchone()
        if not row or not secrets.compare_digest(row["nonce"], req.nonce) or int(row["expires_at"]) < now:
            raise HTTPException(409, "The signing request expired. Start the application again.")
        role = _role(req.role)
        if role != row["role"]:
            raise HTTPException(409, "The participant role changed. Start the application again.")
        message = _message(wallet, req.nonce, int(row["expires_at"]), role)
        try:
            recovered = Account.recover_message(encode_defunct(text=message), signature=req.signature)
        except Exception as exc:
            raise HTTPException(422, "The wallet signature could not be verified.") from exc
        if recovered.lower() != wallet.lower():
            raise HTTPException(403, "The signature does not belong to this wallet.")
        existing = db.execute("SELECT status FROM founding_applications WHERE wallet = ?", (wallet.lower(),)).fetchone()
        if existing:
            db.execute("DELETE FROM founding_challenges WHERE wallet = ?", (wallet.lower(),))
            return {"submitted": True, "status": existing["status"], "already_submitted": True}
        db.execute(
            "INSERT INTO founding_applications(wallet, use_case, created_at, status, role) VALUES(?,?,?,'pending',?)",
            (wallet.lower(), req.use_case.strip(), now, role),
        )
        db.execute("DELETE FROM founding_challenges WHERE wallet = ?", (wallet.lower(),))
    return {"submitted": True, "status": "pending", "already_submitted": False}


def application_list() -> list[dict]:
    """Used only from the password-protected founder report."""
    with _db() as db:
        rows = db.execute(
            "SELECT wallet, use_case, created_at, status, role FROM founding_applications ORDER BY created_at ASC"
        ).fetchall()
    return [dict(row) for row in rows]
