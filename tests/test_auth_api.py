from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.main as api_module
from gaia.ai.memory import ConversationMemory
from gaia.assistant.auth import UserAuth
from gaia.assistant.memory import LongTermMemory


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
