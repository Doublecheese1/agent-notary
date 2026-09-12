"""Read-only RPC and unsigned testnet transactions. Never stores keys or broadcasts."""
import json
import os
import re
from pathlib import Path
from decimal import Decimal
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from web3 import Web3
from eth_abi import encode

ROOT = Path(__file__).resolve().parent
CHAIN = 421614
USDC = "0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d"
ABI = json.loads((ROOT / "artifacts/AgentNotaryEscrow.json").read_text())["abi"]
STATES = ["NONE", "LOCKED", "SETTLED", "REJECTED", "EXPIRED"]
router = APIRouter(prefix="/payments", tags=["Testnet payments"])


def address(value):
    if not Web3.is_address(value) or int(value, 16) == 0:
        raise HTTPException(422, "A nonzero EVM wallet address is required.")
    return Web3.to_checksum_address(value)


def digest(value):
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", value):
        raise HTTPException(422, "Expected a 32-byte hex identifier.")
    return bytes.fromhex(value[2:])


def units(value):
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,6})?", value):
        raise HTTPException(422, "Use a decimal string with at most 6 fractional digits.")
    n = int(Decimal(value) * 1000000)
    if not 0 < n <= 1000000000:
        raise HTTPException(422, "Budget must be greater than zero and at most 1000 test USDC.")
    return n


def quote_values(n):
    commission = n * 150 // 10000
    return {"amount_units": n, "locked_units": n + 5000, "fee_units": commission + 5000,
            "payout_units": n - commission, "rejection_refund_units": n,
            "rejection_fee_units": 5000, "expiry_refund_units": n + 5000}


