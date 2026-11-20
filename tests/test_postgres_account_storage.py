"""PostgreSQL integration coverage for accounts and owner-scoped personal data.

The CI workflow supplies a disposable PostgreSQL service. Local runs skip this
module unless GAIA_POSTGRES_TEST_URL points to a dedicated test database.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text

from gaia.ai.memory import ConversationMemory
from gaia.assistant.auth import UserAuth
from gaia.assistant.memory import LongTermMemory
from gaia.storage import create_database_engine


POSTGRES_URL = os.getenv("GAIA_POSTGRES_TEST_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="Set GAIA_POSTGRES_TEST_URL to run PostgreSQL integration tests.",
)


def test_postgres_accounts_sessions_and_private_records_are_shared_and_isolated(monkeypatch):
    """Two independently-created engines see durable rows without crossing owners."""
    monkeypatch.setenv("GAIA_DATABASE_URL", POSTGRES_URL)
    first_engine = create_database_engine()
    second_engine = create_database_engine()

    suffix = uuid4().hex
    email_a = f"gaia-a-{suffix}@example.test"
    email_b = f"gaia-b-{suffix}@example.test"
    conversation_id = f"pg-isolation-{suffix}"
    password = "integration-test-password-only"

    try:
        # Repeated initialization must be safe when separate workers start.
        auth_a = UserAuth(engine=first_engine)
        auth_b = UserAuth(engine=second_engine)
        conversations_a = ConversationMemory(engine=first_engine)
        conversations_b = ConversationMemory(engine=second_engine)
        facts_a = LongTermMemory(engine=first_engine)
        facts_b = LongTermMemory(engine=second_engine)

        account_a = auth_a.create_user(email_a, password)
        account_b = auth_a.create_user(email_b, password)
        session_a = auth_a.issue_session(account_a["user_id"])

        # A different engine/worker can resolve and revoke the opaque session.
        assert auth_b.verify_credentials(email_a, password)["user_id"] == account_a["user_id"]
        assert auth_b.resolve_session(session_a["access_token"]) == account_a["user_id"]

        owner_a, owner_b = account_a["user_id"], account_b["user_id"]
        conversations_a.add(conversation_id, "user", "private to account A", owner_id=owner_a)
        conversations_b.add(conversation_id, "user", "private to account B", owner_id=owner_b)

        # A legacy NULL-owner row must remain hidden from both accounts.
        with first_engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO messages(conversation_id, role, content, owner_id) "
                    "VALUES (:cid, 'user', 'legacy unassigned record', NULL)"
                ),
                {"cid": conversation_id},
            )

        history_a = conversations_b.get_conversation(conversation_id, owner_id=owner_a)
        history_b = conversations_a.get_conversation(conversation_id, owner_id=owner_b)
        assert [row["content"] for row in history_a] == ["private to account A"]
        assert [row["content"] for row in history_b] == ["private to account B"]
        assert conversations_b.delete_conversation(conversation_id, owner_id=owner_b) is True
        assert [row["content"] for row in conversations_a.get_conversation(
            conversation_id, owner_id=owner_a
        )] == ["private to account A"]

        fact_a = facts_a.add("projects", f"private fact A {suffix}", owner_id=owner_a)
        fact_b = facts_b.add("projects", f"private fact B {suffix}", owner_id=owner_b)
        assert [row["fact_id"] for row in facts_b.list(owner_id=owner_a)] == [fact_a["fact_id"]]
        assert [row["fact_id"] for row in facts_a.list(owner_id=owner_b)] == [fact_b["fact_id"]]
        assert facts_b.delete(fact_a["fact_id"], owner_id=owner_b) is False
        assert facts_a.list(owner_id=owner_a)[0]["fact_id"] == fact_a["fact_id"]

        assert auth_b.revoke_session(session_a["access_token"]) is True
        assert auth_a.resolve_session(session_a["access_token"]) is None
    finally:
        first_engine.dispose()
        second_engine.dispose()
