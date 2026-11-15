"""Small SQLite store for GAIA conversation history."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("GAIA_DB_PATH", "data/gaia.sqlite3"))


class ConversationMemory:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")

    def _connect(self):
        return sqlite3.connect(str(self.path))

    def add(self, conversation_id: str, role: str, content: str) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )

    def recent(self, conversation_id: str, limit: int = 16) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def conversations(self, limit: int = 50) -> list[dict[str, object]]:
        """Return recent conversation summaries without loading full histories."""
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT m.conversation_id, COUNT(*) AS message_count,
                       MAX(m.created_at) AS updated_at,
                       (SELECT latest.content FROM messages AS latest
                        WHERE latest.conversation_id = m.conversation_id
                        ORDER BY latest.id DESC LIMIT 1) AS last_message
                FROM messages AS m
                GROUP BY m.conversation_id
                ORDER BY MAX(m.id) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "conversation_id": conversation_id,
                "message_count": message_count,
                "updated_at": updated_at,
                "last_message": last_message,
            }
            for conversation_id, message_count, updated_at, last_message in rows
        ]

    def get_conversation(self, conversation_id: str) -> list[dict[str, str]]:
        """Return a complete conversation in chronological order."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE conversation_id=? ORDER BY id ASC",
                (conversation_id,),
            ).fetchall()
        return [
            {"role": role, "content": content, "created_at": created_at}
            for role, content, created_at in rows
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete one conversation and report whether any messages existed."""
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM messages WHERE conversation_id=?",
                (conversation_id,),
            )
            return cursor.rowcount > 0
