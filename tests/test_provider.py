from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from gaia.ai.provider import OpenAICompatibleProvider, ProviderError


def configured_provider(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.setenv("GAIA_MODEL", "test-model")
    monkeypatch.setenv("GAIA_BASE_URL", "https://provider.example/v1")
    return OpenAICompatibleProvider()


def test_provider_sends_chat_request_and_extracts_answer(monkeypatch):
    provider = configured_provider(monkeypatch)
    response = BytesIO(json.dumps({
        "choices": [{"message": {"content": "  Hello from GAIA.  "}}]
    }).encode())

    with patch("gaia.ai.provider.urlopen", return_value=response) as mocked:
        answer = provider.chat([{"role": "user", "content": "Hello"}])

    assert answer == "Hello from GAIA."
    request = mocked.call_args.args[0]
    assert request.full_url == "https://provider.example/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-secret"
    assert json.loads(request.data)["model"] == "test-model"


def test_provider_requires_backend_key(monkeypatch):
    monkeypatch.delenv("GAIA_API_KEY", raising=False)
    monkeypatch.setenv("GAIA_MODEL", "test-model")

    with pytest.raises(ProviderError, match="GAIA_API_KEY"):
        OpenAICompatibleProvider().chat([])


def test_provider_requires_model(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.delenv("GAIA_MODEL", raising=False)

    with pytest.raises(ProviderError, match="GAIA_MODEL"):
        OpenAICompatibleProvider().chat([])


def test_provider_does_not_return_raw_http_error_body(monkeypatch):
    provider = configured_provider(monkeypatch)
    error = HTTPError(
        "https://provider.example/v1/chat/completions",
        401,
        "Unauthorized",
        hdrs=None,
        fp=BytesIO(b'{"error":"private provider detail"}'),
    )

    with patch("gaia.ai.provider.urlopen", side_effect=error):
        with pytest.raises(ProviderError) as caught:
            provider.chat([])

    assert "401" in str(caught.value)
    assert "private provider detail" not in str(caught.value)


def test_provider_clamps_timeout_and_rejects_non_http_url(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.setenv("GAIA_MODEL", "test-model")
    monkeypatch.setenv("GAIA_TIMEOUT_SECONDS", "999")
    monkeypatch.setenv("GAIA_BASE_URL", "file:///tmp/provider")

    provider = OpenAICompatibleProvider()
    assert provider.timeout == 180
    with pytest.raises(ProviderError, match="HTTP or HTTPS"):
        provider.chat([])
