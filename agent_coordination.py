"""Private OpenAI/xAI coordination bridge for founder-directed work.

The bridge never exposes provider keys to the browser.  It gives both models the
same task, lets each review the other's proposal, and asks OpenAI for a concise
joint decision.  Results are stored locally so later runs can avoid repeating
work and can be audited from the private reporting area.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Cookie, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from reporting import _authorize_session


router = APIRouter(prefix="/internal/reporting/agents", tags=["Internal agent coordination"])


def _database_path() -> Path:
    configured = os.getenv("AGENT_COORDINATION_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path("/var/data/agentnotary/agent-coordination.sqlite3")


@contextmanager
def _database():
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS agent_rounds (
            id TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL,
            task TEXT NOT NULL,
            context TEXT,
            openai_first TEXT NOT NULL,
            xai_first TEXT NOT NULL,
            openai_review TEXT NOT NULL,
            xai_review TEXT NOT NULL,
            joint_decision TEXT NOT NULL,
            status TEXT NOT NULL
        )"""
    )
    try:
        yield db
        db.commit()
    finally:
        db.close()


class CoordinationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    task: str = Field(min_length=3, max_length=12_000)
    context: str | None = Field(default=None, max_length=20_000)


def _authorize(request: Request, session: str | None, authorization: str | None) -> None:
    token = os.getenv("REPORT_TRIGGER_TOKEN", "").strip()
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if token and supplied and hmac.compare_digest(token, supplied):
        return
    _authorize_session(session)
    origin = request.headers.get("origin")
    if origin and request.headers.get("host") not in origin:
        raise HTTPException(403, "Cross-origin request rejected")


def _provider_settings(provider: str) -> tuple[str, str, str]:
    if provider == "openai":
        return (
            "https://api.openai.com/v1/responses",
            os.getenv("OPENAI_API_KEY", "").strip(),
            os.getenv("OPENAI_COORDINATION_MODEL", "gpt-5-mini").strip(),
        )
    return (
        "https://api.x.ai/v1/responses",
        os.getenv("XAI_API_KEY", "").strip(),
        os.getenv("XAI_COORDINATION_MODEL", "grok-4.7").strip(),
    )


def _extract_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()
    parts: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            value = content.get("text")
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    if not parts:
        raise RuntimeError("Provider returned no text output")
    return "\n".join(parts)


async def _ask(provider: str, instructions: str, prompt: str) -> str:
    url, key, model = _provider_settings(provider)
    if not key:
        raise RuntimeError(f"{provider.upper()} API key is not configured")
    payload = {
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": 1200,
    }
    timeout = httpx.Timeout(120.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"{provider} request failed ({response.status_code}): {detail}")
    return _extract_text(response.json())


def _base_instructions(name: str) -> str:
    return (
        f"You are the {name} coordinator for AgentSolis. Be factual, concise and operational. "
        "Never claim an email was sent, a lead was contacted, or a transaction occurred without evidence. "
        "Treat the shared outreach CRM as the source of truth and flag duplicate ownership before outreach. "
        "Do not reveal secrets or API keys. Return concrete next actions and unresolved risks."
    )


async def coordinate(payload: CoordinationRequest) -> dict:
    context = payload.context or "No additional context supplied."
    first_prompt = f"TASK:\n{payload.task}\n\nSHARED CONTEXT:\n{context}\n\nPropose the best plan."
    openai_first, xai_first = await asyncio.gather(
        _ask("openai", _base_instructions("OpenAI"), first_prompt),
        _ask("xai", _base_instructions("Grok"), first_prompt),
    )
    openai_review_prompt = (
        f"TASK:\n{payload.task}\n\nYOUR FIRST PROPOSAL:\n{openai_first}\n\n"
        f"GROK'S PROPOSAL:\n{xai_first}\n\nReview Grok's proposal, correct it where needed, "
        "keep its useful points, and produce your revised recommendation."
    )
    xai_review_prompt = (
        f"TASK:\n{payload.task}\n\nYOUR FIRST PROPOSAL:\n{xai_first}\n\n"
        f"OPENAI'S PROPOSAL:\n{openai_first}\n\nReview OpenAI's proposal, correct it where needed, "
        "keep its useful points, and produce your revised recommendation."
    )
    openai_review, xai_review = await asyncio.gather(
        _ask("openai", _base_instructions("OpenAI"), openai_review_prompt),
        _ask("xai", _base_instructions("Grok"), xai_review_prompt),
    )
    synthesis_prompt = (
        f"TASK:\n{payload.task}\n\nOPENAI REVISED:\n{openai_review}\n\n"
        f"GROK REVISED:\n{xai_review}\n\nCreate one joint decision. Separate: agreed actions, "
        "disagreements or uncertainty, owner for each action, and the immediate next step."
    )
    joint = await _ask("openai", _base_instructions("joint decision"), synthesis_prompt)
    record_id, created = str(uuid.uuid4()), int(time.time())
    with _database() as db:
        db.execute(
            """INSERT INTO agent_rounds
            (id,created_at,task,context,openai_first,xai_first,openai_review,xai_review,joint_decision,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (record_id, created, payload.task, payload.context, openai_first, xai_first,
             openai_review, xai_review, joint, "complete"),
        )
    return {
        "id": record_id,
        "created_at": created,
        "status": "complete",
        "openai": {"first": openai_first, "review": openai_review},
        "grok": {"first": xai_first, "review": xai_review},
        "joint_decision": joint,
    }


@router.post("/coordinate", include_in_schema=False)
async def coordinate_agents(
    request: Request,
    payload: CoordinationRequest = Body(...),
    agentnotary_report_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _authorize(request, agentnotary_report_session, authorization)
    try:
        return await coordinate(payload)
    except (httpx.HTTPError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/rounds", include_in_schema=False)
def recent_rounds(
    request: Request,
    agentnotary_report_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _authorize(request, agentnotary_report_session, authorization)
    with _database() as db:
        rows = db.execute(
            "SELECT id,created_at,task,joint_decision,status FROM agent_rounds ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return {"rounds": [dict(row) for row in rows]}
