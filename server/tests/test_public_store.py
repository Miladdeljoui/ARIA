import tempfile
import unittest
from pathlib import Path

from server.public_store import PublicStore


class PublicStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = PublicStore(Path(self.temp.name) / "public.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_user_creation_is_idempotent_by_google_subject(self):
        first, created = self.store.create_user("google-sub-1", "a@example.com", True, "A")
        second, created_again = self.store.create_user("google-sub-1", "b@example.com", True, "A B")
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first, second)

    def test_referral_code_and_self_referral_rejection(self):
        inviter, _ = self.store.create_user("google-sub-inviter")
        invitee, _ = self.store.create_user("google-sub-invitee")
        code = self.store.ensure_referral_code(inviter)
        referral_id = self.store.create_referral(inviter, invitee, code.lower())
        self.assertTrue(referral_id)
        with self.assertRaises(ValueError):
            self.store.create_referral(inviter, inviter, code)

    def test_subscription_expiry_and_idempotent_source_event(self):
        user, _ = self.store.create_user("google-sub-2")
        sub = self.store.grant_subscription(user, "trial", 3 * 86400, "trial",
                                            source_id="trial-for-user", now=1000)
        same = self.store.grant_subscription(user, "trial", 3 * 86400, "trial",
                                             source_id="trial-for-user", now=1000)
        self.assertEqual(sub, same)
        self.assertTrue(self.store.has_active_pro(user, now=1001))
        self.assertFalse(self.store.has_active_pro(user, now=1000 + 3 * 86400))

    def test_owner_role_bypasses_paid_subscription_check(self):
        user, _ = self.store.create_user("google-sub-owner")
        with self.store.connection() as db:
            db.execute("UPDATE public_users SET role='owner' WHERE id=?", (user,))
        self.assertTrue(self.store.has_active_pro(user, now=1000))


if __name__ == "__main__":
    unittest.main()
