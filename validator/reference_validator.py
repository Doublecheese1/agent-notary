"""Deterministic reference validator. It performs no network calls and holds no signing key."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from web3 import Web3

POLICY_ID = "agentnotary.json-evidence.v1"
POLICY_DOCUMENT = {
    "id": POLICY_ID,
    "description": "Exact content hash plus bounded JSON field, count and uniqueness checks",
    "max_max_bytes": 1_048_576,
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def policy_hash() -> bytes:
    return Web3.keccak(canonical_json(POLICY_DOCUMENT))


@dataclass(frozen=True)
class ValidationResult:
    decision: str
    evidence_hash: bytes
    evidence: dict[str, Any]


def _result(decision: str, checks: list[dict[str, Any]], deal_id: str, contract: str, chain_id: int) -> ValidationResult:
    evidence = {
        "version": "agentnotary.validation-evidence.v1",
        "deal_id": deal_id.lower(),
        "contract": contract.lower(),
        "chain_id": chain_id,
        "policy_id": POLICY_ID,
        "decision": decision,
        "checks": checks,
    }
    return ValidationResult(decision, Web3.keccak(canonical_json(evidence)), evidence)


def validate(*, deal_id: str, contract: str, chain_id: int, manifest_bytes: bytes,
             expected_manifest_hash: bytes, expected_policy_hash: bytes,
             content_bytes: bytes | None, expected_content_hash: bytes) -> ValidationResult:
    checks: list[dict[str, Any]] = []
    if Web3.keccak(manifest_bytes) != expected_manifest_hash:
        checks.append({"check": "manifest_hash", "ok": False, "reason": "provided manifest bytes do not match the funded deal"})
        return _result("INCONCLUSIVE", checks, deal_id, contract, chain_id)
    if policy_hash() != expected_policy_hash:
        checks.append({"check": "policy_hash", "ok": False, "reason": "validator policy version does not match the funded deal"})
        return _result("INCONCLUSIVE", checks, deal_id, contract, chain_id)
    if content_bytes is None:
        checks.append({"check": "content_available", "ok": False})
        return _result("INCONCLUSIVE", checks, deal_id, contract, chain_id)
    if Web3.keccak(content_bytes) != expected_content_hash:
        checks.append({"check": "content_hash", "ok": False, "reason": "retrieved bytes do not match seller commitment"})
        return _result("INCONCLUSIVE", checks, deal_id, contract, chain_id)

    try:
        manifest = json.loads(manifest_bytes)
        content = json.loads(content_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        checks.append({"check": "valid_json", "ok": False})
        return _result("FAIL", checks, deal_id, contract, chain_id)

    max_bytes = manifest.get("max_bytes")
    if not isinstance(max_bytes, int) or not 1 <= max_bytes <= POLICY_DOCUMENT["max_max_bytes"]:
        checks.append({"check": "valid_manifest_max_bytes", "ok": False})
        return _result("FAIL", checks, deal_id, contract, chain_id)
    checks.append({"check": "max_bytes", "ok": len(content_bytes) <= max_bytes, "actual": len(content_bytes), "expected_max": max_bytes})

    type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}
    required = manifest.get("required_fields", {})
    if not isinstance(required, dict) or any(value not in type_map for value in required.values()):
        checks.append({"check": "valid_required_fields", "ok": False})
        return _result("FAIL", checks, deal_id, contract, chain_id)
    if not isinstance(content, dict):
        checks.append({"check": "root_object", "ok": False})
    else:
        for field, expected_type in sorted(required.items()):
            value = content.get(field)
            ok = field in content and isinstance(value, type_map[expected_type]) and not (expected_type == "integer" and isinstance(value, bool))
            checks.append({"check": "required_field", "field": field, "type": expected_type, "ok": ok})

    array_rule = manifest.get("array_rule")
    if array_rule is not None:
        if not isinstance(array_rule, dict) or not isinstance(content, dict):
            checks.append({"check": "valid_array_rule", "ok": False})
        else:
            field = array_rule.get("field")
            rows = content.get(field)
            ok_array = isinstance(rows, list)
            checks.append({"check": "array", "field": field, "ok": ok_array})
            if ok_array:
                minimum, maximum = array_rule.get("min_items", 0), array_rule.get("max_items", 10_000)
                checks.append({"check": "item_count", "ok": isinstance(minimum, int) and isinstance(maximum, int) and minimum <= len(rows) <= maximum,
                               "actual": len(rows), "min": minimum, "max": maximum})
                unique_by = array_rule.get("unique_by")
                if unique_by:
                    values = [row.get(unique_by) for row in rows if isinstance(row, dict)]
                    checks.append({"check": "unique", "field": unique_by,
                                   "ok": len(values) == len(rows) and None not in values and len(set(map(str, values))) == len(values)})

    decision = "PASS" if checks and all(check["ok"] for check in checks) else "FAIL"
    return _result(decision, checks, deal_id, contract, chain_id)
