"""Wallet-free sandbox; runs an isolated copy of the unchanged legacy engine."""
import importlib.util
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_sandbox_engine", ROOT / "legacy.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
router = APIRouter()
mutex = threading.RLock()
TTL_SECONDS = 900
MAX_DEALS = 1000


def prune():
    cutoff = time.time() - TTL_SECONDS
    for key, deal in list(engine.DEALS_DB.items()):
        if deal["created_at"] < cutoff:
            del engine.DEALS_DB[key]


@router.get("/play", include_in_schema=False)
def play():
    return FileResponse(ROOT / "static" / "play.html", headers={"Cache-Control": "no-cache"})


@router.get("/play/app.js", include_in_schema=False)
def javascript():
    return FileResponse(ROOT / "static" / "app.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@router.get("/sandbox/health", tags=["Sandbox"])
def health():
    return {"status": "ONLINE", "mode": "sandbox", "real_money": False, "retention_seconds": TTL_SECONDS}


@router.post("/sandbox/v1/deals/lock", status_code=201, tags=["Sandbox"])
def lock(req: engine.CreateDealRequest):
    with mutex:
        prune()
        if len(engine.DEALS_DB) >= MAX_DEALS:
            raise HTTPException(429, "Sandbox is full. Please try again later.")
        return engine.lock_deal(req)


@router.post("/sandbox/v1/deals/settle", tags=["Sandbox"])
def settle(req: engine.SettleDealRequest):
    with mutex:
        prune()
        return engine.settle_deal(req)
