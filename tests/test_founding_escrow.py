import unittest
import test_open_escrow as helpers
from web3 import Web3


class FoundingTests(unittest.TestCase):
    # Reuse only helpers, not the paid-contract tests and expectations.
    deploy_artifact = helpers.OpenEscrowTests.deploy_artifact
    balance = helpers.OpenEscrowTests.balance
    now = helpers.OpenEscrowTests.now
    travel = helpers.OpenEscrowTests.travel
    assert_reverts = helpers.OpenEscrowTests.assert_reverts
    both_accept = helpers.OpenEscrowTests.both_accept
    deliver = helpers.OpenEscrowTests.deliver

    def setUp(self):
        helpers.OpenEscrowTests.setUp(self)
        self.c = self.deploy_artifact('AgentNotaryFoundingEscrow', [self.token.address, self.treasury])

    def admit(self):
        self.c.functions.admitMember(self.buyer).transact({'from': self.treasury})

    def propose(self, fee=0):
        self.counter += 1
        self.token.functions.approve(self.c.address, 10_000_000 + fee).transact({'from': self.buyer})
        tx = self.c.functions.proposeDeal(
            self.counter.to_bytes(32, 'big'), self.seller, self.arbiter,
            10_000_000, fee, 4000, Web3.keccak(b'agreed terms'), 3600, 3600, 3600, 3600
        ).transact({'from': self.buyer})
        receipt = self.w.eth.wait_for_transaction_receipt(tx)
        return self.c.events.Proposed().process_receipt(receipt)[0]['args']['id']

    def test_membership_authorization_duplicates_and_limit(self):
        self.assert_reverts('pilot membership required', self.propose)
        self.assert_reverts('admissions only', lambda: self.c.functions.admitMember(self.buyer).transact({'from': self.other}))
        self.admit()
        self.assert_reverts('already member', self.admit)
        for n in range(1, 50):
            member = Web3.to_checksum_address('0x' + (10000 + n).to_bytes(20, 'big').hex())
            self.c.functions.admitMember(member).transact({'from': self.treasury})
        self.assertEqual(self.c.functions.memberCount().call(), 50)
        self.assert_reverts('pilot full', lambda: self.c.functions.admitMember(self.other).transact({'from': self.treasury}))

    def test_nonzero_arbiter_fee_rejected(self):
        self.admit()
        self.assert_reverts('bad arbiter fee', lambda: self.propose(fee=1))

    def test_all_terminal_paths_conserve_funds_without_service_fees(self):
        self.admit()
        self.assertEqual(self.c.functions.FIXED_FEE().call(), 0)
        for outcome in ['accepted', 'silent', 'seller', 'buyer', 'stalemate', 'proposal_expired', 'undelivered']:
            with self.subTest(outcome=outcome):
                buyer_before = self.balance(self.buyer)
                seller_before = self.balance(self.seller)
                key = self.propose()
                self.assertEqual(self.balance(self.c.address), 10_000_000)
                if outcome == 'proposal_expired':
                    self.travel(self.now() + 3601)
                    self.c.functions.expireProposal(key).transact({'from': self.other})
                else:
                    self.both_accept(key)
                    if outcome == 'undelivered':
                        self.travel(self.now() + 3601)
                        self.c.functions.expireUndelivered(key).transact({'from': self.other})
                    else:
                        self.deliver(key)
                        if outcome == 'accepted':
                            self.c.functions.acceptDelivery(key).transact({'from': self.buyer})
                        elif outcome == 'silent':
                            self.travel(self.now() + 3601)
                            self.c.functions.finalizeIfSilent(key).transact({'from': self.other})
                        else:
                            self.c.functions.disputeDelivery(key, Web3.keccak(b'reason')).transact({'from': self.buyer})
                            if outcome == 'stalemate':
                                self.travel(self.now() + 3601)
                                self.c.functions.finalizeStalemate(key).transact({'from': self.other})
                            else:
                                self.c.functions.arbitrate(key, outcome == 'seller').transact({'from': self.arbiter})
                payout = 10_000_000 if outcome in ['accepted', 'silent', 'seller'] else 4_000_000 if outcome == 'stalemate' else 0
                self.assertEqual(self.balance(self.seller) - seller_before, payout)
                self.assertEqual(buyer_before - self.balance(self.buyer), payout)
                self.assertEqual(self.balance(self.treasury), 0)
                self.assertEqual(self.balance(self.arbiter), 0)
                self.assertEqual(self.balance(self.c.address), 0)
                self.assert_reverts('not delivered', lambda: self.c.functions.acceptDelivery(key).transact({'from': self.buyer}))
