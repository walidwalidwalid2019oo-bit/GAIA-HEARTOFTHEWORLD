from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError, URLError
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


def test_provider_rejects_example_placeholder_values(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "put_your_provider_key_here")
    monkeypatch.setenv("GAIA_MODEL", "put_a_model_id_here")

    provider = OpenAICompatibleProvider()

    assert provider.ready() is False
    with pytest.raises(ProviderError, match="GAIA_API_KEY"):
        provider.chat([])


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


def test_provider_requires_https_for_remote_hosts(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.setenv("GAIA_MODEL", "test-model")
    monkeypatch.setenv("GAIA_BASE_URL", "http://provider.example/v1")

    provider = OpenAICompatibleProvider()

    assert provider.ready() is False
    with pytest.raises(ProviderError, match="HTTPS"):
        provider.chat([])


def test_provider_allows_http_for_local_development(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.setenv("GAIA_MODEL", "test-model")
    monkeypatch.setenv("GAIA_BASE_URL", "http://127.0.0.1:9000/v1")

    assert OpenAICompatibleProvider().ready() is True


def test_provider_rejects_embedded_credentials_and_query_strings(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.setenv("GAIA_MODEL", "test-model")
    monkeypatch.setenv("GAIA_BASE_URL", "https://user:pass@provider.example/v1?key=hidden")

    provider = OpenAICompatibleProvider()

    assert provider.ready() is False
    with pytest.raises(ProviderError, match="embedded credentials"):
        provider.chat([])


def test_provider_clamps_timeout_and_rejects_invalid_url(monkeypatch):
    monkeypatch.setenv("GAIA_API_KEY", "test-secret")
    monkeypatch.setenv("GAIA_MODEL", "test-model")
    monkeypatch.setenv("GAIA_TIMEOUT_SECONDS", "999")
    monkeypatch.setenv("GAIA_BASE_URL", "file:///tmp/provider")

    provider = OpenAICompatibleProvider()
    assert provider.timeout == 180
    assert provider.ready() is False
    with pytest.raises(ProviderError, match="absolute HTTP or HTTPS"):
        provider.chat([])


def test_provider_handles_malformed_response_shape(monkeypatch):
    provider = configured_provider(monkeypatch)
    response = BytesIO(json.dumps({"choices": []}).encode())

    with patch("gaia.ai.provider.urlopen", return_value=response):
        with pytest.raises(ProviderError, match="did not contain"):
            provider.chat([])


def test_provider_handles_network_failure_without_leaking_details(monkeypatch):
    provider = configured_provider(monkeypatch)

    with patch("gaia.ai.provider.urlopen", side_effect=URLError("private network detail")):
        with pytest.raises(ProviderError) as caught:
            provider.chat([])

    assert "private network detail" not in str(caught.value)
