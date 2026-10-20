import os
import tempfile
import unittest
from unittest.mock import patch

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException

import negotiation


class NegotiationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "NEGOTIATION_ENABLED": "true",
            "NEGOTIATION_DB_PATH": os.path.join(self.temp.name, "negotiations.db"),
        }, clear=False)
        self.env.start()
        self.buyer = Account.create()
        self.seller = Account.create()
        self.terms = negotiation.Terms(
            title="Custom production job",
            description="Produce the agreed item to the final confirmed dimensions.",
            deliverables="Finished item and shipment tracking",
            limitations="Maximum printable area is 35 x 35 cm",
            evidence="Photo with ruler and shipping receipt",
            amount_usdc="100",
            delivery_days=3,
        )

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    @staticmethod
    def key(link):
        return link.split("#key=", 1)[1]

    def open(self):
        created = negotiation.create_negotiation(negotiation.CreateNegotiation(
            buyer=self.buyer.address, seller=self.seller.address, terms=self.terms
        ))
        return created, self.key(created["buyer_link"]), self.key(created["seller_link"])

    def test_private_links_separate_roles_and_protect_read(self):
        created, buyer_key, seller_key = self.open()
        buyer_view = negotiation.read_negotiation(created["id"], buyer_key)
        seller_view = negotiation.read_negotiation(created["id"], seller_key)
        self.assertEqual(buyer_view["role"], "buyer")
        self.assertEqual(seller_view["role"], "seller")
        self.assertEqual(buyer_view["terms_hash"], created["terms_hash"])
        with self.assertRaises(HTTPException):
            negotiation.read_negotiation(created["id"], "wrong-key")

    def test_new_revision_clears_acceptance_and_both_wallets_must_sign(self):
        created, buyer_key, seller_key = self.open()
        initial = negotiation.read_negotiation(created["id"], buyer_key)
        buyer_signature = Account.sign_message(
            encode_defunct(text=initial["acceptance_statement"]), self.buyer.key
        ).signature.hex()
        after_buyer = negotiation.accept_revision(
            created["id"], negotiation.AcceptanceRequest(signature=buyer_signature), buyer_key
        )
        self.assertEqual(after_buyer["status"], "AWAITING_SIGNATURE")
        self.assertTrue(after_buyer["buyer_accepted"])

        revised_terms = self.terms.model_copy(update={"limitations": "Maximum size is 34 x 34 cm"})
        revised = negotiation.propose_revision(
            created["id"], negotiation.RevisionRequest(terms=revised_terms), seller_key
        )
        self.assertEqual(revised["current_revision"], 2)
        self.assertFalse(revised["buyer_accepted"])
        self.assertFalse(revised["seller_accepted"])

        buyer_sig = Account.sign_message(
            encode_defunct(text=revised["acceptance_statement"]), self.buyer.key
        ).signature.hex()
        negotiation.accept_revision(created["id"], negotiation.AcceptanceRequest(signature=buyer_sig), buyer_key)
        seller_view = negotiation.read_negotiation(created["id"], seller_key)
        seller_sig = Account.sign_message(
            encode_defunct(text=seller_view["acceptance_statement"]), self.seller.key
        ).signature.hex()
        agreed = negotiation.accept_revision(
            created["id"], negotiation.AcceptanceRequest(signature=seller_sig), seller_key
        )
        self.assertEqual(agreed["status"], "AGREED")
        self.assertTrue(agreed["buyer_accepted"] and agreed["seller_accepted"])
        with self.assertRaises(HTTPException):
            negotiation.propose_revision(
                created["id"], negotiation.RevisionRequest(terms=self.terms), buyer_key
            )

    def test_message_is_context_and_does_not_change_terms(self):
        created, _, seller_key = self.open()
        before = negotiation.read_negotiation(created["id"], seller_key)
        after = negotiation.post_message(
            created["id"], negotiation.MessageRequest(body="My printer can only make 35 x 35 cm."), seller_key
        )
        self.assertEqual(after["terms_hash"], before["terms_hash"])
        self.assertEqual(after["messages"][-1]["role"], "seller")


if __name__ == "__main__":
    unittest.main(verbosity=2)
