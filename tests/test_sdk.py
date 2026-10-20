import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))

from eth_tester import EthereumTester, PyEVMBackend
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider
from agentnotary_client import AgentNotaryClient, DealRequest, OperationJournal

ROOT = Path(__file__).resolve().parents[1]


class SdkTest(unittest.TestCase):
    def setUp(self):
        self.w3 = Web3(EthereumTesterProvider(EthereumTester(backend=PyEVMBackend())))
        artifact = json.loads((ROOT / "artifacts" / "AgentNotaryMainnetEscrow.json").read_text())
        self.fake_contract = self.w3.eth.accounts[9]
        self.client = AgentNotaryClient(self.w3, self.fake_contract, ROOT / "artifacts" / "AgentNotaryMainnetEscrow.json", self.w3.eth.chain_id)
        self.request = DealRequest(
            Web3.keccak(text="salt"), self.w3.eth.accounts[1], 0, 10_000_000, 0, 0,
            Web3.keccak(text="manifest"), Web3.keccak(text="policy"), 3600, 3600, 3600, 3600,
        )

    def test_builds_unsigned_intent_and_stable_deal_id(self):
        intent = self.client.prepare_proposal(self.w3.eth.accounts[0], self.request)
        self.assertEqual(set(intent), {"from", "to", "data", "value", "chainId"})
        self.assertNotIn("privateKey", intent)
        self.assertEqual(self.client.deal_id(self.w3.eth.accounts[0], self.request), self.client.deal_id(self.w3.eth.accounts[0], self.request))

    def test_operation_id_cannot_be_rebound_or_double_submitted(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = OperationJournal(Path(directory) / "ops.sqlite")
            intent = self.client.prepare_proposal(self.w3.eth.accounts[0], self.request)
            first = journal.reserve("external-job-17", intent)
            self.assertEqual(journal.reserve("external-job-17", intent), first)
            with self.assertRaises(ValueError):
                journal.reserve("external-job-17", {**intent, "value": "0x1"})
            journal.submitted("external-job-17", "0x" + "11" * 32)
            journal.submitted("external-job-17", "0x" + "11" * 32)
            with self.assertRaises(ValueError):
                journal.submitted("external-job-17", "0x" + "22" * 32)
            journal.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
