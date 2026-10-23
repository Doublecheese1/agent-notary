"""Minimal, cookie-free launch events written to application logs."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field


router = APIRouter(prefix="/internal/analytics", tags=["Internal analytics"])
logger = logging.getLogger("agentsolis.launch")
_ATTEMPTS: dict[str, list[float]] = {}


class LaunchEvent(BaseModel):
    event: Literal[
        "landing_view", "buyer_click", "seller_click", "demo_click",
        "founding_click", "language_click", "guide_click",
    ]
    path: str = Field(default="/", max_length=120, pattern=r"^/[A-Za-z0-9/_-]*$")
    language: str = Field(default="en", max_length=12, pattern=r"^[A-Za-z-]+$")
    campaign: str = Field(default="", max_length=80, pattern=r"^[A-Za-z0-9._-]*$")


@router.post("/event", include_in_schema=False, status_code=204)
def record_launch_event(item: LaunchEvent, request: Request) -> Response:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [stamp for stamp in _ATTEMPTS.get(key, []) if now - stamp < 60]
    if len(recent) >= 120:
        raise HTTPException(status_code=429, detail="Too many analytics events")
    recent.append(now)
    _ATTEMPTS[key] = recent
    logger.info(
        "AGENTSOLIS_EVENT %s",
        json.dumps(
            {
                "event": item.event,
                "path": item.path,
                "language": item.language,
                "campaign": item.campaign,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
            separators=(",", ":"),
        ),
    )
    return Response(status_code=204)
