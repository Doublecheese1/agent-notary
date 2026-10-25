"""Read-only IMAP archive for the private outreach CRM.

This module never sends, deletes, or modifies mail. It stores headers and a
short plain-text summary only; credentials belong in Render secrets.
"""
from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import os
import re
import time
from email import policy
from email.message import Message
from typing import Iterable

from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import JSONResponse

from outreach_crm import _database, _authorize_request

router = APIRouter(prefix="/internal/reporting/outreach/email-archive", tags=["Internal email archive"])


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for chunk, charset in email.header.decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return " ".join(" ".join(parts).split())


def _addresses(value: str | None) -> str:
    return ", ".join(email.utils.formataddr(pair) for pair in email.utils.getaddresses([value or ""]))


def _plain_text(message: Message) -> str:
    if message.is_multipart():
        parts = message.walk()
        for part in parts:
            if part.get_content_type() == "text/plain" and "attachment" not in (part.get("Content-Disposition") or "").lower():
                try:
                    return part.get_content()
                except Exception:
                    continue
        return ""
    if message.get_content_type() == "text/plain":
        try:
            return message.get_content()
        except Exception:
            return ""
    return ""


def _summary(message: Message, limit: int = 600) -> str:
    text = re.sub(r"\s+", " ", _plain_text(message)).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _epoch_date(value: str | None) -> int:
    try:
        return int(email.utils.parsedate_to_datetime(value or "").timestamp())
    except (TypeError, ValueError, OverflowError):
        return int(time.time())


def _folders() -> list[str]:
    return [item.strip() for item in os.getenv("OUTREACH_IMAP_FOLDERS", "INBOX,Sent").split(",") if item.strip()]


def sync_imap() -> dict:
    """Synchronize configured IMAP folders in read-only mode."""
    host = os.getenv("OUTREACH_IMAP_HOST", "mail.solists.com.tr").strip()
    port = int(os.getenv("OUTREACH_IMAP_PORT", "993"))
    user = os.getenv("OUTREACH_IMAP_USER", "").strip()
    password = os.getenv("OUTREACH_IMAP_PASSWORD", "")
    if not user or not password:
        return {"ok": False, "reason": "IMAP credentials are not configured", "imported": 0}
    imported = 0
    checked = 0
    now = int(time.time())
    client = imaplib.IMAP4_SSL(host, port)
    try:
        client.login(user, password)
        for mailbox in _folders():
            status, _ = client.select(mailbox, readonly=True)
            if status != "OK":
                continue
            status, data = client.uid("search", None, "ALL")
            if status != "OK":
                continue
            for uid in (data[0] or b"").split()[-2000:]:
                checked += 1
                status, fetched = client.uid("fetch", uid, "(BODY.PEEK[])")
                if status != "OK":
                    continue
                raw = next((item[1] for item in fetched if isinstance(item, tuple) and isinstance(item[1], bytes)), None)
                if not raw:
                    continue
                message = email.message_from_bytes(raw, policy=policy.default)
                message_id = (message.get("Message-ID") or "").strip()
                if not message_id:
                    message_id = f"imap:{mailbox}:{uid.decode(errors='replace')}"
                occurred = _epoch_date(message.get("Date"))
                sender = _addresses(message.get("From"))
                recipients = _addresses(message.get("To"))
                cc = _addresses(message.get("Cc"))
                direction = "outbound" if user.lower() in (sender or "").lower() else "inbound"
                status_value = "sent" if direction == "outbound" else "received"
                with _database() as db:
                    existing = db.execute("SELECT 1 FROM outreach_messages WHERE message_id=? AND mailbox=?", (message_id, mailbox)).fetchone()
                    if existing:
                        continue
                    lead = None
                    addresses = [value.strip().lower() for value in (recipients + "," + sender).split(",") if "@" in value]
                    for address in addresses:
                        lead = db.execute("SELECT id FROM outreach_leads WHERE lower(channel_value)=? LIMIT 1", (address,)).fetchone()
                        if lead:
                            break
                    lead_id = lead[0] if lead else None
                    db.execute(
                        """INSERT INTO outreach_messages
                        (message_id,mailbox,imap_uid,direction,sender,recipients,cc,subject,occurred_at,status,body_summary,lead_id,synced_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (message_id, mailbox, uid.decode(errors="replace"), direction, sender, recipients, cc,
                         _decode(message.get("Subject")), occurred, status_value, _summary(message), lead_id, now),
                    )
                    imported += 1
        return {"ok": True, "checked": checked, "imported": imported, "synced_at": now}
    finally:
        # IMAP.close() is only legal in SELECTED state.  After a mailbox
        # search loop the connection may be AUTHENTICATED, so always use the
        # session-level logout command and ignore a server-side close error.
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def archive_summary(limit: int = 500) -> dict:
    with _database() as db:
        rows = db.execute(
            """SELECT m.*, l.company_name, l.contact_name FROM outreach_messages m
               LEFT JOIN outreach_leads l ON l.id=m.lead_id
               ORDER BY m.occurred_at DESC, m.id DESC LIMIT ?""", (limit,)
        ).fetchall()
        return {"messages": [dict(row) for row in rows], "count": len(rows)}


@router.post("/sync", include_in_schema=False)
def email_archive_sync(request: Request, agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_request(request, agentnotary_report_session)
    try:
        return JSONResponse(sync_imap(), headers={"Cache-Control": "no-store"})
    except (imaplib.IMAP4.error, OSError, ValueError) as exc:
        return JSONResponse({"ok": False, "reason": str(exc), "imported": 0}, status_code=502)


@router.get("", include_in_schema=False)
def email_archive_data(request: Request, agentnotary_report_session: str | None = Cookie(default=None)):
    _authorize_request(request, agentnotary_report_session)
    return JSONResponse(archive_summary(), headers={"Cache-Control": "no-store"})
