"""Pre-funding buyer/seller negotiation with immutable, wallet-signed final terms."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from web3 import Web3

from payments import ROOT, address

router = APIRouter(prefix="/mainnet/negotiations", tags=["Pre-funding negotiation"])
page_router = APIRouter(prefix="/mainnet/negotiate", tags=["Pre-funding negotiation"])
LOCK = threading.RLock()


def enabled() -> bool:
    return os.getenv("NEGOTIATION_ENABLED", "false").lower() == "true"


def require_enabled() -> None:
    if not enabled():
        raise HTTPException(503, "Negotiation is not open yet.")


def database_path() -> Path:
    path = Path(os.getenv("NEGOTIATION_DB_PATH", str(ROOT / "data" / "negotiations.db")))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def db():
    connection = sqlite3.connect(database_path(), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS negotiations (
            id TEXT PRIMARY KEY, buyer TEXT NOT NULL, seller TEXT NOT NULL,
            status TEXT NOT NULL, current_revision INTEGER NOT NULL,
            buyer_token_hash TEXT NOT NULL, seller_token_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, negotiation_id TEXT NOT NULL,
            role TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL,
            FOREIGN KEY(negotiation_id) REFERENCES negotiations(id)
        );
        CREATE TABLE IF NOT EXISTS revisions (
            negotiation_id TEXT NOT NULL, revision INTEGER NOT NULL,
            proposer TEXT NOT NULL, terms_text TEXT NOT NULL, terms_hash TEXT NOT NULL,
            buyer_signature TEXT, seller_signature TEXT, created_at INTEGER NOT NULL,
            PRIMARY KEY(negotiation_id, revision),
            FOREIGN KEY(negotiation_id) REFERENCES negotiations(id)
        );
    """)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def role_for(row: sqlite3.Row, token: str | None) -> str:
    supplied = token_hash(token or "")
    if secrets.compare_digest(supplied, row["buyer_token_hash"]):
        return "buyer"
    if secrets.compare_digest(supplied, row["seller_token_hash"]):
        return "seller"
    raise HTTPException(403, "This private negotiation link is not valid.")


def negotiation(connection: sqlite3.Connection, negotiation_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM negotiations WHERE id=?", (negotiation_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Negotiation not found.")
    return row


class Terms(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=8000)
    deliverables: str = Field(min_length=3, max_length=5000)
    limitations: str = Field(default="None stated", min_length=1, max_length=3000)
    evidence: str = Field(min_length=3, max_length=3000)
    amount_usdc: str = Field(pattern=r"^\d{1,4}(\.\d{1,6})?$")
    delivery_days: int = Field(ge=1, le=30)


class CreateNegotiation(BaseModel):
    buyer: str
    seller: str
    terms: Terms


class MessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class RevisionRequest(BaseModel):
    terms: Terms


class AcceptanceRequest(BaseModel):
    signature: str = Field(pattern=r"^(0x)?[0-9a-fA-F]{130}$")


def canonical_terms(value: Terms) -> str:
    amount = Decimal(value.amount_usdc)
    if amount < 100 or amount > 1000:
        raise HTTPException(422, "Buyer Review negotiations must be between 100 and 1,000 USDC.")
    payload = {"settlement_mode": "buyer_review", **value.model_dump()}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def acceptance_statement(row: sqlite3.Row, revision: sqlite3.Row) -> str:
    return (
        "AgentNotary Final Terms Acceptance\n"
        f"Negotiation: {row['id']}\n"
        f"Revision: {revision['revision']}\n"
        f"Terms hash: {revision['terms_hash']}\n"
        f"Buyer: {row['buyer']}\n"
        f"Seller: {row['seller']}\n"
        "Network: Arbitrum One (42161)\n"
        "I accept this exact revision as the terms that may be funded in escrow."
    )


