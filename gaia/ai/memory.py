"""Persistent conversation history backed by SQLite or PostgreSQL."""
from __future__ import annotations
from pathlib import Path
from sqlalchemy import Engine, text
from gaia.storage import create_database_engine

DB_PATH = Path("data/gaia.sqlite3")

class ConversationMemory:
    def __init__(self, path: Path | None = None, *, engine: Engine | None = None) -> None:
        self.engine = engine or create_database_engine(path)
        identity = "BIGSERIAL PRIMARY KEY" if self.engine.dialect.name == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        with self.engine.begin() as db:
            db.execute(text(f"""CREATE TABLE IF NOT EXISTS messages (
                id {identity},
                conversation_id VARCHAR(100) NOT NULL,
                role VARCHAR(9) NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)"))

    def add(self, conversation_id: str, role: str, content: str) -> None:
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO messages(conversation_id, role, content) VALUES (:cid, :role, :content)"),
                       {"cid": conversation_id, "role": role, "content": content})

    def recent(self, conversation_id: str, limit: int = 16) -> list[dict[str, str]]:
        with self.engine.connect() as db:
            rows = db.execute(text("SELECT role, content FROM messages WHERE conversation_id=:cid ORDER BY id DESC LIMIT :limit"),
                              {"cid": conversation_id, "limit": limit}).mappings().all()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def conversations(self, limit: int = 50) -> list[dict[str, object]]:
        query = text("""SELECT m.conversation_id, COUNT(*) AS message_count,
            MAX(m.created_at) AS updated_at,
            (SELECT latest.content FROM messages AS latest WHERE latest.conversation_id=m.conversation_id
             ORDER BY latest.id DESC LIMIT 1) AS last_message
            FROM messages AS m GROUP BY m.conversation_id ORDER BY MAX(m.id) DESC LIMIT :limit""")
        with self.engine.connect() as db:
            rows = db.execute(query, {"limit": limit}).mappings().all()
        return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> list[dict[str, str]]:
        with self.engine.connect() as db:
            rows = db.execute(text("SELECT role, content, created_at FROM messages WHERE conversation_id=:cid ORDER BY id ASC"),
                              {"cid": conversation_id}).mappings().all()
        return [{"role": row["role"], "content": row["content"], "created_at": str(row["created_at"])} for row in rows]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self.engine.begin() as db:
            result = db.execute(text("DELETE FROM messages WHERE conversation_id=:cid"), {"cid": conversation_id})
            return result.rowcount > 0
