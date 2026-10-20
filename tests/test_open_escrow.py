"""Local AgentNotaryOpenEscrow contract tests using the compiled artifacts."""
import json
import unittest
from pathlib import Path

from eth_tester import EthereumTester, PyEVMBackend
from eth_tester.exceptions import TransactionFailed
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

ROOT = Path(__file__).resolve().parent.parent


class OpenEscrowTests(unittest.TestCase):
    def setUp(self):
        # Explicit backend: EthereumTester()'s default backend does not
        # implement time_travel/mine_blocks (raises NotImplementedError).
        # PyEVMBackend does, and matches the py-evm dependency already pinned
        # for this project.
        self.tester = EthereumTester(backend=PyEVMBackend())
        self.w = Web3(EthereumTesterProvider(self.tester))
        self.buyer, self.seller, self.treasury, self.arbiter, self.other = self.w.eth.accounts[:5]
        self.token = self.deploy_artifact('TestUSDC', [])
        self.c = self.deploy_artifact('AgentNotaryOpenEscrow', [self.token.address, self.treasury])
        self.counter = 0

    def deploy_artifact(self, name, args):
        artifact = json.loads((ROOT / 'artifacts' / (name + '.json')).read_text())
        factory = self.w.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode'])
        tx_hash = factory.constructor(*args).transact({'from': self.buyer})
        receipt = self.w.eth.wait_for_transaction_receipt(tx_hash)
        return self.w.eth.contract(address=receipt.contractAddress, abi=artifact['abi'])

    def balance(self, who):
        return self.token.functions.balanceOf(who).call()

    def now(self):
        return self.w.eth.get_block('latest')['timestamp']

    def travel(self, ts):
        self.tester.time_travel(ts)
        self.tester.mine_blocks(1)

    def assert_reverts(self, reason_substring, fn):
        """
        Confirms an ACTUAL on-chain revert with the expected reason string.
        Deliberately does NOT catch bare Exception: a typo'd function name
        raises a Web3/ABI-level AttributeError or ValidationError, not a
        TransactionFailed, and must NOT be swallowed as if it were a passing
        negative test.
        """
        with self.assertRaises(TransactionFailed) as ctx:
            fn()
        self.assertIn(reason_substring, str(ctx.exception))

    # proposeDeal ABI order, exactly as declared in the contract:
    # (salt, seller, arbiter, amount, arbiterFee, splitBps, termsHash,
    #  acceptanceWindow, submitWindow, disputeWindow, arbitrationWindow)
    def propose(self, amount=10_000_000, arbiter_fee=200_000, split_bps=4000,
                acc_win=3600, submit_win=3600, dispute_win=3600, arb_win=3600,
                seller=None, arbiter=None, terms=b'terms v1'):
        self.counter += 1
        salt = self.counter.to_bytes(32, 'big')
        seller = self.seller if seller is None else seller
        arbiter = self.arbiter if arbiter is None else arbiter
        total = amount + 5000 + arbiter_fee
        self.token.functions.approve(self.c.address, total).transact({'from': self.buyer})
        terms_hash = Web3.keccak(terms)
        tx_hash = self.c.functions.proposeDeal(
            salt, seller, arbiter, amount, arbiter_fee, split_bps, terms_hash,
            acc_win, submit_win, dispute_win, arb_win
        ).transact({'from': self.buyer})
        receipt = self.w.eth.wait_for_transaction_receipt(tx_hash)
        # transact() returns a TRANSACTION HASH, not the deal id. The deal id
        # is a keccak256 computed inside the contract from msg.sender + salt +
        # a domain string; the only reliable way to get it back is to decode
        # the Proposed event the constructor emits, not to recompute it
        # client-side (recomputing it independently just duplicates the
        # contract's exact encoding and silently drifts if that ever changes).
        events = self.c.events.Proposed().process_receipt(receipt)
        self.assertEqual(len(events), 1)
        deal_id = events[0]['args']['id']
        return deal_id, total

    def both_accept(self, deal_id, seller=None, arbiter=None):
        seller = self.seller if seller is None else seller
        arbiter = self.arbiter if arbiter is None else arbiter
        self.c.functions.sellerAccept(deal_id).transact({'from': seller})
        self.c.functions.arbiterAccept(deal_id).transact({'from': arbiter})

    def deliver(self, deal_id, content=b'result', uri='ipfs://xyz', seller=None):
        seller = self.seller if seller is None else seller
        return self.c.functions.deliver(deal_id, Web3.keccak(content), uri).transact({'from': seller})

    # ---- creation invariants ----

    def test_no_deal_without_valid_split_bps(self):
        self.assert_reverts('splitBps out of range', lambda: self.propose(split_bps=10001))

    def test_terms_amount_arbiter_windows_immutable(self):
        # There is no setter for any of these fields anywhere in the ABI.
        artifact = json.loads((ROOT / 'artifacts' / 'AgentNotaryOpenEscrow.json').read_text())
        fn_names = {f['name'] for f in artifact['abi'] if f.get('type') == 'function'}
        for forbidden in ('setTerms', 'setSplitBps', 'setArbiter', 'setAmount', 'setWindows', 'updateDeal'):
            self.assertNotIn(forbidden, fn_names)

    def test_no_pause_or_owner_recovery_function(self):
        artifact = json.loads((ROOT / 'artifacts' / 'AgentNotaryOpenEscrow.json').read_text())
        fn_names = {f['name'] for f in artifact['abi'] if f.get('type') == 'function'}
        for forbidden in ('pause', 'unpause', 'emergencyWithdraw', 'rescueFunds', 'sweep', 'owner'):
            self.assertNotIn(forbidden, fn_names)

    # ---- happy paths ----

    def test_explicit_accept_pays_correctly_and_totals_match(self):
        start_buyer = self.balance(self.buyer)
        deal_id, total = self.propose(amount=10_000_000, arbiter_fee=200_000)
        self.assertEqual(self.balance(self.c.address), total)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.c.functions.acceptDelivery(deal_id).transact({'from': self.buyer})

        commission = 10_000_000 * 150 // 10000  # 150000
        seller_payout = 10_000_000 - commission  # 9850000
        treasury_amount = commission + 5000       # 155000
        arbiter_refund = 200_000

        self.assertEqual(self.balance(self.seller), seller_payout)
        self.assertEqual(self.balance(self.treasury), treasury_amount)
        self.assertEqual(self.balance(self.buyer), start_buyer - total + arbiter_refund)
        self.assertEqual(self.balance(self.c.address), 0)
        self.assertEqual(seller_payout + treasury_amount + arbiter_refund, total)

    def test_delivered_event_carries_uri(self):
        deal_id, _ = self.propose()
        self.both_accept(deal_id)
        tx_hash = self.deliver(deal_id, uri='ipfs://specific-cid')
        receipt = self.w.eth.wait_for_transaction_receipt(tx_hash)
        events = self.c.events.Delivered().process_receipt(receipt)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['args']['uri'], 'ipfs://specific-cid')

    def test_silent_acceptance_after_dispute_window(self):
        deal_id, _ = self.propose(dispute_win=3600)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.assert_reverts(
            'dispute window still open',
            lambda: self.c.functions.finalizeIfSilent(deal_id).transact({'from': self.other})
        )
        self.travel(self.now() + 3601)
        self.c.functions.finalizeIfSilent(deal_id).transact({'from': self.other})  # permissionless
        self.assertEqual(self.balance(self.c.address), 0)

    # ---- arbitration paths ----

    def test_arbiter_rules_for_seller(self):
        deal_id, total = self.propose(amount=10_000_000, arbiter_fee=200_000)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.c.functions.disputeDelivery(deal_id, Web3.keccak(b'reason')).transact({'from': self.buyer})
        self.c.functions.arbitrate(deal_id, True).transact({'from': self.arbiter})  # True = seller wins

        commission = 10_000_000 * 150 // 10000
        seller_payout = 10_000_000 - commission
        treasury_amount = commission + 5000
        self.assertEqual(self.balance(self.seller), seller_payout)
        self.assertEqual(self.balance(self.treasury), treasury_amount)
        self.assertEqual(self.balance(self.arbiter), 200_000)
        self.assertEqual(self.balance(self.c.address), 0)
        self.assertEqual(seller_payout + treasury_amount + 200_000, total)

    def test_arbiter_rules_for_buyer(self):
        start_buyer = self.balance(self.buyer)
        deal_id, total = self.propose(amount=10_000_000, arbiter_fee=200_000)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.c.functions.disputeDelivery(deal_id, Web3.keccak(b'reason')).transact({'from': self.buyer})
        self.c.functions.arbitrate(deal_id, False).transact({'from': self.arbiter})  # False = buyer wins

        self.assertEqual(self.balance(self.seller), 0)
        self.assertEqual(self.balance(self.treasury), 5000)
        self.assertEqual(self.balance(self.arbiter), 200_000)
        self.assertEqual(self.balance(self.buyer), start_buyer - total + 10_000_000)
        self.assertEqual(self.balance(self.c.address), 0)

    # ---- the mandatory exit rule: arbiter never rules ----

    def test_finalize_stalemate_applies_split_bps_exactly_and_treasury_gets_zero(self):
        deal_id, total = self.propose(amount=10_000_000, arbiter_fee=200_000, split_bps=4000, arb_win=3600)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.c.functions.disputeDelivery(deal_id, Web3.keccak(b'reason')).transact({'from': self.buyer})
        self.assert_reverts(
            'arbitration window still open',
            lambda: self.c.functions.finalizeStalemate(deal_id).transact({'from': self.other})
        )
        self.travel(self.now() + 3601)

        self.c.functions.finalizeStalemate(deal_id).transact({'from': self.other})  # permissionless

        seller_amount = 10_000_000 * 4000 // 10000  # 4,000,000
        buyer_amount = (10_000_000 - seller_amount) + 200_000 + 5000  # 6,205,000

        self.assertEqual(self.balance(self.seller), seller_amount)
        self.assertEqual(self.balance(self.arbiter), 0)   # arbiter never ruled, gets nothing
        self.assertEqual(self.balance(self.treasury), 0)  # treasury gets zero, by design
        self.assertEqual(self.balance(self.c.address), 0)
        self.assertEqual(seller_amount + buyer_amount, total)

        # cannot run twice
        self.assert_reverts(
            'not disputed',
            lambda: self.c.functions.finalizeStalemate(deal_id).transact({'from': self.other})
        )

    def test_finalize_stalemate_zero_split_bps(self):
        deal_id, _ = self.propose(amount=10_000_000, arbiter_fee=200_000, split_bps=0, arb_win=3600)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.c.functions.disputeDelivery(deal_id, Web3.keccak(b'reason')).transact({'from': self.buyer})
        self.travel(self.now() + 3601)
        self.c.functions.finalizeStalemate(deal_id).transact({'from': self.other})
        self.assertEqual(self.balance(self.seller), 0)
        self.assertEqual(self.balance(self.c.address), 0)

    def test_arbitrate_after_deadline_reverts_finalize_still_available(self):
        deal_id, _ = self.propose(arb_win=3600)
        self.both_accept(deal_id)
        self.deliver(deal_id)
        self.c.functions.disputeDelivery(deal_id, Web3.keccak(b'reason')).transact({'from': self.buyer})
        self.travel(self.now() + 3601)
        self.assert_reverts(
            'arbitration window closed',
            lambda: self.c.functions.arbitrate(deal_id, True).transact({'from': self.arbiter})
        )
        self.c.functions.finalizeStalemate(deal_id).transact({'from': self.other})  # still resolvable

    # ---- expiry / permissionless timeout paths (no dead ends) ----

    def test_expire_proposal_full_refund_when_not_both_accepted(self):
        start_buyer = self.balance(self.buyer)
        deal_id, _ = self.propose(acc_win=3600)
        self.c.functions.sellerAccept(deal_id).transact({'from': self.seller})  # only one side accepts
        self.travel(self.now() + 3601)
        self.assert_reverts(
            'not locked',
            lambda: self.deliver(deal_id)
        )
        self.c.functions.expireProposal(deal_id).transact({'from': self.other})
        self.assertEqual(self.balance(self.buyer), start_buyer)
        self.assertEqual(self.balance(self.c.address), 0)
        self.assert_reverts(
            'not proposed',
            lambda: self.c.functions.expireProposal(deal_id).transact({'from': self.other})
        )

    def test_expire_undelivered_full_refund(self):
        start_buyer = self.balance(self.buyer)
        deal_id, _ = self.propose(submit_win=3600)
        self.both_accept(deal_id)
        self.travel(self.now() + 3601)
        self.assert_reverts(
            'submit window closed',
            lambda: self.deliver(deal_id)
        )
        self.c.functions.expireUndelivered(deal_id).transact({'from': self.other})
        self.assertEqual(self.balance(self.buyer), start_buyer)
        self.assertEqual(self.balance(self.c.address), 0)

    # ---- authorization ----

    def test_only_designated_parties_can_act(self):
        deal_id, _ = self.propose()
        self.assert_reverts('seller only', lambda: self.c.functions.sellerAccept(deal_id).transact({'from': self.other}))
        self.assert_reverts('arbiter only', lambda: self.c.functions.arbiterAccept(deal_id).transact({'from': self.other}))
        self.both_accept(deal_id)
        self.assert_reverts('seller only', lambda: self.deliver(deal_id, seller=self.other))
        self.deliver(deal_id)
        self.assert_reverts('buyer only', lambda: self.c.functions.acceptDelivery(deal_id).transact({'from': self.other}))
        self.assert_reverts(
            'buyer only',
            lambda: self.c.functions.disputeDelivery(deal_id, Web3.keccak(b'r')).transact({'from': self.other})
        )

    def test_arbiter_cannot_equal_buyer_seller_or_treasury(self):
        self.assert_reverts('arbiter must be distinct', lambda: self.propose(arbiter=self.buyer))
        self.assert_reverts('arbiter must be distinct', lambda: self.propose(arbiter=self.seller))
        self.assert_reverts('arbiter must be distinct', lambda: self.propose(arbiter=self.treasury))


if __name__ == '__main__':
    unittest.main()
