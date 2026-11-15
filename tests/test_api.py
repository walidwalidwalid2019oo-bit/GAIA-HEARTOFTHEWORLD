from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import backend.main as api_module
from gaia.ai.provider import ProviderError


class FakeAI:
    def __init__(self, answer=None, error=None, ready=True):
        self.answer = answer or {
            "answer": "Hello.",
            "specialist": "GAIA",
            "conversation_id": "conversation-1",
        }
        self.error = error
        self.ready = ready
        self.calls = []
        self.selected_specialists = []

    def status(self):
        return {"provider_configured": self.ready, "memory": "sqlite"}

    def respond(self, message, conversation_id, specialist=None):
        self.calls.append((message, conversation_id))
        self.selected_specialists.append(specialist)
        if self.error:
            raise self.error
        return {**self.answer, "conversation_id": conversation_id}


@pytest.fixture
def api_client(monkeypatch):
    monkeypatch.setenv("GAIA_API_TOKEN", "test-access-token-" + ("x" * 32))
    fake = FakeAI()
    monkeypatch.setattr(api_module, "ai", fake)
    with TestClient(api_module.app) as client:
        yield client, fake


def auth_headers():
    return {"Authorization": "Bearer " + "test-access-token-" + ("x" * 32)}


def test_health_reports_ready_only_when_provider_and_api_auth_are_configured(api_client):
    client, _ = api_client

    result = client.get("/health")

    assert result.status_code == 200
    assert result.json()["status"] == "ready"
    assert result.json()["api_auth_configured"] is True


def test_health_reports_setup_required_without_provider(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setattr(api_module, "ai", FakeAI(ready=False))

    result = client.get("/health")

    assert result.json()["status"] == "setup_required"
    assert result.json()["ai"]["provider_configured"] is False


def test_health_rejects_placeholder_api_token(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setenv("GAIA_API_TOKEN", "put_a_long_random_api_token_here")

    result = client.get("/health")

    assert result.json()["status"] == "setup_required"
    assert result.json()["api_auth_configured"] is False


def test_health_reports_setup_required_without_api_token(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.delenv("GAIA_API_TOKEN")

    result = client.get("/health")

    assert result.json()["status"] == "setup_required"
    assert result.json()["api_auth_configured"] is False


def test_chat_requires_bearer_authentication(api_client):
    client, fake = api_client

    result = client.post("/chat", json={"message": "Hello"})

    assert result.status_code == 401
    assert fake.calls == []


def test_chat_fails_closed_when_api_token_is_not_configured(api_client, monkeypatch):
    client, fake = api_client
    monkeypatch.delenv("GAIA_API_TOKEN")

    result = client.post("/chat", json={"message": "Hello"}, headers=auth_headers())

    assert result.status_code == 503
    assert fake.calls == []


def test_chat_trims_message_and_generates_conversation_id(api_client):
    client, fake = api_client

    result = client.post("/chat", json={"message": "  Hello GAIA  "}, headers=auth_headers())

    assert result.status_code == 200
    assert fake.calls[0][0] == "Hello GAIA"
    UUID(fake.calls[0][1])
    assert result.json()["answer"] == "Hello."


def test_chat_uses_supplied_conversation_id(api_client):
    client, fake = api_client

    result = client.post(
        "/chat",
        json={"message": "Hello", "conversation_id": "phone-session_01"},
        headers=auth_headers(),
    )

    assert result.status_code == 200
    assert fake.calls == [("Hello", "phone-session_01")]
    assert result.json()["conversation_id"] == "phone-session_01"


@pytest.mark.parametrize("conversation_id", ["contains spaces", "../other", "line\nbreak", "💥"])
def test_chat_rejects_unsafe_conversation_ids(api_client, conversation_id):
    client, fake = api_client

    result = client.post(
        "/chat",
        json={"message": "Hello", "conversation_id": conversation_id},
        headers=auth_headers(),
    )

    assert result.status_code == 422
    assert fake.calls == []


def test_chat_rejects_whitespace_only_message(api_client):
    client, fake = api_client

    result = client.post("/chat", json={"message": "   "}, headers=auth_headers())

    assert result.status_code == 422
    assert fake.calls == []


def test_chat_rejects_oversized_message(api_client):
    client, fake = api_client

    result = client.post("/chat", json={"message": "x" * 12001}, headers=auth_headers())

    assert result.status_code == 422
    assert fake.calls == []


def test_chat_rejects_unknown_request_fields(api_client):
    client, fake = api_client

    result = client.post(
        "/chat",
        json={"message": "Hello", "unexpected": "value"},
        headers=auth_headers(),
    )

    assert result.status_code == 422
    assert fake.calls == []


def test_chat_can_select_a_registered_specialist(api_client):
    client, fake = api_client

    result = client.post(
        "/chat",
        json={"message": "Review this system", "specialist": "HADES"},
        headers=auth_headers(),
    )

    assert result.status_code == 200
    assert fake.selected_specialists == ["HADES"]


def test_chat_rejects_unknown_specialist(api_client):
    client, fake = api_client

    result = client.post(
        "/chat",
        json={"message": "Hello", "specialist": "UNKNOWN"},
        headers=auth_headers(),
    )

    assert result.status_code == 422
    assert fake.calls == []


def test_chat_maps_provider_failure_to_service_unavailable(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setattr(api_module, "ai", FakeAI(error=ProviderError("provider not configured")))

    result = client.post("/chat", json={"message": "Hello"}, headers=auth_headers())

    assert result.status_code == 503
    assert result.json()["detail"] == "provider not configured"
