import tempfile
import unittest
from pathlib import Path

from core.memory import MemoryStore
from core.permissions import PermissionLevel, classify_request
from core.runtime import choose_backend


class CoreTests(unittest.TestCase):
    def test_critical_permission(self):
        result = classify_request("می‌خواهم پرداخت انجام بدهی")
        self.assertEqual(result.level, PermissionLevel.CRITICAL)
        self.assertTrue(result.requires_approval)

    def test_approval_permission(self):
        result = classify_request("یک پیام ارسال کن")
        self.assertEqual(result.level, PermissionLevel.APPROVAL)
        self.assertTrue(result.requires_approval)

    def test_safe_permission(self):
        result = classify_request("امروز چه برنامه‌ای دارم؟")
        self.assertEqual(result.level, PermissionLevel.SAFE)
        self.assertFalse(result.requires_approval)

    def test_memory_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "memory.db"
            memory = MemoryStore(str(db_path))
            memory_id = memory.add_memory("من در حال ساخت ARIA هستم", kind="goal")
            self.assertGreater(memory_id, 0)

            results = memory.search("ARIA")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["kind"], "goal")

    def test_local_fallback_selector(self):
        local = "http://127.0.0.1:8765"
        chosen = choose_backend("https://cloud.example", local, timeout=0.01)
        self.assertIn(chosen, {"https://cloud.example", local})


if __name__ == "__main__":
    unittest.main()
