from __future__ import annotations

from gaia.ai.memory import ConversationMemory


def test_memory_persists_across_instances(tmp_path):
    database = tmp_path / "gaia.sqlite3"
    first = ConversationMemory(database)
    first.add("session-a", "user", "Hello")
    first.add("session-a", "assistant", "Welcome back")

    reopened = ConversationMemory(database)

    assert reopened.recent("session-a") == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Welcome back"},
    ]


def test_memory_keeps_conversations_isolated(tmp_path):
    memory = ConversationMemory(tmp_path / "gaia.sqlite3")
    memory.add("session-a", "user", "A")
    memory.add("session-b", "user", "B")

    assert memory.recent("session-a") == [{"role": "user", "content": "A"}]
    assert memory.recent("session-b") == [{"role": "user", "content": "B"}]


def test_recent_memory_returns_newest_limit_in_chronological_order(tmp_path):
    memory = ConversationMemory(tmp_path / "gaia.sqlite3")
    for index in range(5):
        memory.add("session-a", "user", f"message-{index}")

    assert memory.recent("session-a", limit=2) == [
        {"role": "user", "content": "message-3"},
        {"role": "user", "content": "message-4"},
    ]


def test_memory_uses_parameterized_values_for_conversation_ids(tmp_path):
    memory = ConversationMemory(tmp_path / "gaia.sqlite3")
    unusual_id = "session'; DROP TABLE messages; --"
    memory.add(unusual_id, "user", "still safe")

    assert memory.recent(unusual_id) == [{"role": "user", "content": "still safe"}]
    assert memory.recent("another-session") == []