def serialize(connection: sqlite3.Connection, row: sqlite3.Row, role: str) -> dict:
    revision = connection.execute(
        "SELECT * FROM revisions WHERE negotiation_id=? AND revision=?",
        (row["id"], row["current_revision"]),
    ).fetchone()
    messages = connection.execute(
        "SELECT id,role,body,created_at FROM messages WHERE negotiation_id=? ORDER BY id",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"], "role": role, "buyer": row["buyer"], "seller": row["seller"],
        "status": row["status"], "current_revision": row["current_revision"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "terms": json.loads(revision["terms_text"]), "terms_text": revision["terms_text"],
        "terms_hash": revision["terms_hash"],
        "buyer_accepted": bool(revision["buyer_signature"]),
        "seller_accepted": bool(revision["seller_signature"]),
        "acceptance_statement": acceptance_statement(row, revision),
        "messages": [dict(message) for message in messages],
    }


@page_router.get("", include_in_schema=False)
def negotiation_page():
    return FileResponse(ROOT / "static" / "negotiate.html", headers={"Cache-Control": "no-store"})


@page_router.get("/app.js", include_in_schema=False)
def negotiation_script():
    return FileResponse(ROOT / "static" / "negotiate.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@page_router.get("/{negotiation_id}", include_in_schema=False)
def negotiation_workspace(negotiation_id: str):
    uuid.UUID(negotiation_id)
    return FileResponse(ROOT / "static" / "negotiate.html", headers={"Cache-Control": "no-store"})


@router.post("")
def create_negotiation(request: CreateNegotiation):
    require_enabled()
    buyer, seller = address(request.buyer), address(request.seller)
    if buyer == seller:
        raise HTTPException(422, "Buyer and seller must use different wallets.")
    terms_text = canonical_terms(request.terms)
    terms_hash = Web3.to_hex(Web3.keccak(text=terms_text))
    negotiation_id = str(uuid.uuid4())
    buyer_token, seller_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = int(time.time())
    with LOCK, db() as connection:
        connection.execute(
            "INSERT INTO negotiations VALUES (?,?,?,?,?,?,?,?,?)",
            (negotiation_id, buyer, seller, "OPEN", 1, token_hash(buyer_token), token_hash(seller_token), now, now),
        )
        connection.execute(
            "INSERT INTO revisions VALUES (?,?,?,?,?,?,?,?)",
            (negotiation_id, 1, "buyer", terms_text, terms_hash, None, None, now),
        )
        connection.execute(
            "INSERT INTO messages(negotiation_id,role,body,created_at) VALUES (?,?,?,?)",
            (negotiation_id, "system", "Buyer opened the request. Discuss constraints before accepting final terms.", now),
        )
    return {
        "id": negotiation_id,
        "buyer_link": f"/mainnet/negotiate/{negotiation_id}#key={buyer_token}",
        "seller_link": f"/mainnet/negotiate/{negotiation_id}#key={seller_token}",
        "terms_hash": terms_hash,
    }


@router.get("/{negotiation_id}")
def read_negotiation(negotiation_id: str, x_negotiation_key: str | None = Header(default=None)):
    require_enabled()
    with LOCK, db() as connection:
        row = negotiation(connection, negotiation_id)
        return serialize(connection, row, role_for(row, x_negotiation_key))


@router.post("/{negotiation_id}/messages")
def post_message(negotiation_id: str, request: MessageRequest, x_negotiation_key: str | None = Header(default=None)):
    require_enabled()
    now = int(time.time())
    with LOCK, db() as connection:
        row = negotiation(connection, negotiation_id)
        role = role_for(row, x_negotiation_key)
        connection.execute(
            "INSERT INTO messages(negotiation_id,role,body,created_at) VALUES (?,?,?,?)",
            (negotiation_id, role, request.body.strip(), now),
        )
        connection.execute("UPDATE negotiations SET updated_at=? WHERE id=?", (now, negotiation_id))
        return serialize(connection, negotiation(connection, negotiation_id), role)


@router.post("/{negotiation_id}/revisions")
def propose_revision(negotiation_id: str, request: RevisionRequest, x_negotiation_key: str | None = Header(default=None)):
    require_enabled()
    terms_text = canonical_terms(request.terms)
    terms_hash = Web3.to_hex(Web3.keccak(text=terms_text))
    now = int(time.time())
    with LOCK, db() as connection:
        row = negotiation(connection, negotiation_id)
        role = role_for(row, x_negotiation_key)
        if row["status"] == "AGREED":
            raise HTTPException(409, "Signed final terms are frozen. Open a new negotiation to change them.")
        revision = int(row["current_revision"]) + 1
        connection.execute(
            "INSERT INTO revisions VALUES (?,?,?,?,?,?,?,?)",
            (negotiation_id, revision, role, terms_text, terms_hash, None, None, now),
        )
        connection.execute(
            "UPDATE negotiations SET status='OPEN',current_revision=?,updated_at=? WHERE id=?",
            (revision, now, negotiation_id),
        )
        connection.execute(
            "INSERT INTO messages(negotiation_id,role,body,created_at) VALUES (?,?,?,?)",
            (negotiation_id, "system", f"{role.title()} proposed final terms revision {revision}. Earlier acceptances were cleared.", now),
        )
        return serialize(connection, negotiation(connection, negotiation_id), role)


@router.post("/{negotiation_id}/accept")
def accept_revision(negotiation_id: str, request: AcceptanceRequest, x_negotiation_key: str | None = Header(default=None)):
    require_enabled()
    now = int(time.time())
    signature = request.signature if request.signature.startswith("0x") else "0x" + request.signature
    with LOCK, db() as connection:
        row = negotiation(connection, negotiation_id)
        role = role_for(row, x_negotiation_key)
        revision = connection.execute(
            "SELECT * FROM revisions WHERE negotiation_id=? AND revision=?",
            (negotiation_id, row["current_revision"]),
        ).fetchone()
        expected = row[role]
        try:
            recovered = Account.recover_message(
                encode_defunct(text=acceptance_statement(row, revision)), signature=signature
            )
        except Exception as exc:
            raise HTTPException(422, "The wallet signature is invalid.") from exc
        if recovered.lower() != expected.lower():
            raise HTTPException(403, f"Connect the designated {role} wallet.")
        column = "buyer_signature" if role == "buyer" else "seller_signature"
        connection.execute(
            f"UPDATE revisions SET {column}=? WHERE negotiation_id=? AND revision=?",
            (signature, negotiation_id, row["current_revision"]),
        )
        updated = connection.execute(
            "SELECT * FROM revisions WHERE negotiation_id=? AND revision=?",
            (negotiation_id, row["current_revision"]),
        ).fetchone()
        status = "AGREED" if updated["buyer_signature"] and updated["seller_signature"] else "AWAITING_SIGNATURE"
        connection.execute("UPDATE negotiations SET status=?,updated_at=? WHERE id=?", (status, now, negotiation_id))
        if status == "AGREED":
            connection.execute(
                "INSERT INTO messages(negotiation_id,role,body,created_at) VALUES (?,?,?,?)",
                (negotiation_id, "system", f"Both wallets accepted revision {row['current_revision']}. It is ready for escrow funding.", now),
            )
        return serialize(connection, negotiation(connection, negotiation_id), role)
