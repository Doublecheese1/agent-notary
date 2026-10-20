import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validator"))
from web3 import Web3
from reference_validator import canonical_json, policy_hash, validate


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        self.manifest = canonical_json({
            "max_bytes": 10_000,
            "required_fields": {"records": "array", "source": "string"},
            "array_rule": {"field": "records", "min_items": 2, "max_items": 3, "unique_by": "id"},
        })
        self.content = canonical_json({"source": "signed-api", "records": [{"id": 1}, {"id": 2}]})
        self.args = dict(deal_id="0x" + "11" * 32, contract="0x" + "22" * 20, chain_id=42161,
                         manifest_bytes=self.manifest, expected_manifest_hash=Web3.keccak(self.manifest),
                         expected_policy_hash=policy_hash(), content_bytes=self.content,
                         expected_content_hash=Web3.keccak(self.content))

    def test_pass_is_deterministic(self):
        first = validate(**self.args)
        second = validate(**self.args)
        self.assertEqual(first.decision, "PASS")
        self.assertEqual(first.evidence_hash, second.evidence_hash)

    def test_duplicate_or_missing_rows_fail(self):
        content = canonical_json({"source": "signed-api", "records": [{"id": 1}, {"id": 1}]})
        result = validate(**{**self.args, "content_bytes": content, "expected_content_hash": Web3.keccak(content)})
        self.assertEqual(result.decision, "FAIL")

    def test_unavailable_or_wrong_bytes_are_inconclusive(self):
        self.assertEqual(validate(**{**self.args, "content_bytes": None}).decision, "INCONCLUSIVE")
        self.assertEqual(validate(**{**self.args, "content_bytes": b"different"}).decision, "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
