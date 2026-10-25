"""Private outreach CRM for the founder dashboard.

The CRM records public business contact details and explicit outreach events.  It
does not send mail, load tracking pixels, infer personal data, or treat a draft
as a sent message.
"""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Cookie, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from web3 import Web3

from reporting import _authorize_session


router = APIRouter(prefix="/internal/reporting/outreach", tags=["Internal outreach CRM"])

STATUSES = (
    "draft", "sent", "bounced", "opt_out", "replied", "positive", "demo",
    "founding50", "escrow", "won", "lost",
)
EVENT_KINDS = STATUSES + ("follow_up", "note")
TERMINAL_STATUSES = {"bounced", "opt_out", "won", "lost"}


def _database_path() -> Path:
    configured = os.getenv("OUTREACH_CRM_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "data" / "outreach-crm.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    _migrate(db)
    return db


@contextmanager
def _database():
    db = _connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _migrate(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS outreach_leads (
            id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            contact_name TEXT,
            website TEXT,
            country TEXT,
            country_verified INTEGER NOT NULL DEFAULT 0 CHECK(country_verified IN (0,1)),
            channel_type TEXT NOT NULL,
            channel_value TEXT NOT NULL,
            source_url TEXT NOT NULL,
            segment TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            first_contact_at INTEGER,
            last_contact_at INTEGER,
            subject TEXT,
            reply_summary TEXT,
            next_follow_up_at INTEGER,
            follow_up_count INTEGER NOT NULL DEFAULT 0,
            wallet TEXT,
            deal_id TEXT,
            relationship_verified INTEGER NOT NULL DEFAULT 0 CHECK(relationship_verified IN (0,1)),
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outreach_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id TEXT NOT NULL REFERENCES outreach_leads(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            occurred_at INTEGER NOT NULL,
            subject TEXT,
            message_summary TEXT,
            reply_summary TEXT,
            source_url TEXT,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outreach_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            mailbox TEXT NOT NULL,
            imap_uid TEXT,
            direction TEXT NOT NULL,
            sender TEXT,
            recipients TEXT,
            cc TEXT,
            subject TEXT,
            occurred_at INTEGER NOT NULL,
            status TEXT NOT NULL,
            body_summary TEXT,
            lead_id TEXT REFERENCES outreach_leads(id) ON DELETE SET NULL,
            synced_at INTEGER NOT NULL,
            UNIQUE(message_id, mailbox)
        );
        CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_leads(status);
        CREATE INDEX IF NOT EXISTS idx_outreach_follow_up ON outreach_leads(next_follow_up_at);
        CREATE INDEX IF NOT EXISTS idx_outreach_owner ON outreach_leads(owner);
        CREATE INDEX IF NOT EXISTS idx_outreach_event_lead ON outreach_events(lead_id, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_outreach_messages_time ON outreach_messages(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_outreach_messages_lead ON outreach_messages(lead_id, occurred_at DESC);
        """
    )
    db.execute("PRAGMA user_version=1")
    db.commit()
    if os.getenv("OUTREACH_CRM_SEED_EVIDENCE", "false").lower() == "true":
        _seed_evidence(db)


def _epoch(value: str | None) -> int:
    if not value:
        return int(time.time())
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return int(time.time())


def _seed_evidence(db: sqlite3.Connection) -> None:
    """Import founder-verified CSV evidence once into the private CRM."""
    if db.execute("SELECT 1 FROM outreach_events LIMIT 1").fetchone():
        return
    root = Path(__file__).resolve().parent / "outreach"
    leads_path = root / "crm-leads.csv"
    events_path = Path(os.getenv("OUTREACH_CRM_EVIDENCE_PATH", str(root / "crm-interactions.csv")))
    if not events_path.exists():
        return
    lead_ids: dict[str, str] = {}
    if leads_path.exists():
        with leads_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                lead_id = row.get("lead_id") or str(uuid.uuid4())
                created = _epoch(row.get("created_at"))
                country = (row.get("country") or "").strip()
                country_value = None if country.lower() in {"", "unknown", "bilinmiyor"} else country
                source = row.get("website_or_profile_url") or "https://agentsolis.solists.com.tr/"
                db.execute(
                    """INSERT OR IGNORE INTO outreach_leads
                    (id,company_name,contact_name,website,country,country_verified,channel_type,
                     channel_value,source_url,segment,owner,status,subject,next_follow_up_at,
                     wallet,deal_id,relationship_verified,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (lead_id, row.get("company_or_person") or "Bilinmeyen aday", None,
                     row.get("website_or_profile_url") or None, country_value,
                     int(bool(country_value and row.get("country_source_url"))),
                     row.get("contact_channel") or "other", row.get("contact_address_or_url") or "—",
                     source, row.get("segment") or "unknown", row.get("owner_agent") or "codex",
                     row.get("status") if row.get("status") in STATUSES else "draft", None, None,
                     None, None, 0, created, _epoch(row.get("updated_at")) or created),
                )
                lead_ids[row["lead_id"]] = lead_id
    with events_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            interaction_id = row.get("interaction_id") or str(uuid.uuid4())
            existing = db.execute("SELECT 1 FROM outreach_events WHERE source_url LIKE ?", (f"%{interaction_id}%",)).fetchone()
            if existing:
                continue
            lead_id = lead_ids.get(row.get("lead_id") or "")
            recipient = (row.get("to_address_or_url") or "").strip()
            if not lead_id:
                lead_id = f"evidence-{interaction_id[:48]}"
                domain = recipient.split("@", 1)[-1] if "@" in recipient else "unknown"
                db.execute(
                    """INSERT OR IGNORE INTO outreach_leads
                    (id,company_name,website,country_verified,channel_type,channel_value,
                     source_url,segment,owner,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (lead_id, domain, f"https://{domain}" if domain != "unknown" else None, 0,
                     "email", recipient or "—", "https://agentsolis.solists.com.tr/",
                     "verified_outreach", "codex", "draft", _epoch(row.get("occurred_at")), _epoch(row.get("occurred_at"))),
                )
            event_type = row.get("event_type") or "note"
            kind = "sent" if event_type == "sent_evidence" else "bounced" if event_type == "bounce" else "replied" if event_type == "auto_reply" else "note"
            occurred = _epoch(row.get("occurred_at"))
            subject = row.get("subject_or_context") or None
            summary = row.get("reply_summary") or None
            evidence = f"evidence:{interaction_id}; {row.get('evidence_url_or_ref') or ''}".strip()
            db.execute(
                """INSERT INTO outreach_events
                (lead_id,kind,occurred_at,subject,message_summary,reply_summary,source_url,created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (lead_id, kind, occurred, subject, summary, summary if kind in {"bounced", "replied"} else None, evidence, occurred),
            )
            db.execute(
                "UPDATE outreach_leads SET status=?,first_contact_at=COALESCE(first_contact_at,?),last_contact_at=?,subject=?,reply_summary=?,updated_at=? WHERE id=?",
                (kind, occurred, occurred, subject, summary if kind in {"bounced", "replied"} else None, occurred, lead_id),
            )
    db.commit()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _url(value: str | None) -> str | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Use a public http(s) URL.")
    return cleaned


class LeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=100)
    country_verified: bool = False
    channel_type: Literal["email", "contact_form", "platform", "social_business", "other"]
    channel_value: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=1000)
    segment: str = Field(min_length=1, max_length=120)
    owner: str = Field(min_length=1, max_length=120)
    subject: str | None = Field(default=None, max_length=300)
    next_follow_up_at: int | None = None
    wallet: str | None = Field(default=None, max_length=42)
    deal_id: str | None = Field(default=None, max_length=66)
    relationship_verified: bool = False

    @field_validator("website", "source_url")
    @classmethod
    def validate_urls(cls, value):
        return _url(value)

    @model_validator(mode="after")
    def verify_sensitive_links(self):
        self.contact_name = _clean(self.contact_name)
        self.country = _clean(self.country)
        self.subject = _clean(self.subject)
        self.wallet = _clean(self.wallet)
        self.deal_id = _clean(self.deal_id)
        if self.country and not self.country_verified:
            raise ValueError("Country may be stored only when it is verified by a source.")
        if (self.wallet or self.deal_id) and not self.relationship_verified:
            raise ValueError("Wallet/deal links require an explicit verified relationship.")
        if self.wallet and not Web3.is_address(self.wallet):
            raise ValueError("wallet is not a valid address")
        if self.deal_id and (not self.deal_id.startswith("0x") or len(self.deal_id) != 66):
            raise ValueError("deal_id must be a 32-byte hex value")
        return self


class LeadUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=100)
    country_verified: bool | None = None
    channel_type: Literal["email", "contact_form", "platform", "social_business", "other"] | None = None
    channel_value: str | None = Field(default=None, min_length=1, max_length=500)
    source_url: str | None = Field(default=None, max_length=1000)
    segment: str | None = Field(default=None, min_length=1, max_length=120)
    owner: str | None = Field(default=None, min_length=1, max_length=120)
    subject: str | None = Field(default=None, max_length=300)
    reply_summary: str | None = Field(default=None, max_length=1000)
    next_follow_up_at: int | None = None
    wallet: str | None = Field(default=None, max_length=42)
    deal_id: str | None = Field(default=None, max_length=66)
    relationship_verified: bool | None = None

    @field_validator("website", "source_url")
    @classmethod
    def validate_urls(cls, value):
        return _url(value)


class EventCreate(BaseModel):
    kind: Literal[
        "draft", "sent", "bounced", "opt_out", "replied", "positive",
        "demo", "founding50", "escrow", "won", "lost", "follow_up", "note"
    ]
    occurred_at: int | None = None
    subject: str | None = Field(default=None, max_length=300)
    message_summary: str | None = Field(default=None, max_length=1000)
    reply_summary: str | None = Field(default=None, max_length=1000)
    source_url: str | None = Field(default=None, max_length=1000)
    next_follow_up_at: int | None = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value):
        return _url(value)


def _lead(db: sqlite3.Connection, lead_id: str) -> sqlite3.Row:
    row = db.execute("SELECT * FROM outreach_leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    return row


def create_lead(payload: LeadCreate, now: int | None = None) -> dict:
    current = int(now or time.time())
    lead_id = str(uuid.uuid4())
    with _database() as db:
        db.execute(
            """INSERT INTO outreach_leads
            (id,company_name,contact_name,website,country,country_verified,channel_type,
             channel_value,source_url,segment,owner,status,subject,next_follow_up_at,
             wallet,deal_id,relationship_verified,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lead_id, payload.company_name, payload.contact_name, payload.website,
             payload.country, int(payload.country_verified), payload.channel_type,
             payload.channel_value, payload.source_url, payload.segment, payload.owner,
             "draft", payload.subject, payload.next_follow_up_at, payload.wallet,
             payload.deal_id, int(payload.relationship_verified), current, current),
        )
        db.execute(
            "INSERT INTO outreach_events (lead_id,kind,occurred_at,subject,created_at) VALUES (?,?,?,?,?)",
            (lead_id, "draft", current, payload.subject, current),
        )
        return _serialize_lead(_lead(db, lead_id))


def update_lead(lead_id: str, payload: LeadUpdate, now: int | None = None) -> dict:
    current = int(now or time.time())
    values = payload.model_dump(exclude_unset=True)
    with _database() as db:
        existing = dict(_lead(db, lead_id))
        merged = {**existing, **values}
        country = _clean(merged.get("country"))
        country_verified = bool(merged.get("country_verified"))
        wallet, deal_id = _clean(merged.get("wallet")), _clean(merged.get("deal_id"))
        relationship_verified = bool(merged.get("relationship_verified"))
        if country and not country_verified:
            raise HTTPException(422, "Country may be stored only when verified.")
        if (wallet or deal_id) and not relationship_verified:
            raise HTTPException(422, "Wallet/deal links require an explicit verified relationship.")
        if wallet and not Web3.is_address(wallet):
            raise HTTPException(422, "wallet is not a valid address")
        if deal_id and (not deal_id.startswith("0x") or len(deal_id) != 66):
            raise HTTPException(422, "deal_id must be a 32-byte hex value")
        allowed = {
            "company_name", "contact_name", "website", "country", "country_verified",
            "channel_type", "channel_value", "source_url", "segment", "owner", "subject",
            "reply_summary", "next_follow_up_at", "wallet", "deal_id", "relationship_verified",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        for key in ("contact_name", "country", "subject", "reply_summary", "wallet", "deal_id"):
            if key in updates:
                updates[key] = _clean(updates[key])
        for key in ("country_verified", "relationship_verified"):
            if key in updates:
                updates[key] = int(bool(updates[key]))
        if updates:
            assignments = ",".join(f"{key}=?" for key in updates)
            db.execute(
                f"UPDATE outreach_leads SET {assignments},updated_at=? WHERE id=?",
                (*updates.values(), current, lead_id),
            )
        return _serialize_lead(_lead(db, lead_id))


def add_event(lead_id: str, payload: EventCreate, now: int | None = None) -> dict:
    occurred = int(payload.occurred_at or now or time.time())
    created = int(now or time.time())
    with _database() as db:
        row = _lead(db, lead_id)
        status = row["status"]
        first_contact = row["first_contact_at"]
        last_contact = row["last_contact_at"]
        follow_up_count = int(row["follow_up_count"])
        next_follow_up = payload.next_follow_up_at
        reply_summary = row["reply_summary"]
        if payload.kind == "sent":
            status = "sent"
            first_contact = first_contact or occurred
            last_contact = occurred
        elif payload.kind == "follow_up":
            follow_up_count += 1
            first_contact = first_contact or occurred
            last_contact = occurred
            if status == "draft":
                status = "sent"
        elif payload.kind not in {"draft", "note"}:
            status = payload.kind
            if payload.kind in {"replied", "positive", "demo", "founding50", "escrow", "won", "lost", "bounced", "opt_out"}:
                last_contact = occurred
        if payload.reply_summary is not None:
            reply_summary = _clean(payload.reply_summary)
        if payload.kind in TERMINAL_STATUSES:
            next_follow_up = None
        elif payload.next_follow_up_at is None:
            next_follow_up = row["next_follow_up_at"]
        subject = _clean(payload.subject) or row["subject"]
        db.execute(
            """INSERT INTO outreach_events
            (lead_id,kind,occurred_at,subject,message_summary,reply_summary,source_url,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (lead_id, payload.kind, occurred, _clean(payload.subject),
             _clean(payload.message_summary), _clean(payload.reply_summary), payload.source_url, created),
        )
        db.execute(
            """UPDATE outreach_leads SET status=?,first_contact_at=?,last_contact_at=?,
            subject=?,reply_summary=?,next_follow_up_at=?,follow_up_count=?,updated_at=? WHERE id=?""",
            (status, first_contact, last_contact, subject, reply_summary, next_follow_up,
             follow_up_count, created, lead_id),
        )
        return _serialize_lead(_lead(db, lead_id))


def _serialize_lead(row: sqlite3.Row | dict) -> dict:
    item = dict(row)
    item["country_verified"] = bool(item["country_verified"])
    item["relationship_verified"] = bool(item["relationship_verified"])
    return item


def crm_summary(now: int | None = None) -> dict:
    current = int(now or time.time())
    with _database() as db:
        rows = db.execute("SELECT * FROM outreach_leads ORDER BY updated_at DESC").fetchall()
        counts = {status: 0 for status in STATUSES}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        sent_ever = int(db.execute(
            "SELECT COUNT(DISTINCT lead_id) FROM outreach_events WHERE kind IN ('sent','follow_up')"
        ).fetchone()[0])
        replied_ever = int(db.execute(
            "SELECT COUNT(DISTINCT lead_id) FROM outreach_events WHERE kind IN ('replied','positive','demo','founding50','escrow','won')"
        ).fetchone()[0])
        positive_ever = int(db.execute(
            "SELECT COUNT(DISTINCT lead_id) FROM outreach_events WHERE kind IN ('positive','demo','founding50','escrow','won')"
        ).fetchone()[0])
        due = db.execute(
            """SELECT * FROM outreach_leads
            WHERE next_follow_up_at IS NOT NULL AND next_follow_up_at<=?
              AND status NOT IN ('bounced','opt_out','won','lost')
            ORDER BY next_follow_up_at""",
            (current,),
        ).fetchall()
        segments = [dict(row) for row in db.execute(
            "SELECT segment,COUNT(*) AS leads,SUM(CASE WHEN status IN ('replied','positive','demo','founding50','escrow','won') THEN 1 ELSE 0 END) AS replies FROM outreach_leads GROUP BY segment ORDER BY leads DESC"
        )]
        channels = [dict(row) for row in db.execute(
            "SELECT channel_type,COUNT(*) AS leads,SUM(CASE WHEN status IN ('replied','positive','demo','founding50','escrow','won') THEN 1 ELSE 0 END) AS replies FROM outreach_leads GROUP BY channel_type ORDER BY leads DESC"
        )]
        recent_events = [dict(row) for row in db.execute(
            """SELECT e.id,e.lead_id,l.company_name,l.contact_name,e.kind,e.occurred_at,
                      e.subject,e.message_summary,e.reply_summary,e.source_url
               FROM outreach_events e JOIN outreach_leads l ON l.id=e.lead_id
               ORDER BY e.occurred_at DESC,e.id DESC LIMIT 250"""
        )]
        return {
            "generated_at": datetime.fromtimestamp(current, timezone.utc).isoformat(),
            "total_leads": len(rows),
            "status_counts": counts,
            "sent_ever": sent_ever,
            "replied_ever": replied_ever,
            "positive_ever": positive_ever,
            "reply_rate": round((replied_ever / sent_ever * 100), 1) if sent_ever else 0.0,
            "positive_rate": round((positive_ever / sent_ever * 100), 1) if sent_ever else 0.0,
            "follow_ups_due": [_serialize_lead(row) for row in due],
            "segments": segments,
            "channels": channels,
            "recent_events": recent_events,
            "leads": [_serialize_lead(row) for row in rows],
        }


def _authorize_request(request: Request, session: str | None) -> None:
    _authorize_session(session)
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.netloc != request.headers.get("host") or parsed.scheme not in {"http", "https"}:
                raise HTTPException(403, "Cross-origin update rejected")


@router.get("", include_in_schema=False)
def outreach_data(request: Request, agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_request(request, agentnotary_report_session)
    return JSONResponse(crm_summary(), headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.post("/leads", include_in_schema=False)
def outreach_create(request: Request, payload: LeadCreate = Body(...), agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_request(request, agentnotary_report_session)
    return create_lead(payload)


@router.patch("/leads/{lead_id}", include_in_schema=False)
def outreach_update(lead_id: str, request: Request, payload: LeadUpdate = Body(...), agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_request(request, agentnotary_report_session)
    return update_lead(lead_id, payload)


@router.post("/leads/{lead_id}/events", include_in_schema=False)
def outreach_event(lead_id: str, request: Request, payload: EventCreate = Body(...), agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_request(request, agentnotary_report_session)
    return add_event(lead_id, payload)
