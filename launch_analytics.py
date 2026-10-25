"""Product analytics plus a restricted, time-limited security IP log.

The normal analytics tables never contain raw IP addresses.  A separate
security log may retain the source IP for the configured six-month window so
the owner can investigate abuse; it is not part of visitor counts.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from urllib.parse import quote
from urllib.request import Request as UrlRequest, urlopen
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field


router = APIRouter(prefix="/internal/analytics", tags=["Internal analytics"])
_ATTEMPTS: dict[str, list[float]] = {}
_GEO_CACHE: dict[str, tuple[float, str | None]] = {}
_LOCK = threading.RLock()


def analytics_enabled() -> bool:
    return os.getenv("ANALYTICS_ENABLED", "false").lower() == "true"


def _database_path() -> Path:
    return Path(os.getenv("ANALYTICS_DB_PATH", "/var/data/agentnotary/analytics.sqlite3"))


def _retention_days() -> int:
    try:
        value = int(os.getenv("ANALYTICS_RETENTION_DAYS", "760"))
    except ValueError:
        value = 760
    return min(1095, max(30, value))


def _security_ip_retention_days() -> int:
    """Raw-IP security-log retention; six months by default and at most six months."""
    try:
        value = int(os.getenv("ANALYTICS_IP_RETENTION_DAYS", "180"))
    except ValueError:
        value = 180
    return min(180, max(1, value))


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """CREATE TABLE IF NOT EXISTS analytics_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL, event TEXT NOT NULL, path TEXT NOT NULL,
        language TEXT NOT NULL, campaign TEXT NOT NULL, country TEXT,
        duration_seconds INTEGER NOT NULL, recorded_at INTEGER NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS analytics_security_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_ip TEXT NOT NULL,
        event TEXT NOT NULL, path TEXT NOT NULL,
        country TEXT, recorded_at INTEGER NOT NULL
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_analytics_time ON analytics_events(recorded_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_analytics_session ON analytics_events(session_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_security_time ON analytics_security_events(recorded_at)")
    return db


class LaunchEvent(BaseModel):
    event: Literal[
        "landing_view", "page_view", "page_exit", "heartbeat",
        "buyer_click", "seller_click", "demo_click",
        "founding_click", "language_click", "guide_click",
    ]
    path: str = Field(default="/", max_length=160, pattern=r"^/[A-Za-z0-9/_.-]*$")
    language: str = Field(default="en", max_length=12, pattern=r"^[A-Za-z-]+$")
    campaign: str = Field(default="", max_length=80, pattern=r"^[A-Za-z0-9._-]*$")
    session_id: str = Field(default="anonymous", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    duration_seconds: int = Field(default=0, ge=0, le=86_400)


def _country(request: Request) -> str | None:
    header = os.getenv("ANALYTICS_COUNTRY_HEADER", "").strip().lower()
    if header not in {"cf-ipcountry", "x-vercel-ip-country", "x-country-code"}:
        return None
    value = request.headers.get(header, "").upper()
    if re.fullmatch(r"[A-Z]{2}", value) and value not in {"XX", "T1"}:
        return value
    return None


def _geoip_country(source_ip: str) -> str | None:
    """Resolve a country code via an explicitly configured GeoIP endpoint."""
    templates = [item.strip() for item in (
        os.getenv("ANALYTICS_GEOIP_URL", ""),
        os.getenv("ANALYTICS_GEOIP_FALLBACK_URL", ""),
    ) if item.strip()]
    if not templates or source_ip in {"", "unknown"}:
        return None
    now = time.time()
    cached = _GEO_CACHE.get(source_ip)
    if cached and now - cached[0] < 86_400:
        return cached[1]
    country = None
    for template in templates:
        try:
            url = template.format(ip=quote(source_ip, safe=""))
            request = UrlRequest(url, headers={"Accept": "application/json,text/plain", "User-Agent": "AgentSolis-Analytics/1.0"})
            with urlopen(request, timeout=1.5) as response:
                body = response.read(4096).decode("utf-8", "replace").strip()
            if body.startswith("{"):
                import json
                payload = json.loads(body)
                body = payload.get("country_code") or payload.get("countryCode") or payload.get("country") or ""
            candidate = str(body).strip().upper()
            if re.fullmatch(r"[A-Z]{2}", candidate) and candidate not in {"XX", "T1"}:
                country = candidate
                break
        except Exception:
            continue
    if country:
        _GEO_CACHE[source_ip] = (now, country)
    return country


def _source_ip(request: Request) -> str:
    """Return the source address without trusting spoofable proxy headers by default."""
    if os.getenv("ANALYTICS_TRUST_PROXY_HEADERS", "false").lower() == "true":
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded[:128]
    return (request.client.host if request.client else "unknown")[:128]


@router.post("/event", include_in_schema=False, status_code=204)
def record_launch_event(item: LaunchEvent, request: Request) -> Response:
    if not analytics_enabled():
        return Response(status_code=204)
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [stamp for stamp in _ATTEMPTS.get(key, []) if now - stamp < 60]
    if len(recent) >= 120:
        raise HTTPException(status_code=429, detail="Too many analytics events")
    recent.append(now)
    _ATTEMPTS[key] = recent
    source_ip = _source_ip(request)
    data = {
        "session_id": item.session_id, "event": item.event, "path": item.path,
        "language": item.language, "campaign": item.campaign,
        "country": _country(request) or _geoip_country(source_ip),
        "duration_seconds": item.duration_seconds,
        "recorded_at": int(time.time()),
    }
    with _LOCK:
        db = _connect()
        try:
            db.execute(
                """INSERT INTO analytics_events
                (session_id,event,path,language,campaign,country,duration_seconds,recorded_at)
                VALUES (:session_id,:event,:path,:language,:campaign,:country,:duration_seconds,:recorded_at)""",
                data,
            )
            db.execute(
                """INSERT INTO analytics_security_events
                (source_ip,event,path,country,recorded_at)
                VALUES (?,?,?,?,?)""",
                (source_ip, item.event, item.path, data["country"], data["recorded_at"]),
            )
            cutoff = data["recorded_at"] - _retention_days() * 86_400
            db.execute("DELETE FROM analytics_events WHERE recorded_at < ?", (cutoff,))
            ip_cutoff = data["recorded_at"] - _security_ip_retention_days() * 86_400
            db.execute("DELETE FROM analytics_security_events WHERE recorded_at < ?", (ip_cutoff,))
            db.commit()
        finally:
            db.close()
    return Response(status_code=204)


def analytics_summary(now: datetime | None = None) -> dict:
    if not analytics_enabled() or not _database_path().exists():
        return {"available": False, "message": "Ziyaretçi analitiği etkin değil veya henüz veri oluşmadı."}
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    day = current.replace(hour=0, minute=0, second=0, microsecond=0)
    starts = {
        "today": day, "last_7_days": current - timedelta(days=7),
        "last_21_days": current - timedelta(days=21),
        "month": datetime(current.year, current.month, 1, tzinfo=timezone.utc),
        "year": datetime(current.year, 1, 1, tzinfo=timezone.utc), "all": None,
    }

    def metrics(db: sqlite3.Connection, start: datetime | None) -> dict:
        where = "WHERE recorded_at >= ?" if start else ""
        args = (int(start.timestamp()),) if start else ()
        row = db.execute(
            f"""SELECT COUNT(DISTINCT session_id),
            SUM(CASE WHEN event IN ('landing_view','page_view') THEN 1 ELSE 0 END), COUNT(*)
            FROM analytics_events {where}""", args,
        ).fetchone()
        dwell = db.execute(
            f"""SELECT AVG(max_duration) FROM (SELECT session_id, path,
            MAX(duration_seconds) AS max_duration FROM analytics_events {where}
            GROUP BY session_id, path)""", args,
        ).fetchone()[0]
        return {"visitors": int(row[0] or 0), "page_views": int(row[1] or 0),
                "events": int(row[2] or 0), "average_session_seconds": round(float(dwell or 0), 1)}

    with _LOCK:
        db = _connect()
        try:
            periods = {name: metrics(db, start) for name, start in starts.items()}
            top_pages = [{"path": row[0], "views": int(row[1]), "visitors": int(row[2])} for row in db.execute(
                """SELECT path, COUNT(*), COUNT(DISTINCT session_id) FROM analytics_events
                WHERE event IN ('landing_view','page_view') GROUP BY path ORDER BY COUNT(*) DESC LIMIT 20""").fetchall()]
            countries = [{"country": row[0], "visitors": int(row[1])} for row in db.execute(
                """SELECT COALESCE(country,'Unknown'), COUNT(DISTINCT session_id) FROM analytics_events
                GROUP BY COALESCE(country,'Unknown') ORDER BY COUNT(DISTINCT session_id) DESC LIMIT 30""").fetchall()]
            actions = [{"event": row[0], "count": int(row[1])} for row in db.execute(
                """SELECT event, COUNT(*) FROM analytics_events
                WHERE event NOT IN ('landing_view','page_view','heartbeat','page_exit')
                GROUP BY event ORDER BY COUNT(*) DESC""").fetchall()]
        finally:
            db.close()
    return {"available": True, "message": "Yaklaşık ürün analitiğidir; bot ve test trafiği içerebilir. Ziyaretçi sayısı tarayıcı sekmesi oturumudur. Ülke yalnız güvenilir ağ başlığı yapılandırılmışsa gösterilir. IP adresi, cüzdan, e-posta ve cihaz parmak izi saklanmaz.",
            "periods": periods, "top_pages": top_pages, "countries": countries, "actions": actions}


def _parse_filter_date(value: str | None, end: bool = False) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(422, "Tarih ISO-8601 biçiminde olmalı.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp())


def analytics_events(
    start: str | None = None,
    end: str | None = None,
    country: str | None = None,
    path: str | None = None,
    event: str | None = None,
    limit: int = 500,
) -> dict:
    """Return filterable, privacy-light event detail for the private founder panel."""
    if not analytics_enabled() or not _database_path().exists():
        return {"available": False, "message": "Ziyaretçi analitiği etkin değil veya henüz veri oluşmadı.", "events": []}
    start_ts = _parse_filter_date(start)
    end_ts = _parse_filter_date(end, end=True)
    if end_ts is not None:
        end_ts = end_ts + 86399 if len(end or "") <= 10 else end_ts
    clauses, args = [], []
    if start_ts is not None:
        clauses.append("recorded_at >= ?"); args.append(start_ts)
    if end_ts is not None:
        clauses.append("recorded_at <= ?"); args.append(end_ts)
    if country:
        clauses.append("COALESCE(country,'Unknown') = ?"); args.append(country.upper())
    if path:
        clauses.append("path = ?"); args.append(path)
    if event:
        clauses.append("event = ?"); args.append(event)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    safe_limit = min(2000, max(1, int(limit)))
    with _LOCK:
        db = _connect()
        try:
            rows = db.execute(
                f"""SELECT recorded_at, session_id, event, path, language, campaign,
                           COALESCE(country,'Unknown') AS country, duration_seconds
                    FROM analytics_events {where}
                    ORDER BY recorded_at DESC LIMIT ?""",
                (*args, safe_limit),
            ).fetchall()
        finally:
            db.close()
    return {
        "available": True,
        "message": "IP, cüzdan, e-posta ve cihaz parmak izi saklanmaz; yalnız toplulaştırılmış ülke ve olay kaydı gösterilir.",
        "filters": {"start": start, "end": end, "country": country, "path": path, "event": event},
        "events": [
            {"recorded_at": int(row[0]), "session_id": row[1], "event": row[2], "path": row[3],
             "language": row[4], "campaign": row[5], "country": row[6], "duration_seconds": int(row[7] or 0)}
            for row in rows
        ],
    }


def analytics_security_events(
    start: str | None = None,
    end: str | None = None,
    country: str | None = None,
    path: str | None = None,
    limit: int = 500,
) -> dict:
    """Return restricted raw-IP security records; never used for visitor totals."""
    if not analytics_enabled() or not _database_path().exists():
        return {"available": False, "message": "Güvenlik IP arşivi etkin değil veya henüz veri oluşmadı.", "events": []}
    start_ts = _parse_filter_date(start)
    end_ts = _parse_filter_date(end, end=True)
    if end_ts is not None:
        end_ts = end_ts + 86399 if len(end or "") <= 10 else end_ts
    clauses, args = [], []
    if start_ts is not None:
        clauses.append("recorded_at >= ?"); args.append(start_ts)
    if end_ts is not None:
        clauses.append("recorded_at <= ?"); args.append(end_ts)
    if country:
        clauses.append("COALESCE(country,'Unknown') = ?"); args.append(country.upper())
    if path:
        clauses.append("path = ?"); args.append(path)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    safe_limit = min(2000, max(1, int(limit)))
    with _LOCK:
        db = _connect()
        try:
            rows = db.execute(
                f"""SELECT recorded_at, source_ip, event, path,
                           COALESCE(country,'Unknown') AS country
                    FROM analytics_security_events {where}
                    ORDER BY recorded_at DESC LIMIT ?""",
                (*args, safe_limit),
            ).fetchall()
        finally:
            db.close()
    return {
        "available": True,
        "message": "Kısıtlı güvenlik kaydıdır; yalnız güvenlik/abuse incelemesi için gösterilir ve 180 gün sonra silinir.",
        "retention_days": _security_ip_retention_days(),
        "events": [
            {"recorded_at": int(row[0]), "ip": row[1], "event": row[2], "path": row[3], "country": row[4]}
            for row in rows
        ],
    }
