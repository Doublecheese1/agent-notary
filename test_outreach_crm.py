import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

import outreach_crm


class OutreachCrmTest(unittest.TestCase):
    def setUp(self):
        directory = os.path.join(os.path.dirname(__file__), ".test-tmp")
        os.makedirs(directory, exist_ok=True)
        self.db_path = os.path.join(directory, f"outreach-{id(self)}.sqlite3")
        self.env = patch.dict(os.environ, {"OUTREACH_CRM_DB_PATH": self.db_path}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.db_path + suffix)
            except FileNotFoundError:
                pass

    def payload(self, **changes):
        values = {
            "company_name": "Example Labs",
            "contact_name": "Public Founder",
            "website": "https://example.com",
            "channel_type": "email",
            "channel_value": "hello@example.com",
            "source_url": "https://example.com/contact",
            "segment": "AI marketplace",
            "owner": "research-agent-a",
            "subject": "Try AgentSolis",
        }
        values.update(changes)
        return outreach_crm.LeadCreate(**values)

    def test_draft_is_not_counted_as_sent(self):
        lead = outreach_crm.create_lead(self.payload(), now=1_000)
        report = outreach_crm.crm_summary(now=1_100)
        self.assertEqual(lead["status"], "draft")
        self.assertEqual(report["total_leads"], 1)
        self.assertEqual(report["sent_ever"], 0)
        self.assertIsNone(report["leads"][0]["first_contact_at"])

    def test_sent_reply_follow_up_and_behavior_metrics(self):
        lead = outreach_crm.create_lead(self.payload(next_follow_up_at=1_500), now=1_000)
        outreach_crm.add_event(lead["id"], outreach_crm.EventCreate(
            kind="sent", message_summary="Invited to the demo", next_follow_up_at=1_500
        ), now=1_100)
        outreach_crm.add_event(lead["id"], outreach_crm.EventCreate(
            kind="replied", reply_summary="Asked for an API walkthrough", next_follow_up_at=1_300
        ), now=1_200)
        report = outreach_crm.crm_summary(now=1_400)
        current = report["leads"][0]
        self.assertEqual(report["sent_ever"], 1)
        self.assertEqual(report["replied_ever"], 1)
        self.assertEqual(report["reply_rate"], 100.0)
        self.assertEqual(current["reply_summary"], "Asked for an API walkthrough")
        self.assertEqual(report["follow_ups_due"][0]["id"], lead["id"])
        self.assertEqual(report["recent_events"][0]["kind"], "replied")

    def test_opt_out_cancels_follow_up(self):
        lead = outreach_crm.create_lead(self.payload(next_follow_up_at=1_500), now=1_000)
        result = outreach_crm.add_event(
            lead["id"], outreach_crm.EventCreate(kind="opt_out", reply_summary="Do not contact"), now=1_100
        )
        report = outreach_crm.crm_summary(now=2_000)
        self.assertEqual(result["status"], "opt_out")
        self.assertIsNone(result["next_follow_up_at"])
        self.assertEqual(report["follow_ups_due"], [])

    def test_country_requires_verification(self):
        with self.assertRaises(ValidationError):
            self.payload(country="Canada")
        verified = self.payload(country="Canada", country_verified=True)
        self.assertEqual(verified.country, "Canada")

    def test_wallet_and_deal_require_explicit_relationship(self):
        wallet = "0x" + "11" * 20
        deal_id = "0x" + "22" * 32
        with self.assertRaises(ValidationError):
            self.payload(wallet=wallet)
        lead = outreach_crm.create_lead(self.payload(
            wallet=wallet, deal_id=deal_id, relationship_verified=True
        ), now=1_000)
        self.assertTrue(lead["relationship_verified"])
        self.assertEqual(lead["deal_id"], deal_id)

    def test_follow_up_event_counts_real_contact(self):
        lead = outreach_crm.create_lead(self.payload(), now=1_000)
        result = outreach_crm.add_event(
            lead["id"], outreach_crm.EventCreate(kind="follow_up", message_summary="One follow-up sent"), now=1_100
        )
        report = outreach_crm.crm_summary(now=1_200)
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["follow_up_count"], 1)
        self.assertEqual(report["sent_ever"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
