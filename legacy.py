import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="AgentSolis Clearinghouse",
    version="1.0.0",
    description="Escrow workflow demo for agent-to-agent jobs.",
    docs_url="/docs" if os.getenv("PUBLIC_API_DOCS", "false").lower() == "true" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if os.getenv("PUBLIC_API_DOCS", "false").lower() == "true" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "PUBLIC_CORS_ORIGINS", "https://agentsolis.solists.com.tr"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-AgentNotary-Report-Token"],
)

# =====================================================================
# MODELLER
# =====================================================================

class CreateDealRequest(BaseModel):
    buyer_agent_id: str = Field(min_length=1, max_length=128)
    seller_agent_id: str = Field(min_length=1, max_length=128)
    amount_usd: float = Field(gt=0, description="Escrowed transaction amount in USD")
    criteria: str = Field(min_length=1, max_length=20_000, description="Markdown or text rules specifying acceptance criteria")
    timeout_seconds: int = Field(default=86400, ge=60, le=604800, description="Auto-release timeout in seconds (default: 24h)")

class SettleDealRequest(BaseModel):
    deal_id: str
    seller_agent_id: str
    deliverable: Dict[str, Any]

# =====================================================================
# KASA VE PARİBU CÜZDAN AYARI
# =====================================================================

LEGACY_SIMULATED_PAYOUT_WALLET = "0x19cb83a03aed8ec032ab0f6b115e196d4b386727"
PAYOUT_NETWORK = "Arbitrum One"

DEALS_DB: Dict[str, Dict[str, Any]] = {}
PLATFORM_TREASURY = {
    "network": PAYOUT_NETWORK,
    "treasury_wallet": LEGACY_SIMULATED_PAYOUT_WALLET,
    "total_settled_volume_usd": 0.0,
    "total_commission_earned_usd": 0.0,
    "total_transactions": 0
}

COMMISSION_RATE = 0.015       # %1.5 komisyon
FIXED_ARBITRATION_FEE = 0.005 # $0.005 hakem denetim bedeli

# =====================================================================
# HAKEM MOTORU
# =====================================================================

def evaluate_deliverable(criteria: str, payload: Dict[str, Any]) -> tuple[bool, str]:
    if not payload:
        return False, "Payload is completely empty."

    if "result" not in payload and "data" not in payload:
        return False, "Missing mandatory 'result' or 'data' root key."

    content = payload.get("result") or payload.get("data")
    if isinstance(content, list) and len(content) == 0:
        return False, "Delivered list contains 0 items."

    if isinstance(content, str) and len(content.strip()) < 5:
        return False, "Delivered content is truncated or trivial."

    return True, "Deliverable matches structured validation criteria."

# =====================================================================
# API UÇLARI
# =====================================================================

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


def _require_legacy_public_api() -> None:
    if os.getenv("LEGACY_PUBLIC_API", "false").lower() != "true":
        raise HTTPException(410, "This legacy demo endpoint is retired. Use /sandbox/v1/deals instead.")

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ONLINE", "timestamp": time.time()}

@app.post("/v1/deals/lock", include_in_schema=False, status_code=status.HTTP_201_CREATED)
def lock_deal(req: CreateDealRequest):
    _require_legacy_public_api()
    deal_id = f"deal_{uuid.uuid4().hex[:12]}"
    created_at = time.time()
    total_locked = req.amount_usd + FIXED_ARBITRATION_FEE

    DEALS_DB[deal_id] = {
        "deal_id": deal_id,
        "buyer": req.buyer_agent_id,
        "seller": req.seller_agent_id,
        "amount_usd": req.amount_usd,
        "arbitration_fee": FIXED_ARBITRATION_FEE,
        "criteria": req.criteria,
        "status": "LOCKED",
        "created_at": created_at,
        "expires_at": created_at + req.timeout_seconds,
        "deliverable_hash": None
    }

    return {
        "status": "LOCKED",
        "deal_id": deal_id,
        "locked_amount_usd": total_locked,
        "expires_at": DEALS_DB[deal_id]["expires_at"]
    }

@app.post("/v1/deals/settle", include_in_schema=False)
def settle_deal(req: SettleDealRequest):
    _require_legacy_public_api()
    if len(json.dumps(req.deliverable, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) > 65_536:
        raise HTTPException(status_code=413, detail="Deliverable is too large.")
    deal = DEALS_DB.get(req.deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    if deal["status"] != "LOCKED":
        raise HTTPException(status_code=400, detail=f"Cannot settle deal with status: {deal['status']}")

    if deal["seller"] != req.seller_agent_id:
        raise HTTPException(status_code=403, detail="Unauthorized seller agent.")

    raw_str = json.dumps(req.deliverable, sort_keys=True)
    proof_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    deal["deliverable_hash"] = proof_hash

    is_valid, reason = evaluate_deliverable(deal["criteria"], req.deliverable)

    if is_valid:
        commission = round(deal["amount_usd"] * COMMISSION_RATE, 4)
        seller_net = round(deal["amount_usd"] - commission, 4)

        deal["status"] = "SETTLED"
        deal["settled_at"] = time.time()

        PLATFORM_TREASURY["total_settled_volume_usd"] += deal["amount_usd"]
        PLATFORM_TREASURY["total_commission_earned_usd"] += (commission + deal["arbitration_fee"])
        PLATFORM_TREASURY["total_transactions"] += 1

        return {
            "decision": "APPROVED",
            "proof_hash": proof_hash,
            "seller_payout_usd": seller_net,
            "protocol_fee_usd": commission + deal["arbitration_fee"],
            "refund_to_buyer_usd": 0.0,
            "credited_treasury": LEGACY_SIMULATED_PAYOUT_WALLET
        }
    else:
        deal["status"] = "REJECTED"
        deal["settled_at"] = time.time()

        PLATFORM_TREASURY["total_commission_earned_usd"] += deal["arbitration_fee"]
        PLATFORM_TREASURY["total_transactions"] += 1

        return {
            "decision": "REJECTED",
            "proof_hash": proof_hash,
            "reason": reason,
            "seller_payout_usd": 0.0,
            "protocol_fee_usd": deal["arbitration_fee"],
            "refund_to_buyer_usd": deal["amount_usd"]
        }

@app.get("/v1/analytics/treasury", include_in_schema=False)
def get_treasury_metrics():
    _require_legacy_public_api()
    return {
        "metrics": PLATFORM_TREASURY,
        "active_escrow_count": len([d for d in DEALS_DB.values() if d["status"] == "LOCKED"])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
