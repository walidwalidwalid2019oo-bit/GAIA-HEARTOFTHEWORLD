from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.main as api_module
from gaia.assistant.memory import LongTermMemory


@pytest.fixture
def client_with_memory(monkeypatch, tmp_path):
    token = "gaia-test-token-" + ("x" * 32)
    monkeypatch.setenv("GAIA_API_TOKEN", token)
    monkeypatch.setattr(
        api_module, "long_term_memory",
        LongTermMemory(tmp_path / "assistant-api.sqlite3"),
    )
    with TestClient(api_module.app) as client:
        yield client, {"Authorization": "Bearer " + token}


def test_memory_fact_routes_require_authentication(client_with_memory):
    client, _ = client_with_memory
    assert client.get("/memory/facts").status_code == 401
    assert client.post(
        "/memory/facts",
        json={"category": "general", "content": "A note"},
    ).status_code == 401


def test_memory_fact_can_be_saved_and_listed(client_with_memory):
    client, headers = client_with_memory
    created = client.post(
        "/memory/facts",
        json={"category": "projects", "content": "GAIA has a separate long-term memory layer."},
        headers=headers,
    )

    assert created.status_code == 200
    assert created.json()["saved"] is True
    fact_id = created.json()["fact"]["fact_id"]

    # A fact belonging to a different owner must not appear in this API session.
    api_module.long_term_memory.add(
        "projects", "Private to another account", owner_id="another-account"
    )
    listing = client.get("/memory/facts?category=projects", headers=headers)
    assert listing.status_code == 200
    assert [fact["fact_id"] for fact in listing.json()["facts"]] == [fact_id]


def test_memory_fact_delete_requires_explicit_confirmation(client_with_memory):
    client, headers = client_with_memory
    created = client.post(
        "/memory/facts",
        json={"content": "A removable note"},
        headers=headers,
    )
    fact_id = created.json()["fact"]["fact_id"]

    denied = client.request(
        "DELETE", f"/memory/facts/{fact_id}",
        json={"confirm": False}, headers=headers,
    )
    assert denied.status_code == 400
    assert client.get("/memory/facts", headers=headers).json()["facts"]

    deleted = client.request(
        "DELETE", f"/memory/facts/{fact_id}",
        json={"confirm": True}, headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert client.get("/memory/facts", headers=headers).json()["facts"] == []


def test_memory_fact_api_rejects_credential_like_content(client_with_memory):
    client, headers = client_with_memory
    result = client.post(
        "/memory/facts",
        json={"content": "password: do-not-store-this"},
        headers=headers,
    )
    assert result.status_code == 422



def test_memory_fact_cannot_be_deleted_by_another_owner(client_with_memory):
    client, headers = client_with_memory
    foreign = api_module.long_term_memory.add(
        "private", "Belongs to another account", owner_id="another-account"
    )
    result = client.request(
        "DELETE", f"/memory/facts/{foreign['fact_id']}",
        json={"confirm": True}, headers=headers,
    )
    assert result.status_code == 404
    assert api_module.long_term_memory.list(owner_id="another-account")[0]["fact_id"] == foreign["fact_id"]
