import json
import unittest
from pathlib import Path

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider


ROOT = Path(__file__).resolve().parent


def artifact(name):
    return json.loads((ROOT / "artifacts" / f"{name}.json").read_text(encoding="utf-8"))


class MainnetContractSecurityTest(unittest.TestCase):
    def setUp(self):
        self.w3 = Web3(EthereumTesterProvider())
        self.accounts = self.w3.eth.accounts
        self.token = self.deploy("TestUSDC")
        self.quorum = self.deploy(
            "AgentNotaryValidatorQuorum", self.accounts[3], self.accounts[4], self.accounts[5]
        )
        self.resolver = self.deploy(
            "AgentNotaryAIReviewResolver",
            self.accounts[0], self.accounts[2], self.accounts[1],
            self.accounts[3], self.accounts[4], self.accounts[5],
            250_000_000, 24 * 60 * 60, 8500,
        )
        self.escrow = self.deploy(
            "AgentNotaryMainnetEscrow",
            self.token.address, self.accounts[1], self.accounts[0],
            self.quorum.address, self.resolver.address,
        )

    def deploy(self, name, *arguments):
        compiled = artifact(name)
        factory = self.w3.eth.contract(abi=compiled["abi"], bytecode=compiled["bytecode"])
        tx_hash = factory.constructor(*arguments).transact({"from": self.accounts[0]})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.assertEqual(receipt.status, 1)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=compiled["abi"])

    def test_new_funds_gate_starts_closed_and_only_operations_can_open_it(self):
        self.assertTrue(self.escrow.functions.paused().call())
        self.assertFalse(self.escrow.functions.publicAccess().call())
        self.assertEqual(self.escrow.functions.totalEscrowed().call(), 0)
        with self.assertRaises(Exception):
            self.escrow.functions.resumeNewDeals().transact({"from": self.accounts[6]})
        with self.assertRaises(Exception):
            self.escrow.functions.setPublicAccess(True).transact({"from": self.accounts[6]})
        self.escrow.functions.resumeNewDeals().transact({"from": self.accounts[0]})
        self.escrow.functions.setPublicAccess(True).transact({"from": self.accounts[0]})
        self.assertFalse(self.escrow.functions.paused().call())
        self.assertTrue(self.escrow.functions.publicAccess().call())

    def test_access_list_and_resolver_rotation_are_operations_only(self):
        buyer = self.accounts[7]
        with self.assertRaises(Exception):
            self.escrow.functions.setBuyerAccess(buyer, True).transact({"from": self.accounts[6]})
        with self.assertRaises(Exception):
            self.escrow.functions.setAutomaticValidator(self.accounts[8]).transact({"from": self.accounts[6]})
        with self.assertRaises(Exception):
            self.escrow.functions.setReviewArbitrator(self.accounts[8]).transact({"from": self.accounts[6]})
        self.escrow.functions.setBuyerAccess(buyer, True).transact({"from": self.accounts[0]})
        self.assertTrue(self.escrow.functions.approvedBuyers(buyer).call())

    def test_review_resolver_binds_once_and_only_to_the_matching_escrow(self):
        with self.assertRaises(Exception):
            self.resolver.functions.bindEscrow(self.escrow.address).transact({"from": self.accounts[6]})
        self.resolver.functions.bindEscrow(self.escrow.address).transact({"from": self.accounts[0]})
        self.assertEqual(self.resolver.functions.escrow().call(), self.escrow.address)
        with self.assertRaises(Exception):
            self.resolver.functions.bindEscrow(self.escrow.address).transact({"from": self.accounts[0]})

    def test_duplicate_quorum_and_ai_signers_are_rejected(self):
        with self.assertRaises(Exception):
            self.deploy(
                "AgentNotaryValidatorQuorum", self.accounts[3], self.accounts[3], self.accounts[5]
            )
        with self.assertRaises(Exception):
            self.deploy(
                "AgentNotaryAIReviewResolver",
                self.accounts[0], self.accounts[2], self.accounts[1],
                self.accounts[3], self.accounts[3], self.accounts[5],
                250_000_000, 24 * 60 * 60, 8500,
            )

    def test_escrow_exposes_no_generic_withdraw_or_sweep_function(self):
        names = {item["name"] for item in artifact("AgentNotaryMainnetEscrow")["abi"] if item.get("type") == "function"}
        self.assertFalse(names & {"withdraw", "sweep", "rescue", "emergencyWithdraw"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
