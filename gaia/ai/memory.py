"""Owner-scoped conversation history backed by SQLite or PostgreSQL."""
from __future__ import annotations

from pathlib import Path
from sqlalchemy import Engine, inspect, text
from gaia.storage import create_database_engine

DB_PATH = Path("data/gaia.sqlite3")
_DEFAULT_OWNER = "local"


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
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                owner_id VARCHAR(36)
            )"""))
            # Additive migration: old rows stay NULL and are deliberately not
            # visible to any authenticated owner until an explicit migration.
            columns = {column["name"] for column in inspect(db).get_columns("messages")}
            if "owner_id" not in columns:
                db.execute(text("ALTER TABLE messages ADD COLUMN owner_id VARCHAR(36)"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_owner_conversation ON messages(owner_id, conversation_id, id)"))

    def add(self, conversation_id: str, role: str, content: str, *, owner_id: str = _DEFAULT_OWNER) -> None:
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO messages(conversation_id, role, content, owner_id) "
                            "VALUES (:cid, :role, :content, :owner)"),
                       {"cid": conversation_id, "role": role, "content": content, "owner": owner_id})

    def recent(self, conversation_id: str, limit: int = 16, *, owner_id: str = _DEFAULT_OWNER) -> list[dict[str, str]]:
        with self.engine.connect() as db:
            rows = db.execute(text("SELECT role, content FROM messages "
                                   "WHERE conversation_id=:cid AND owner_id=:owner "
                                   "ORDER BY id DESC LIMIT :limit"),
                              {"cid": conversation_id, "owner": owner_id, "limit": limit}).mappings().all()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def conversations(self, limit: int = 50, *, owner_id: str = _DEFAULT_OWNER) -> list[dict[str, object]]:
        query = text("""SELECT m.conversation_id, COUNT(*) AS message_count,
            MAX(m.created_at) AS updated_at,
            (SELECT latest.content FROM messages AS latest
             WHERE latest.conversation_id=m.conversation_id AND latest.owner_id=m.owner_id
             ORDER BY latest.id DESC LIMIT 1) AS last_message
            FROM messages AS m WHERE m.owner_id=:owner
            GROUP BY m.owner_id, m.conversation_id
            ORDER BY MAX(m.id) DESC LIMIT :limit""")
        with self.engine.connect() as db:
            rows = db.execute(query, {"owner": owner_id, "limit": limit}).mappings().all()
        return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str, *, owner_id: str = _DEFAULT_OWNER) -> list[dict[str, str]]:
        with self.engine.connect() as db:
            rows = db.execute(text("SELECT role, content, created_at FROM messages "
                                   "WHERE conversation_id=:cid AND owner_id=:owner ORDER BY id ASC"),
                              {"cid": conversation_id, "owner": owner_id}).mappings().all()
        return [{"role": row["role"], "content": row["content"], "created_at": str(row["created_at"])} for row in rows]

    def delete_conversation(self, conversation_id: str, *, owner_id: str = _DEFAULT_OWNER) -> bool:
        with self.engine.begin() as db:
            result = db.execute(text("DELETE FROM messages WHERE conversation_id=:cid AND owner_id=:owner"),
                                {"cid": conversation_id, "owner": owner_id})
            return result.rowcount > 0
