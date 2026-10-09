import unittest
from unittest.mock import Mock, patch

from core.huggingface_backend import (
    HuggingFaceConfigurationError,
    chat_completion,
)


class HuggingFaceBackendTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_token_fails_without_network(self):
        with patch("core.huggingface_backend.requests.post") as post:
            with self.assertRaises(HuggingFaceConfigurationError):
                chat_completion([{"role": "user", "content": "سلام"}])
            post.assert_not_called()

    @patch.dict("os.environ", {"HF_TOKEN": "test-token"}, clear=True)
    def test_missing_model_fails_without_network(self):
        with patch("core.huggingface_backend.requests.post") as post:
            with self.assertRaises(HuggingFaceConfigurationError):
                chat_completion([{"role": "user", "content": "سلام"}])
            post.assert_not_called()

    @patch.dict(
        "os.environ",
        {"HF_TOKEN": "test-token", "HF_MODEL": "example/model"},
        clear=True,
    )
    @patch("core.huggingface_backend.requests.post")
    def test_parses_chat_response(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "سلام، ARIA آماده است."}}]
        }
        post.return_value = response

        result = chat_completion([{"role": "user", "content": "سلام"}])

        self.assertEqual(result, "سلام، ARIA آماده است.")
        response.raise_for_status.assert_called_once()
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-token",
        )


if __name__ == "__main__":
    unittest.main()
