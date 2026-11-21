import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import billing


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "test.sqlite3")
        self.patch = patch.object(billing, "DB_PATH", self.db)
        self.patch.start()
        billing.init_db()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def payment(self, user_id=101, plan="weekly"):
        return billing.create_payment(user_id, plan, "telegram-file-id")

    def test_plan_limits(self):
        self.assertEqual(billing.PLANS["weekly"]["clips"], 28)
        self.assertEqual(billing.PLANS["weekly"]["daily_limit"], 4)
        self.assertEqual(billing.PLANS["monthly"]["clips"], 140)
        self.assertIsNone(billing.PLANS["monthly"]["daily_limit"])

    def test_duplicate_pending_payment_is_blocked(self):
        self.payment()
        with self.assertRaises(ValueError):
            self.payment()

    def test_approval_is_idempotent(self):
        payment_id = self.payment()
        first = billing.approve_payment(payment_id, 999)
        second = billing.approve_payment(payment_id, 999)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_second_purchase_is_queued_after_first(self):
        first_id = self.payment(user_id=202, plan="weekly")
        first = billing.approve_payment(first_id, 999)
        second_id = self.payment(user_id=202, plan="monthly")
        second = billing.approve_payment(second_id, 999)
        self.assertTrue(second["queued"])
        self.assertEqual(second["starts_at"], first["ends_at"])

    def test_weekly_daily_limit(self):
        payment_id = self.payment(user_id=303, plan="weekly")
        billing.approve_payment(payment_id, 999)
        for _ in range(4):
            reservation = billing.reserve_clip(303)
            self.assertTrue(reservation["ok"])
            self.assertTrue(billing.finish_clip(reservation["job_id"], True))
        blocked = billing.reserve_clip(303)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["reason"], "daily_quota_exhausted")

    def test_failed_clip_refunds_quota(self):
        payment_id = self.payment(user_id=404, plan="weekly")
        billing.approve_payment(payment_id, 999)
        reservation = billing.reserve_clip(404)
        self.assertTrue(reservation["ok"])
        self.assertTrue(billing.finish_clip(reservation["job_id"], False))
        again = billing.reserve_clip(404)
        self.assertTrue(again["ok"])
        self.assertEqual(again["remaining"], 26)

    def test_reject_does_not_create_subscription(self):
        payment_id = self.payment(user_id=505)
        self.assertTrue(billing.reject_payment(payment_id, 999))
        self.assertFalse(billing.reject_payment(payment_id, 999))
        account = billing.get_account(505)
        self.assertIsNone(account["active"])
        self.assertEqual(len(account["queued"]), 0)


if __name__ == "__main__":
    unittest.main()
