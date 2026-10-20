"""Unsigned AgentNotary client. It never stores a key or broadcasts a transaction."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from eth_abi import encode
from web3 import Web3


@dataclass(frozen=True)
class DealRequest:
    salt: bytes
    seller: str
    mode: int
    amount: int
    arbitration_reserve: int
    fallback_seller_bps: int
    manifest_hash: bytes
    policy_hash: bytes
    acceptance_window: int
    delivery_window: int
    decision_window: int
    arbitration_window: int

    def contract_tuple(self) -> tuple[Any, ...]:
        return (
            self.salt, Web3.to_checksum_address(self.seller), self.mode, self.amount,
            self.arbitration_reserve, self.fallback_seller_bps, self.manifest_hash,
            self.policy_hash, self.acceptance_window, self.delivery_window,
            self.decision_window, self.arbitration_window,
        )


class AgentNotaryClient:
    """Builds reviewable transaction intents for an injected wallet/session-key layer."""

    def __init__(self, web3: Web3, escrow_address: str, artifact_path: str | Path, expected_chain_id: int = 42161):
        self.web3 = web3
        self.expected_chain_id = expected_chain_id
        artifact = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
        self.escrow = web3.eth.contract(address=Web3.to_checksum_address(escrow_address), abi=artifact["abi"])

    def _assert_chain(self) -> None:
        if self.web3.eth.chain_id != self.expected_chain_id:
            raise RuntimeError(f"wrong chain: expected {self.expected_chain_id}, got {self.web3.eth.chain_id}")

    def deal_id(self, buyer: str, request: DealRequest) -> bytes:
        return Web3.keccak(encode(
            ["address", "uint256", "address", "address", "bytes32"],
            [self.escrow.address, self.expected_chain_id, Web3.to_checksum_address(buyer),
             Web3.to_checksum_address(request.seller), request.salt],
        ))

    def prepare_proposal(self, buyer: str, request: DealRequest) -> dict[str, Any]:
        self._assert_chain()
        buyer = Web3.to_checksum_address(buyer)
        data = self.escrow.functions.proposeDeal(request.contract_tuple())._encode_transaction_data()
        return {"from": buyer, "to": self.escrow.address, "data": data, "value": "0x0", "chainId": hex(self.expected_chain_id)}

    def prepare_action(self, caller: str, function_name: str, *args: Any) -> dict[str, Any]:
        self._assert_chain()
        allowed = {
            "sellerAccept", "cancelProposal", "expireProposal", "deliver", "expireUndelivered",
            "submitValidation", "acceptDelivery", "disputeDelivery", "finalizeIfSilent",
            "resolveReview", "finalizeUnresolvedAutomatic", "finalizeUnresolvedReview",
        }
        if function_name not in allowed:
            raise ValueError("unsupported escrow action")
        data = getattr(self.escrow.functions, function_name)(*args)._encode_transaction_data()
        return {"from": Web3.to_checksum_address(caller), "to": self.escrow.address, "data": data,
                "value": "0x0", "chainId": hex(self.expected_chain_id)}


class OperationJournal:
    """Prevents a caller from assigning one operation ID to two different intents."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS operations (operation_id TEXT PRIMARY KEY, intent_hash TEXT NOT NULL, tx_hash TEXT, status TEXT NOT NULL)")
        self.db.commit()

    @staticmethod
    def intent_hash(intent: dict[str, Any]) -> str:
        encoded = json.dumps(intent, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def reserve(self, operation_id: str, intent: dict[str, Any]) -> dict[str, Any]:
        digest = self.intent_hash(intent)
        row = self.db.execute("SELECT intent_hash, tx_hash, status FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if row:
            if row[0] != digest:
                raise ValueError("operation ID is already bound to a different intent")
            return {"operation_id": operation_id, "intent_hash": row[0], "tx_hash": row[1], "status": row[2]}
        self.db.execute("INSERT INTO operations VALUES (?, ?, NULL, 'PREPARED')", (operation_id, digest))
        self.db.commit()
        return {"operation_id": operation_id, "intent_hash": digest, "tx_hash": None, "status": "PREPARED"}

    def submitted(self, operation_id: str, tx_hash: str) -> None:
        current = self.db.execute("SELECT tx_hash FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if not current:
            raise KeyError("unknown operation ID")
        if current[0] and current[0].lower() != tx_hash.lower():
            raise ValueError("operation already has a different transaction hash")
        self.db.execute("UPDATE operations SET tx_hash=?, status='SUBMITTED' WHERE operation_id=?", (tx_hash, operation_id))
        self.db.commit()

    def close(self) -> None:
        self.db.close()
