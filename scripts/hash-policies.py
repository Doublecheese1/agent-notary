"""Print deployment-ready Keccak-256 hashes for the exact policy file bytes."""
from pathlib import Path
from web3 import Web3

root = Path(__file__).resolve().parents[1]
for name in ("automatic-json-evidence-v1.json", "buyer-review-v1.json"):
    data = (root / "policies" / name).read_bytes().rstrip(b"\r\n")
    print(f"{name}={Web3.to_hex(Web3.keccak(data))}")
