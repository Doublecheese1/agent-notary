import os
import tempfile
import unittest
from unittest.mock import patch

from eth_account import Account
from eth_account.messages import encode_defunct

import founding50


class Founding50ApplicationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp.name, "founding.sqlite3")
        self.env = patch.dict(os.environ, {
            "FOUNDING50_APPLICATIONS_OPEN": "true",
            "FOUNDING50_DB_PATH": self.db_path,
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_signed_application_is_recorded_once(self):
        wallet = Account.create()
        challenge = founding50.challenge(founding50.WalletRequest(wallet=wallet.address))
        signature = Account.sign_message(
            encode_defunct(text=challenge["message"]), wallet.key
        ).signature.hex()
        request = founding50.ApplicationRequest(
            wallet=wallet.address, nonce=challenge["nonce"], signature=signature,
            use_case="Pay AI agents for research reports.", accepted_terms=True,
        )
        result = founding50.apply(request)
        self.assertTrue(result["submitted"])
        self.assertEqual("pending", result["status"])
        applications = founding50.application_list()
        self.assertEqual(1, len(applications))
        self.assertEqual(wallet.address.lower(), applications[0]["wallet"])

    def test_signature_from_another_wallet_is_rejected(self):
        applicant, stranger = Account.create(), Account.create()
        challenge = founding50.challenge(founding50.WalletRequest(wallet=applicant.address))
        signature = Account.sign_message(
            encode_defunct(text=challenge["message"]), stranger.key
        ).signature.hex()
        request = founding50.ApplicationRequest(
            wallet=applicant.address, nonce=challenge["nonce"], signature=signature,
            use_case="Pay AI agents for research reports.", accepted_terms=True,
        )
        with self.assertRaises(Exception) as caught:
            founding50.apply(request)
        self.assertEqual(403, caught.exception.status_code)


if __name__ == "__main__":
    unittest.main()
