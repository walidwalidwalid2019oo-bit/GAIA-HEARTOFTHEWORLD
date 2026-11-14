"""Minimal OpenAI-compatible chat-completions client.

Credentials are read from the backend environment, never from source code.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """Safe, user-facing provider configuration or request error."""


_PLACEHOLDERS = {
    "put_your_provider_key_here",
    "put_a_model_id_here",
    "replace_me",
    "your_api_key_here",
}
_ALLOWED_HTTP_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024


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

    @staticmethod
    def _is_placeholder(value: str) -> bool:
        lowered = value.casefold()
        return lowered in _PLACEHOLDERS or lowered.startswith(("put_", "replace_", "your_"))

    def _base_url_error(self) -> str | None:
        try:
            parsed = urlsplit(self.base_url)
            hostname = (parsed.hostname or "").casefold()
            # Accessing .port validates malformed port values.
            _ = parsed.port
        except ValueError:
            return "GAIA_BASE_URL is not a valid URL."

        if parsed.scheme not in {"https", "http"} or not hostname:
            return "GAIA_BASE_URL must be an absolute HTTP or HTTPS URL."
        if parsed.username is not None or parsed.password is not None:
            return "GAIA_BASE_URL must not contain embedded credentials."
        if parsed.query or parsed.fragment:
            return "GAIA_BASE_URL must not contain a query string or fragment."
        if parsed.scheme == "http" and hostname not in _ALLOWED_HTTP_HOSTS:
            return "GAIA_BASE_URL must use HTTPS except for localhost development."
        return None

    def configuration_error(self) -> str | None:
        if not self.api_key or self._is_placeholder(self.api_key):
            return "GAIA_API_KEY is not configured on the backend."
        if not self.model or self._is_placeholder(self.model):
            return "GAIA_MODEL is not configured on the backend."
        return self._base_url_error()

    def ready(self) -> bool:
        return self.configuration_error() is None

    def chat(self, messages: list[dict[str, str]]) -> str:
        problem = self.configuration_error()
        if problem:
            raise ProviderError(problem)

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
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise ProviderError("The AI provider response was larger than GAIA allows.")
            result = json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            # Provider bodies can contain request metadata; don't echo them to clients.
            raise ProviderError(
                f"AI provider returned HTTP {exc.code}. Check backend provider settings."
            ) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
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
