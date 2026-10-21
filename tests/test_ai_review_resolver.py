import json
import unittest
from pathlib import Path

from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider


ROOT = Path(__file__).resolve().parents[1]
USDC = 10**6


class AIReviewResolverTest(unittest.TestCase):
    def setUp(self):
        self.backend = PyEVMBackend()
        self.tester = EthereumTester(backend=self.backend)
        self.w3 = Web3(EthereumTesterProvider(self.tester))
        (self.buyer, self.seller, self.treasury, self.ops, self.human,
         self.signer_a, self.signer_b, self.signer_c, self.relayer, self.other) = self.w3.eth.accounts[:10]

        self.token = self._deploy("TestUSDC")
        self.validator = self._deploy("AgentNotaryValidatorQuorum", self.signer_a, self.signer_b, self.signer_c)
        self.resolver = self._deploy(
            "AgentNotaryAIReviewResolver",
            self.ops, self.human, self.treasury,
            self.signer_a, self.signer_b, self.signer_c,
            250 * USDC, 3600, 8500,
        )
        self.escrow = self._deploy(
            "AgentNotaryMainnetEscrow",
            self.token.address, self.treasury, self.ops, self.validator.address, self.resolver.address,
        )
        self.resolver.functions.bindEscrow(self.escrow.address).transact({"from": self.ops})
        self.escrow.functions.setBuyerAccess(self.buyer, True).transact({"from": self.ops})
        self.escrow.functions.resumeNewDeals().transact({"from": self.ops})
        self.token.functions.approve(self.escrow.address, 2_000 * USDC).transact({"from": self.buyer})
        self.token.functions.mint(self.seller, 500 * USDC).transact({"from": self.buyer})
        self.token.functions.approve(self.escrow.address, 500 * USDC).transact({"from": self.seller})

    def _artifact(self, name):
        return json.loads((ROOT / "artifacts" / f"{name}.json").read_text())

    def _deploy(self, name, *args):
        artifact = self._artifact(name)
        factory = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx = factory.constructor(*args).transact({"from": self.buyer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    def _hash(self, text):
        return Web3.keccak(text=text)

    def _disputed_deal(self, amount=100 * USDC, arbitration=604800):
        reserve = self.escrow.functions.arbitrationReserveFor(amount).call()
        request = (
            self._hash(f"salt-{amount}-{arbitration}"), self.seller, 1, amount, reserve, 0,
            self._hash("manifest"), self._hash("policy"), 3600, 3600, 172800, arbitration,
        )
        tx = self.escrow.functions.proposeDeal(request).transact({"from": self.buyer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        deal_id = self.escrow.events.DealProposed().process_receipt(receipt)[0]["args"]["id"]
        self.escrow.functions.sellerAccept(deal_id).transact({"from": self.seller})
        self.escrow.functions.deliver(deal_id, self._hash("content"), "ipfs://delivery").transact({"from": self.seller})
        self.escrow.functions.disputeDelivery(deal_id, self._hash("reason"), "ipfs://evidence").transact({"from": self.buyer})
        return deal_id

    def _signatures(self, deal_id, decision=0, confidence=9000, flags=0, nonce=0):
        package_hash = self._hash("immutable-package")
        report_hash = self._hash("combined-ai-report")
        deadline = self.tester.get_block_by_number("latest")["timestamp"] + 1800
        message = encode_typed_data(full_message={
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"},
                ],
                "AIReview": [
                    {"name": "dealId", "type": "bytes32"}, {"name": "decision", "type": "uint8"},
                    {"name": "packageHash", "type": "bytes32"}, {"name": "reportHash", "type": "bytes32"},
                    {"name": "confidenceBps", "type": "uint16"}, {"name": "flags", "type": "uint32"},
                    {"name": "nonce", "type": "uint256"}, {"name": "signatureDeadline", "type": "uint256"},
                ],
            },
            "primaryType": "AIReview",
            "domain": {
                "name": "AgentNotaryAIReviewResolver", "version": "1",
                "chainId": self.w3.eth.chain_id, "verifyingContract": self.resolver.address,
            },
            "message": {
                "dealId": deal_id, "decision": decision, "packageHash": package_hash,
                "reportHash": report_hash, "confidenceBps": confidence, "flags": flags,
                "nonce": nonce, "signatureDeadline": deadline,
            },
        })
        signatures = []
        for signer in (self.signer_a, self.signer_b):
            key = self.backend.account_keys[self.w3.eth.accounts.index(signer)]
            signatures.append(Account.sign_message(message, private_key=key).signature)
        return package_hash, report_hash, deadline, signatures

    def _propose_ai(self, deal_id, decision=0, confidence=9000, flags=0):
        package_hash, report_hash, deadline, signatures = self._signatures(
            deal_id, decision=decision, confidence=confidence, flags=flags
        )
        return self.resolver.functions.proposeAIResolution(
            deal_id, decision, package_hash, report_hash, confidence, flags, 0, deadline, signatures
        ).transact({"from": self.relayer})

    def _travel(self, timestamp):
        self.tester.time_travel(timestamp + 1)
        self.tester.mine_block()

    def test_two_ai_signatures_stage_then_finalize_after_appeal_window(self):
        deal_id = self._disputed_deal()
        self._propose_ai(deal_id, decision=0)
        pending = self.resolver.functions.pendingRulings(deal_id).call()
        with self.assertRaises(TransactionFailed):
            self.resolver.functions.finalizeAIResolution(deal_id).transact({"from": self.other})
        self._travel(pending[4])
        self.resolver.functions.finalizeAIResolution(deal_id).transact({"from": self.other})
        self.assertEqual(self.escrow.functions.deals(deal_id).call()[4], 5)
        self.assertGreater(self.token.functions.balanceOf(self.resolver.address).call(), 0)
        self.resolver.functions.sweepFees(self.token.address).transact({"from": self.other})
        self.assertGreater(self.token.functions.balanceOf(self.treasury).call(), 0)

    def test_party_appeal_blocks_ai_and_human_safe_resolves(self):
        deal_id = self._disputed_deal()
        self._propose_ai(deal_id, decision=0)
        self.resolver.functions.appeal(deal_id).transact({"from": self.buyer})
        pending = self.resolver.functions.pendingRulings(deal_id).call()
        self._travel(pending[4])
        with self.assertRaises(TransactionFailed):
            self.resolver.functions.finalizeAIResolution(deal_id).transact({"from": self.other})
        with self.assertRaises(TransactionFailed):
            self.resolver.functions.humanResolve(deal_id, 1).transact({"from": self.other})
        self.resolver.functions.humanResolve(deal_id, 1).transact({"from": self.human})
        self.assertEqual(self.escrow.functions.deals(deal_id).call()[4], 6)

    def test_low_confidence_or_flags_cannot_stage_automatic_ruling(self):
        deal_id = self._disputed_deal()
        with self.assertRaises(TransactionFailed):
            self._propose_ai(deal_id, confidence=8000)
        with self.assertRaises(TransactionFailed):
            self._propose_ai(deal_id, flags=1)

    def test_high_value_case_goes_directly_to_human_safe(self):
        deal_id = self._disputed_deal(amount=300 * USDC)
        with self.assertRaises(TransactionFailed):
            self._propose_ai(deal_id)
        self.resolver.functions.humanResolve(deal_id, 0).transact({"from": self.human})
        self.assertEqual(self.escrow.functions.deals(deal_id).call()[4], 5)

    def test_duplicate_ai_signer_is_rejected(self):
        deal_id = self._disputed_deal()
        package_hash, report_hash, deadline, signatures = self._signatures(deal_id)
        with self.assertRaises(TransactionFailed):
            self.resolver.functions.proposeAIResolution(
                deal_id, 0, package_hash, report_hash, 9000, 0, 0, deadline,
                [signatures[0], signatures[0]],
            ).transact({"from": self.relayer})


if __name__ == "__main__":
    unittest.main()
