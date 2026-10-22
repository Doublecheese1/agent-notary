import json
import os
import unittest
import warnings
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_abi import encode
from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

warnings.filterwarnings("ignore", message="The log with transaction hash.*MismatchedABI")


ROOT = Path(__file__).resolve().parents[1]
USDC = 10**6


class MainnetEscrowTest(unittest.TestCase):
    def setUp(self):
        self.backend = PyEVMBackend()
        self.tester = EthereumTester(backend=self.backend)
        self.w3 = Web3(EthereumTesterProvider(self.tester))
        (self.buyer, self.seller, self.treasury, self.ops, self.validator_a,
         self.arbitrator, self.relayer, self.validator_b, self.validator_c,
         self.other) = self.w3.eth.accounts[:10]

        token_artifact = self._artifact("TestUSDC")
        token_factory = self.w3.eth.contract(abi=token_artifact["abi"], bytecode=token_artifact["bytecode"])
        receipt = self.w3.eth.wait_for_transaction_receipt(token_factory.constructor().transact({"from": self.buyer}))
        self.token = self.w3.eth.contract(address=receipt.contractAddress, abi=token_artifact["abi"])

        quorum_artifact = self._artifact("AgentNotaryValidatorQuorum")
        quorum_factory = self.w3.eth.contract(abi=quorum_artifact["abi"], bytecode=quorum_artifact["bytecode"])
        receipt = self.w3.eth.wait_for_transaction_receipt(quorum_factory.constructor(
            self.validator_a, self.validator_b, self.validator_c
        ).transact({"from": self.buyer}))
        self.quorum = self.w3.eth.contract(address=receipt.contractAddress, abi=quorum_artifact["abi"])

        escrow_artifact = self._artifact("AgentNotaryMainnetEscrow")
        escrow_factory = self.w3.eth.contract(abi=escrow_artifact["abi"], bytecode=escrow_artifact["bytecode"])
        receipt = self.w3.eth.wait_for_transaction_receipt(escrow_factory.constructor(
            self.token.address, self.treasury, self.ops, self.quorum.address, self.arbitrator
        ).transact({"from": self.buyer}))
        self.escrow = self.w3.eth.contract(address=receipt.contractAddress, abi=escrow_artifact["abi"])
        self.initially_paused = self.escrow.functions.paused().call()
        self.escrow.functions.setBuyerAccess(self.buyer, True).transact({"from": self.ops})
        self.escrow.functions.resumeNewDeals().transact({"from": self.ops})
        self.token.functions.approve(self.escrow.address, 10_000 * USDC).transact({"from": self.buyer})
        self.token.functions.mint(self.seller, 500 * USDC).transact({"from": self.buyer})
        self.token.functions.approve(self.escrow.address, 500 * USDC).transact({"from": self.seller})
        self.counter = 0

    def _artifact(self, name):
        return json.loads((ROOT / "artifacts" / f"{name}.json").read_text())

    def _hash(self, text):
        return Web3.keccak(text=text)

    def _request(self, mode=0, amount=10 * USDC, reserve=0, fallback=0,
                 acceptance=3600, delivery=3600, decision=3600, arbitration=3600):
        self.counter += 1
        return (
            self._hash(f"salt-{self.counter}"), self.seller, mode, amount, reserve,
            fallback, self._hash("manifest-v1"), self._hash("policy-v1"),
            acceptance, delivery, decision, arbitration
        )

    def _propose(self, request):
        tx = self.escrow.functions.proposeDeal(request).transact({"from": self.buyer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        return self.escrow.events.DealProposed().process_receipt(receipt)[0]["args"]["id"]

    def _accept_deliver(self, deal_id, content=None):
        self.escrow.functions.sellerAccept(deal_id).transact({"from": self.seller})
        content = content or self._hash("delivered bytes")
        self.escrow.functions.deliver(deal_id, content, "ipfs://bafy-test").transact({"from": self.seller})
        return content

    def _deal(self, deal_id):
        return self.escrow.functions.deals(deal_id).call()

    def _travel_after(self, timestamp):
        self.tester.time_travel(timestamp + 1)
        self.tester.mine_block()

    def _validation_signature(self, deal_id, content_hash, decision, evidence_hash, nonce, deadline):
        message = encode_typed_data(full_message={
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Validation": [
                    {"name": "dealId", "type": "bytes32"},
                    {"name": "contentHash", "type": "bytes32"},
                    {"name": "manifestHash", "type": "bytes32"},
                    {"name": "policyHash", "type": "bytes32"},
                    {"name": "decision", "type": "uint8"},
                    {"name": "evidenceHash", "type": "bytes32"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "signatureDeadline", "type": "uint256"},
                ],
            },
            "primaryType": "Validation",
            "domain": {
                "name": "AgentNotaryMainnetEscrow", "version": "1",
                "chainId": self.w3.eth.chain_id, "verifyingContract": self.escrow.address,
            },
            "message": {
                "dealId": deal_id, "contentHash": content_hash,
                "manifestHash": self._deal(deal_id)[10], "policyHash": self._deal(deal_id)[11],
                "decision": decision, "evidenceHash": evidence_hash,
                "nonce": nonce, "signatureDeadline": deadline,
            },
        })
        signatures = []
        for validator in (self.validator_a, self.validator_b):
            key = self.backend.account_keys[self.w3.eth.accounts.index(validator)]
            signatures.append(Account.sign_message(message, private_key=key).signature)
        return encode(["bytes[]"], [signatures])

    def _submit_validation(self, deal_id, content, decision, nonce=0):
        evidence = self._hash(f"evidence-{nonce}")
        deadline = self.tester.get_block_by_number("latest")["timestamp"] + 1800
        signature = self._validation_signature(deal_id, content, decision, evidence, nonce, deadline)
        self.escrow.functions.submitValidation(deal_id, decision, evidence, deadline, signature).transact({"from": self.relayer})
        return evidence, deadline, signature

    def test_deployment_starts_paused(self):
        self.assertTrue(self.initially_paused)

    def test_amount_above_1000_is_allowed_and_fee_caps_at_50(self):
        amount = 5_000 * USDC
        deal_id = self._propose(self._request(amount=amount))
        deal = self._deal(deal_id)
        self.assertEqual(deal[5], amount)
        self.assertEqual(deal[8], 50 * USDC)
        self.escrow.functions.cancelProposal(deal_id).transact({"from": self.buyer})
        self.assertEqual(self.escrow.functions.totalEscrowed().call(), 0)

    def test_buyer_review_rejects_short_decision_or_arbitration_windows(self):
        amount = 100 * USDC
        reserve = self.escrow.functions.arbitrationReserveFor(amount).call()
        with self.assertRaises(TransactionFailed):
            self._propose(self._request(
                mode=1, amount=amount, reserve=reserve,
                decision=172799, arbitration=604800,
            ))
        with self.assertRaises(TransactionFailed):
            self._propose(self._request(
                mode=1, amount=amount, reserve=reserve,
                decision=172800, arbitration=604799,
            ))

    def test_automatic_pass_pays_seller_and_protocol(self):
        deal_id = self._propose(self._request())
        content = self._accept_deliver(deal_id)
        seller_before = self.token.functions.balanceOf(self.seller).call()
        treasury_before = self.token.functions.balanceOf(self.treasury).call()
        self._submit_validation(deal_id, content, 0)
        self.assertEqual(self.token.functions.balanceOf(self.seller).call() - seller_before, 9_850_000)
        self.assertEqual(self.token.functions.balanceOf(self.treasury).call() - treasury_before, 150_000)
        self.assertEqual(self._deal(deal_id)[4], 5)  # Paid
        self.assertEqual(self.escrow.functions.totalEscrowed().call(), 0)

    def test_automatic_fail_refunds_full_amount(self):
        before = self.token.functions.balanceOf(self.buyer).call()
        deal_id = self._propose(self._request())
        content = self._accept_deliver(deal_id)
        self._submit_validation(deal_id, content, 1)
        self.assertEqual(self.token.functions.balanceOf(self.buyer).call(), before)
        self.assertEqual(self.token.functions.balanceOf(self.treasury).call(), 0)

    def test_signature_is_scoped_and_cannot_be_replayed(self):
        deal_id = self._propose(self._request())
        content = self._accept_deliver(deal_id)
        evidence, deadline, signature = self._submit_validation(deal_id, content, 2)
        with self.assertRaises(TransactionFailed):
            self.escrow.functions.submitValidation(deal_id, 2, evidence, deadline, signature).transact({"from": self.relayer})

        other_id = self._propose(self._request())
        self._accept_deliver(other_id, content)
        with self.assertRaises(TransactionFailed):
            self.escrow.functions.submitValidation(other_id, 2, evidence, deadline, signature).transact({"from": self.relayer})

    def test_one_validator_signature_is_not_enough(self):
        deal_id = self._propose(self._request())
        content = self._accept_deliver(deal_id)
        evidence = self._hash("evidence")
        deadline = self.tester.get_block_by_number("latest")["timestamp"] + 1800
        message = encode_typed_data(full_message={
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"},
                ],
                "Validation": [
                    {"name": "dealId", "type": "bytes32"}, {"name": "contentHash", "type": "bytes32"},
                    {"name": "manifestHash", "type": "bytes32"}, {"name": "policyHash", "type": "bytes32"},
                    {"name": "decision", "type": "uint8"}, {"name": "evidenceHash", "type": "bytes32"},
                    {"name": "nonce", "type": "uint256"}, {"name": "signatureDeadline", "type": "uint256"},
                ],
            },
            "primaryType": "Validation",
            "domain": {"name": "AgentNotaryMainnetEscrow", "version": "1", "chainId": self.w3.eth.chain_id, "verifyingContract": self.escrow.address},
            "message": {"dealId": deal_id, "contentHash": content, "manifestHash": self._deal(deal_id)[10],
                        "policyHash": self._deal(deal_id)[11], "decision": 0, "evidenceHash": evidence,
                        "nonce": 0, "signatureDeadline": deadline},
        })
        key = self.backend.account_keys[self.w3.eth.accounts.index(self.validator_a)]
        one_signature = encode(["bytes[]"], [[Account.sign_message(message, private_key=key).signature]])
        with self.assertRaises(TransactionFailed):
            self.escrow.functions.submitValidation(deal_id, 0, evidence, deadline, one_signature).transact({"from": self.relayer})

    def test_inconclusive_is_bounded_then_timeout_fallback(self):
        deal_id = self._propose(self._request(fallback=4000))
        content = self._accept_deliver(deal_id)
        for nonce in range(3):
            self._submit_validation(deal_id, content, 2, nonce)
        with self.assertRaises(TransactionFailed):
            self._submit_validation(deal_id, content, 2, 3)
        buyer_before = self.token.functions.balanceOf(self.buyer).call()
        seller_before = self.token.functions.balanceOf(self.seller).call()
        self._travel_after(self._deal(deal_id)[18])
        self.escrow.functions.finalizeUnresolvedAutomatic(deal_id).transact({"from": self.other})
        self.assertEqual(self.token.functions.balanceOf(self.seller).call() - seller_before, 4 * USDC)
        self.assertEqual(self.token.functions.balanceOf(self.buyer).call() - buyer_before, 6 * USDC)

    def test_review_accept_refunds_bonds_and_charges_protocol_fee(self):
        amount = 100 * USDC
        reserve = self.escrow.functions.arbitrationReserveFor(amount).call()
        deal_id = self._propose(self._request(mode=1, amount=amount, reserve=reserve, decision=172800, arbitration=604800))
        buyer_after_lock = self.token.functions.balanceOf(self.buyer).call()
        seller_before_accept = self.token.functions.balanceOf(self.seller).call()
        self._accept_deliver(deal_id)
        self.escrow.functions.acceptDelivery(deal_id).transact({"from": self.buyer})
        self.assertEqual(self.token.functions.balanceOf(self.buyer).call() - buyer_after_lock, reserve)
        self.assertEqual(self.token.functions.balanceOf(self.seller).call() - seller_before_accept, amount - 1_500_000)
        self.assertEqual(self.token.functions.balanceOf(self.treasury).call(), 1_500_000)

    def test_review_buyer_win_uses_seller_bond_and_refunds_buyer_reserve(self):
        amount = 100 * USDC
        reserve = self.escrow.functions.arbitrationReserveFor(amount).call()
        buyer_before = self.token.functions.balanceOf(self.buyer).call()
        seller_before = self.token.functions.balanceOf(self.seller).call()
        arb_before = self.token.functions.balanceOf(self.arbitrator).call()
        deal_id = self._propose(self._request(mode=1, amount=amount, reserve=reserve, decision=172800, arbitration=604800))
        self._accept_deliver(deal_id)
        self.escrow.functions.disputeDelivery(deal_id, self._hash("wrong result"), "ipfs://dispute").transact({"from": self.buyer})
        self.escrow.functions.resolveReview(deal_id, 1).transact({"from": self.arbitrator})
        self.assertEqual(self.token.functions.balanceOf(self.buyer).call(), buyer_before)
        self.assertEqual(seller_before - self.token.functions.balanceOf(self.seller).call(), reserve)
        self.assertEqual(self.token.functions.balanceOf(self.arbitrator).call() - arb_before, reserve)

    def test_review_seller_win_charges_buyer_reserve(self):
        amount = 100 * USDC
        reserve = self.escrow.functions.arbitrationReserveFor(amount).call()
        arb_before = self.token.functions.balanceOf(self.arbitrator).call()
        seller_before = self.token.functions.balanceOf(self.seller).call()
        deal_id = self._propose(self._request(mode=1, amount=amount, reserve=reserve, decision=172800, arbitration=604800))
        self._accept_deliver(deal_id)
        self.escrow.functions.disputeDelivery(deal_id, self._hash("claim"), "ipfs://dispute").transact({"from": self.buyer})
        self.escrow.functions.resolveReview(deal_id, 0).transact({"from": self.arbitrator})
        self.assertEqual(self.token.functions.balanceOf(self.arbitrator).call() - arb_before, reserve)
        self.assertEqual(self.token.functions.balanceOf(self.seller).call() - seller_before, amount - 1_500_000)

    def test_silence_cannot_finalize_before_24_hours(self):
        amount = 100 * USDC
        reserve = self.escrow.functions.arbitrationReserveFor(amount).call()
        deal_id = self._propose(self._request(mode=1, amount=amount, reserve=reserve, decision=172800, arbitration=604800))
        self._accept_deliver(deal_id)
        with self.assertRaises(TransactionFailed):
            self.escrow.functions.finalizeIfSilent(deal_id).transact({"from": self.other})
        self._travel_after(self._deal(deal_id)[18])
        self.escrow.functions.finalizeIfSilent(deal_id).transact({"from": self.other})
        self.assertEqual(self._deal(deal_id)[4], 5)

    def test_pause_blocks_new_deals_but_not_existing_exit(self):
        deal_id = self._propose(self._request())
        self.escrow.functions.pauseNewDeals().transact({"from": self.ops})
        with self.assertRaises(TransactionFailed):
            self._propose(self._request())
        self.escrow.functions.cancelProposal(deal_id).transact({"from": self.buyer})
        self.assertEqual(self._deal(deal_id)[4], 6)

    def test_founding_fee_is_snapshotted_at_funding(self):
        self.escrow.functions.admitFoundingBuyer(self.buyer).transact({"from": self.ops})
        deal_id = self._propose(self._request())
        self.assertEqual(self._deal(deal_id)[8], 0)
        content = self._accept_deliver(deal_id)
        self._submit_validation(deal_id, content, 0)
        self.assertEqual(self.token.functions.balanceOf(self.treasury).call(), 0)

    def test_no_admin_withdraw_or_rescue_entrypoint(self):
        names = {item.get("name") for item in self.escrow.abi if item.get("type") == "function"}
        self.assertFalse({"withdraw", "sweep", "rescue", "emergencyWithdraw"} & names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
