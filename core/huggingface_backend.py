"""Optional Hugging Face Inference Providers adapter.

This module is not selected automatically. Configure HF_TOKEN and HF_MODEL
locally, then call chat_completion explicitly. Never commit tokens.
"""
import os
from typing import Any

import requests

HF_CHAT_COMPLETIONS_URL = "https://router.huggingface.co/v1/chat/completions"


class HuggingFaceConfigurationError(RuntimeError):
    """Raised when Hugging Face credentials or model configuration is missing."""


def chat_completion(
    messages: list[dict[str, Any]],
    *,
    timeout: float = 30.0,
) -> str:
    """Send chat messages to a configured Hugging Face Inference Provider.

    Remote providers receive the supplied message content. Call this function
    only when remote inference is permitted and the user expects cloud processing.
    """
    token = os.getenv("HF_TOKEN", "").strip()
    model = os.getenv("HF_MODEL", "").strip()
    if not token:
        raise HuggingFaceConfigurationError(
            "HF_TOKEN is not configured; local ARIA mode remains available."
        )
    if not model:
        raise HuggingFaceConfigurationError(
            "HF_MODEL is not configured; choose a supported model explicitly."
        )
    if not messages:
        raise ValueError("messages must contain at least one message")

    response = requests.post(
        HF_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected Hugging Face chat-completion response") from exc

    if not isinstance(content, str):
        raise RuntimeError("Hugging Face returned a non-text chat response")
    return content
