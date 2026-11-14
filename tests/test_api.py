from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException

import backend.main as api_module
from backend.main import ChatRequest
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

    def status(self):
        return {"provider_configured": self.ready, "memory": "sqlite"}

    def respond(self, message, conversation_id):
        self.calls.append((message, conversation_id))
        if self.error:
            raise self.error
        return {**self.answer, "conversation_id": conversation_id}


def test_health_reports_setup_required_without_provider(monkeypatch):
    monkeypatch.setattr(api_module, "ai", FakeAI(ready=False))

    result = api_module.health()

    assert result["status"] == "setup_required"
    assert result["ai"]["provider_configured"] is False


def test_health_reports_ready_when_provider_is_configured(monkeypatch):
    monkeypatch.setattr(api_module, "ai", FakeAI(ready=True))

    assert api_module.health()["status"] == "ready"


def test_chat_trims_message_and_generates_conversation_id(monkeypatch):
    fake = FakeAI()
    monkeypatch.setattr(api_module, "ai", fake)

    result = api_module.chat(ChatRequest(message="  Hello GAIA  "))

    assert fake.calls[0][0] == "Hello GAIA"
    UUID(fake.calls[0][1])
    assert result["answer"] == "Hello."


def test_chat_rejects_whitespace_only_message(monkeypatch):
    fake = FakeAI()
    monkeypatch.setattr(api_module, "ai", fake)

    with pytest.raises(HTTPException) as caught:
        api_module.chat(ChatRequest(message="   "))

    assert caught.value.status_code == 422
    assert fake.calls == []


def test_chat_maps_provider_failure_to_service_unavailable(monkeypatch):
    monkeypatch.setattr(api_module, "ai", FakeAI(error=ProviderError("not configured")))

    with pytest.raises(HTTPException) as caught:
        api_module.chat(ChatRequest(message="Hello"))

    assert caught.value.status_code == 503
