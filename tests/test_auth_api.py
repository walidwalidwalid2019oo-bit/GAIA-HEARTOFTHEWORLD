from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.main as api_module
from gaia.ai.memory import ConversationMemory
from gaia.assistant.auth import UserAuth
from gaia.assistant.memory import LongTermMemory
from gaia.assistant.rate_limit import PersistentRateLimiter


class FakeAI:
    def __init__(self, memory):
        self.memory = memory
    def status(self):
        return {"provider_configured": True, "memory": "test"}
    def respond(self, message, conversation_id, specialist=None, *, owner_id="local"):
        self.memory.add(conversation_id, "user", message, owner_id=owner_id)
        return {"answer": "Test response", "specialist": specialist or "GAIA",
                "conversation_id": conversation_id}


@pytest.fixture
def client(monkeypatch, tmp_path):
    memory = ConversationMemory(tmp_path / "auth-api.sqlite3")
    fake = FakeAI(memory)
    monkeypatch.setattr(api_module, "ai", fake)
    monkeypatch.setattr(api_module, "user_auth", UserAuth(engine=memory.engine))
    monkeypatch.setattr(api_module, "long_term_memory", LongTermMemory(engine=memory.engine))
    monkeypatch.setenv("GAIA_RATE_LIMIT_SECRET", "test-rate-limit-secret-" + ("x" * 32))
    monkeypatch.setattr(api_module, "rate_limiter", PersistentRateLimiter(engine=memory.engine))
    monkeypatch.setenv("GAIA_ALLOW_SHARED_TOKEN", "false")
    with TestClient(api_module.app) as test_client:
        yield test_client


def register(client, email):
    response = client.post("/auth/register", json={
        "email": email, "password": "correct-horse-battery"
    })
    assert response.status_code == 200
    return response.json()


def headers(session):
    return {"Authorization": "Bearer " + session["access_token"]}


def test_register_login_me_and_logout(client):
    created = register(client, "pilot@example.com")
    token_headers = headers(created["session"])

    current = client.get("/auth/me", headers=token_headers)
    assert current.status_code == 200
    assert current.json()["account"]["email"] == "pilot@example.com"

    logged_out = client.post("/auth/logout", headers=token_headers)
    assert logged_out.status_code == 200
    assert client.get("/auth/me", headers=token_headers).status_code == 401

    login = client.post("/auth/login", json={
        "email": "PILOT@example.com", "password": "correct-horse-battery"
    })
    assert login.status_code == 200
    assert client.get("/auth/me", headers=headers(login.json()["session"])).status_code == 200


def test_accounts_cannot_read_each_others_memory(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")

    saved = client.post("/memory/facts", headers=headers(a["session"]), json={
        "category": "projects", "content": "Private GAIA project note"
    })
    assert saved.status_code == 200

    a_facts = client.get("/memory/facts", headers=headers(a["session"]))
    b_facts = client.get("/memory/facts", headers=headers(b["session"]))
    assert len(a_facts.json()["facts"]) == 1
    assert b_facts.json()["facts"] == []

    fact_id = a_facts.json()["facts"][0]["fact_id"]
    foreign_delete = client.request("DELETE", f"/memory/facts/{fact_id}",
                                    headers=headers(b["session"]), json={"confirm": True})
    assert foreign_delete.status_code == 404


def test_shared_development_token_is_disabled_by_default(client, monkeypatch):
    monkeypatch.setenv("GAIA_API_TOKEN", "x" * 48)
    monkeypatch.setenv("GAIA_ALLOW_SHARED_TOKEN", "false")
    response = client.get("/conversations", headers={"Authorization": "Bearer " + "x" * 48})
    assert response.status_code == 401


def test_registration_rejects_short_password(client):
    response = client.post("/auth/register", json={
        "email": "short@example.com", "password": "tiny"
    })
    assert response.status_code == 400


def test_accounts_cannot_read_each_others_conversation_history(client):
    a = register(client, "chat-a@example.com")
    b = register(client, "chat-b@example.com")
    conversation_id = "same-conversation-id"

    first = client.post("/chat", headers=headers(a["session"]), json={
        "message": "Private message from A", "conversation_id": conversation_id
    })
    second = client.post("/chat", headers=headers(b["session"]), json={
        "message": "Private message from B", "conversation_id": conversation_id
    })
    assert first.status_code == 200
    assert second.status_code == 200

    a_history = client.get(f"/conversations/{conversation_id}", headers=headers(a["session"]))
    b_history = client.get(f"/conversations/{conversation_id}", headers=headers(b["session"]))
    assert [m["content"] for m in a_history.json()["messages"]] == ["Private message from A"]
    assert [m["content"] for m in b_history.json()["messages"]] == ["Private message from B"]



def test_registration_is_globally_rate_limited(client, monkeypatch):
    monkeypatch.setattr(api_module, "AUTH_REGISTER_GLOBAL_LIMIT", 1)
    first = client.post("/auth/register", json={
        "email": "first@example.com", "password": "correct-horse-battery"
    })
    blocked = client.post("/auth/register", json={
        "email": "second@example.com", "password": "correct-horse-battery"
    })
    assert first.status_code == 200
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_login_is_rate_limited_per_email(client, monkeypatch):
    register(client, "limited@example.com")
    monkeypatch.setattr(api_module, "AUTH_LOGIN_EMAIL_LIMIT", 1)
    payload = {"email": "limited@example.com", "password": "correct-horse-battery"}

    first = client.post("/auth/login", json=payload)
    blocked = client.post("/auth/login", json=payload)

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many requests. Try again later."


def test_chat_is_rate_limited_per_account(client, monkeypatch):
    account_a = register(client, "chat-limit-a@example.com")
    account_b = register(client, "chat-limit-b@example.com")
    monkeypatch.setattr(api_module, "CHAT_ACCOUNT_MINUTE_LIMIT", 1)

    first = client.post("/chat", headers=headers(account_a["session"]), json={"message": "A1"})
    blocked = client.post("/chat", headers=headers(account_a["session"]), json={"message": "A2"})
    other_account = client.post("/chat", headers=headers(account_b["session"]), json={"message": "B1"})

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert other_account.status_code == 200


def test_account_routes_fail_closed_without_rate_limit_secret(client, monkeypatch):
    monkeypatch.delenv("GAIA_RATE_LIMIT_SECRET")
    response = client.post("/auth/register", json={
        "email": "no-secret@example.com", "password": "correct-horse-battery"
    })
    assert response.status_code == 503
    assert response.json()["detail"] == "Server rate limiting is not configured."


def test_invalid_blank_email_is_rejected_without_bypassing_rate_limiter(client):
    response = client.post("/auth/register", json={
        "email": "   ", "password": "correct-horse-battery"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Enter a valid email address."


def test_invalid_blank_login_email_returns_generic_auth_failure(client):
    response = client.post("/auth/login", json={
        "email": "   ", "password": "correct-horse-battery"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect."
