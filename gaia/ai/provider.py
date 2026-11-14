"""Minimal OpenAI-compatible chat-completions client.

Credentials are read from the backend environment, never from source code.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("GAIA_API_KEY", "").strip()
        self.base_url = os.getenv("GAIA_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        self.model = os.getenv("GAIA_MODEL", "").strip()
        self.timeout = int(os.getenv("GAIA_TIMEOUT_SECONDS", "60"))

    def ready(self) -> bool:
        return bool(self.api_key and self.model)

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ProviderError("GAIA_API_KEY is not configured on the backend.")
        if not self.model:
            raise ProviderError("GAIA_MODEL is not configured on the backend.")

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
        }).encode("utf-8")
        request = Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderError(f"AI provider returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Could not reach or read the AI provider: {exc}") from exc

        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError, TypeError) as exc:
            raise ProviderError("The provider response did not contain a chat completion.") from exc
