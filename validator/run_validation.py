"""Run the deterministic validator on local bytes. No network and no signing key."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from web3 import Web3

from reference_validator import validate


def bytes32(value: str) -> bytes:
    raw = Web3.to_bytes(hexstr=value)
    if len(raw) != 32:
        raise argparse.ArgumentTypeError("expected a 32-byte 0x hash")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deal-id", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--chain-id", type=int, default=42161)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--content", type=Path)
    parser.add_argument("--manifest-hash", type=bytes32, required=True)
    parser.add_argument("--policy-hash", type=bytes32, required=True)
    parser.add_argument("--content-hash", type=bytes32, required=True)
    args = parser.parse_args()

    result = validate(
        deal_id=args.deal_id,
        contract=args.contract,
        chain_id=args.chain_id,
        manifest_bytes=args.manifest.read_bytes(),
        expected_manifest_hash=args.manifest_hash,
        expected_policy_hash=args.policy_hash,
        content_bytes=args.content.read_bytes() if args.content else None,
        expected_content_hash=args.content_hash,
    )
    print(json.dumps({
        "decision": result.decision,
        "evidence_hash": Web3.to_hex(result.evidence_hash),
        "evidence": result.evidence,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
