from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import backend.main as api_module
from gaia.ai.memory import ConversationMemory
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
        self.owners = []
        self.memory = None

    def status(self):
        return {"provider_configured": self.ready, "memory": "sqlite"}

    def respond(self, message, conversation_id, specialist=None, *, owner_id="local"):
        self.calls.append((message, conversation_id))
        self.selected_specialists.append(specialist)
        self.owners.append(owner_id)
        if self.error:
            raise self.error
        return {**self.answer, "conversation_id": conversation_id}


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    monkeypatch.setenv("GAIA_API_TOKEN", "test-access-token-" + ("x" * 32))
    fake = FakeAI()
    fake.memory = ConversationMemory(tmp_path / "gaia-test.sqlite3")
    monkeypatch.setattr(api_module, "ai", fake)
    with TestClient(api_module.app) as client:
        yield client, fake


def auth_headers():
    return {"Authorization": "Bearer " + "test-access-token-" + ("x" * 32)}


def test_liveness_is_available_without_provider_or_api_credentials(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.delenv("GAIA_API_TOKEN")
    monkeypatch.setattr(api_module, "ai", FakeAI(ready=False))

    result = client.get("/health/live")

    assert result.status_code == 200
    assert result.json() == {"service": "GAIA", "status": "alive"}


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
    assert fake.owners == ["shared-token-owner"]


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


def test_memory_routes_require_authentication(api_client):
    client, fake = api_client
    fake.memory.add("session-a", "user", "Private message", owner_id="shared-token-owner")

    result = client.get("/conversations")

    assert result.status_code == 401
    assert client.get("/conversations", headers=auth_headers()).status_code == 200


def test_list_and_read_conversations(api_client):
    client, fake = api_client
    fake.memory.add("session-a", "user", "Hello", owner_id="shared-token-owner")
    fake.memory.add("session-a", "assistant", "Welcome", owner_id="shared-token-owner")
    fake.memory.add("session-b", "user", "Another chat", owner_id="shared-token-owner")

    listing = client.get("/conversations?limit=1", headers=auth_headers())
    detail = client.get("/conversations/session-a", headers=auth_headers())

    assert listing.status_code == 200
    assert len(listing.json()["conversations"]) == 1
    assert listing.json()["conversations"][0]["conversation_id"] == "session-b"
    assert detail.status_code == 200
    assert [item["content"] for item in detail.json()["messages"]] == ["Hello", "Welcome"]


def test_read_conversation_returns_not_found_for_unknown_id(api_client):
    client, _ = api_client

    result = client.get("/conversations/missing", headers=auth_headers())

    assert result.status_code == 404


def test_delete_conversation_removes_only_the_selected_history(api_client):
    client, fake = api_client
    fake.memory.add("session-a", "user", "Remove this", owner_id="shared-token-owner")
    fake.memory.add("session-b", "user", "Keep this", owner_id="shared-token-owner")

    result = client.delete("/conversations/session-a", headers=auth_headers())

    assert result.status_code == 200
    assert result.json()["deleted"] is True
    assert fake.memory.get_conversation("session-a", owner_id="shared-token-owner") == []
    assert fake.memory.get_conversation("session-b", owner_id="shared-token-owner")[0]["content"] == "Keep this"


def test_memory_routes_reject_unsafe_conversation_ids(api_client):
    client, _ = api_client

    result = client.delete("/conversations/bad%20id", headers=auth_headers())

    assert result.status_code == 422


def test_conversation_history_isolated_between_owners(tmp_path):
    memory = ConversationMemory(tmp_path / "owner-isolation.sqlite3")
    memory.add("same-id", "user", "Owner A secret", owner_id="owner-a")
    memory.add("same-id", "user", "Owner B secret", owner_id="owner-b")

    assert memory.get_conversation("same-id", owner_id="owner-a")[0]["content"] == "Owner A secret"
    assert memory.get_conversation("same-id", owner_id="owner-b")[0]["content"] == "Owner B secret"
    assert memory.conversations(owner_id="owner-a")[0]["conversation_id"] == "same-id"
    assert memory.delete_conversation("same-id", owner_id="owner-a") is True
    assert memory.get_conversation("same-id", owner_id="owner-a") == []
    assert memory.get_conversation("same-id", owner_id="owner-b")[0]["content"] == "Owner B secret"


def test_legacy_conversation_rows_are_unowned_and_hidden(tmp_path):
    from sqlalchemy import text
    from gaia.storage import create_database_engine

    engine = create_database_engine(tmp_path / "legacy.sqlite3")
    with engine.begin() as db:
        db.execute(text("""CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id VARCHAR(100) NOT NULL,
            role VARCHAR(9) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""))
        db.execute(text("INSERT INTO messages(conversation_id, role, content) VALUES "
                        "('old-chat', 'user', 'Legacy private content')"))
    memory = ConversationMemory(engine=engine)
    assert memory.get_conversation("old-chat", owner_id="new-owner") == []
    assert memory.conversations(owner_id="new-owner") == []
    engine.dispose()