def connection():
    if os.getenv("PAYMENTS_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "Testnet payments are not configured. Sandbox /play is still available.")
    rpc = os.getenv("PAYMENTS_RPC_URL", "")
    if not rpc.startswith("https://"):
        raise HTTPException(503, "An HTTPS testnet RPC URL is required.")
    escrow_address = address(os.getenv("PAYMENTS_ESCROW_ADDRESS", ""))
    treasury = address(os.getenv("PAYMENTS_TREASURY_ADDRESS", ""))
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
        if w3.eth.chain_id != CHAIN:
            raise HTTPException(503, "Wrong network: only Arbitrum Sepolia is supported.")
        contract = w3.eth.contract(address=escrow_address, abi=ABI)
        if not w3.eth.get_code(escrow_address):
            raise HTTPException(503, "No escrow contract at the configured address.")
        if contract.functions.token().call() != USDC or contract.functions.treasury().call() != treasury:
            raise HTTPException(503, "Configured token or treasury does not match the deployed contract.")
        return w3, contract
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Testnet RPC unavailable or incompatible escrow. No transaction was sent.")


def tx(sender, target, data):
    return {"from": sender, "to": target, "data": data, "value": "0x0", "chainId": hex(CHAIN)}


class Lock(BaseModel):
    buyer: str
    seller: str
    amount: str = "1"
    salt: str
    expected_text: str = Field(min_length=1, max_length=4096)
    duration_seconds: int = Field(default=3600, ge=60, le=604700)


class Delivery(BaseModel):
    seller: str
    text: str = Field(min_length=1, max_length=4096)


class Refund(BaseModel):
    caller: str


class Deploy(BaseModel):
    deployer: str
    treasury: str


@router.post("/prepare-deployment")
def prepare_deployment(req: Deploy):
    deployer, treasury = address(req.deployer), address(req.treasury)
    artifact = json.loads((ROOT / "artifacts/AgentNotaryEscrow.json").read_text())
    data = artifact["bytecode"] + encode(["address", "address"], [USDC, treasury]).hex()
    return {"transaction": {"from": deployer, "data": data, "value": "0x0", "chainId": hex(CHAIN)},
            "token": USDC, "treasury": treasury, "testnet_only": True}


@router.get("", include_in_schema=False)
def page():
    return FileResponse(ROOT / "static/payments.html", headers={"Cache-Control": "no-store"})


@router.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(ROOT / "static/payments.js", media_type="text/javascript")


@router.get("/config")
def config():
    enabled = os.getenv("PAYMENTS_ENABLED", "false").lower() == "true"
    if not enabled:
        return {"enabled": False, "testnet_only": True, "chain_id": CHAIN}
    _, c = connection()
    return {"enabled": True, "testnet_only": True, "chain_id": CHAIN, "token": USDC,
            "escrow": c.address, "treasury": c.functions.treasury().call(), "decimals": 6}


@router.get("/quote")
def quote(amount: str = "1"):
    return quote_values(units(amount))


@router.post("/prepare-lock")
def prepare_lock(req: Lock):
    buyer, seller = address(req.buyer), address(req.seller)
    if buyer == seller:
        raise HTTPException(422, "Use separate buyer and seller wallets.")
    salt, n = digest(req.salt), units(req.amount)
    raw = req.expected_text.encode("utf-8")
    if len(raw) > 4096:
        raise HTTPException(422, "Delivery cannot exceed 4096 UTF-8 bytes.")
    w3, c = connection()
    expected = Web3.keccak(raw)
    deal_id = Web3.keccak(encode(["address", "bytes32"], [buyer, salt]))
    if c.functions.deals(deal_id).call()[-1] != 0:
        raise HTTPException(409, "This deal already exists. Read its state; do not create another payment.")
    deadline = w3.eth.get_block("latest")["timestamp"] + req.duration_seconds
    q = quote_values(n)
    approve = Web3.keccak(text="approve(address,uint256)")[:4] + encode(["address", "uint256"], [c.address, q["locked_units"]])
    return {"deal_id": Web3.to_hex(deal_id), "expected_hash": Web3.to_hex(expected), "deadline": deadline,
            **q, "approval": tx(buyer, USDC, Web3.to_hex(approve)),
            "lock": tx(buyer, c.address, c.functions.lock(salt, seller, n, expected, deadline)._encode_transaction_data())}


@router.get("/deals/{deal_id}")
def state(deal_id: str):
    key = digest(deal_id)
    w3, c = connection()
    block = w3.eth.block_number
    d = c.functions.deals(key).call(block_identifier=block)
    if d[-1] == 0:
        raise HTTPException(404, "Deal not observed on this chain.")
    q = quote_values(d[2])
    outcome = {"fee_units": 0, "payout_units": 0, "refund_units": 0}
    if d[6] == 2:
        outcome.update(fee_units=q["fee_units"], payout_units=q["payout_units"])
    elif d[6] == 3:
        outcome.update(fee_units=5000, refund_units=d[2])
    elif d[6] == 4:
        outcome.update(refund_units=q["expiry_refund_units"])
    return {"deal_id": deal_id, "buyer": d[0], "seller": d[1], "amount_units": d[2], "deadline": d[3],
            "outcome": outcome, "decimals": 6, "asset": "test USDC",
            "expected_hash": Web3.to_hex(d[4]), "delivered_hash": Web3.to_hex(d[5]),
            "state": STATES[d[6]], "observed_block": block, "finality": "latest observed; not a finality guarantee"}


@router.post("/deals/{deal_id}/prepare-delivery")
def prepare_delivery(deal_id: str, req: Delivery):
    key, seller = digest(deal_id), address(req.seller)
    raw = req.text.encode("utf-8")
    if len(raw) > 4096:
        raise HTTPException(422, "Delivery cannot exceed 4096 UTF-8 bytes.")
    w3, c = connection()
    d = c.functions.deals(key).call()
    if d[-1] != 1 or d[1] != seller or w3.eth.get_block("latest")["timestamp"] >= d[3]:
        raise HTTPException(409, "Deal is not locked for this seller or has expired.")
    return {"transaction": tx(seller, c.address, c.functions.deliver(key, raw)._encode_transaction_data())}


@router.post("/deals/{deal_id}/prepare-refund")
def prepare_refund(deal_id: str, req: Refund):
    key, caller = digest(deal_id), address(req.caller)
    w3, c = connection()
    d = c.functions.deals(key).call()
    if d[-1] != 1 or w3.eth.get_block("latest")["timestamp"] < d[3]:
        raise HTTPException(409, "Deal is not eligible for expiry refund.")
    return {"transaction": tx(caller, c.address, c.functions.refundExpired(key)._encode_transaction_data())}
