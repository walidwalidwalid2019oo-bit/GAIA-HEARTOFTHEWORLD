"""Minimal OpenAI-compatible chat-completions client.

Credentials are read from the backend environment, never from source code.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """Safe, user-facing provider configuration or request error."""


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("GAIA_API_KEY", "").strip()
        self.base_url = os.getenv(
            "GAIA_BASE_URL", "https://api.groq.com/openai/v1"
        ).strip().rstrip("/")
        self.model = os.getenv("GAIA_MODEL", "").strip()
        try:
            configured_timeout = int(os.getenv("GAIA_TIMEOUT_SECONDS", "60"))
        except ValueError:
            configured_timeout = 60
        self.timeout = min(max(configured_timeout, 5), 180)

    def ready(self) -> bool:
        return bool(self.api_key and self.model)

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ProviderError("GAIA_API_KEY is not configured on the backend.")
        if not self.model:
            raise ProviderError("GAIA_MODEL is not configured on the backend.")
        if not self.base_url.startswith(("https://", "http://")):
            raise ProviderError("GAIA_BASE_URL must be an HTTP or HTTPS URL.")

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
            # Provider bodies can contain request metadata; don't echo them to clients.
            raise ProviderError(
                f"AI provider returned HTTP {exc.code}. Check backend provider settings."
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(
                "Could not reach or read the AI provider. Check the backend URL and network."
            ) from exc

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "The provider response did not contain a chat completion."
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("The provider returned an empty chat completion.")
        return content.strip()
