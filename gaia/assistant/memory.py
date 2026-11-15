"""Explicitly saved long-term facts, separate from chat transcripts."""
from __future__ import annotations
import re
from pathlib import Path
from uuid import uuid4
from sqlalchemy import Engine, text
from gaia.storage import create_database_engine

DB_PATH = Path("data/gaia.sqlite3")
_CATEGORY = re.compile(r"[a-z][a-z0-9_-]{0,39}")
_SECRET_PATTERN = re.compile(r"(?i)(?:api[_ -]?key|access[_ -]?token|password|recovery code|secret)\\s*[:=]")

class MemoryFactError(ValueError):
    """A fact is invalid or appears to contain a credential."""

class LongTermMemory:
    """Store only facts explicitly submitted by the user."""
    def __init__(self, path: Path | None = None, *, engine: Engine | None = None) -> None:
        self.engine = engine or create_database_engine(path)
        with self.engine.begin() as db:
            db.execute(text("""CREATE TABLE IF NOT EXISTS memory_facts (
                fact_id VARCHAR(36) PRIMARY KEY, category VARCHAR(40) NOT NULL,
                content TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_facts_created ON memory_facts(created_at)"))

    @staticmethod
    def _validate(category: str, content: str) -> tuple[str, str]:
        category, content = category.strip().casefold(), content.strip()
        if not _CATEGORY.fullmatch(category):
            raise MemoryFactError("Category must be a short lowercase identifier.")
        if not content or len(content) > 2000:
            raise MemoryFactError("Memory fact must contain 1 to 2000 characters.")
        if _SECRET_PATTERN.search(content):
            raise MemoryFactError("GAIA will not save text that looks like a credential.")
        return category, content

    def add(self, category: str, content: str) -> dict[str, str]:
        category, content = self._validate(category, content)
        fact_id = str(uuid4())
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO memory_facts(fact_id, category, content) VALUES (:id, :category, :content)"),
                       {"id": fact_id, "category": category, "content": content})
            row = db.execute(text("SELECT created_at FROM memory_facts WHERE fact_id=:id"), {"id": fact_id}).mappings().one()
        return {"fact_id": fact_id, "category": category, "content": content, "created_at": str(row["created_at"])}

    def list(self, *, category: str | None = None, limit: int = 100) -> list[dict[str, str]]:
        if not 1 <= limit <= 200:
            raise ValueError("Limit must be between 1 and 200.")
        if category is not None and not _CATEGORY.fullmatch(category):
            raise ValueError("Invalid memory category.")
        if category is None:
            query = text("SELECT fact_id, category, content, created_at FROM memory_facts ORDER BY created_at DESC, fact_id DESC LIMIT :limit")
            params = {"limit": limit}
        else:
            query = text("SELECT fact_id, category, content, created_at FROM memory_facts WHERE category=:category ORDER BY created_at DESC, fact_id DESC LIMIT :limit")
            params = {"category": category, "limit": limit}
        with self.engine.connect() as db:
            rows = db.execute(query, params).mappings().all()
        return [{"fact_id": row["fact_id"], "category": row["category"], "content": row["content"], "created_at": str(row["created_at"])} for row in rows]

    def delete(self, fact_id: str) -> bool:
        with self.engine.begin() as db:
            result = db.execute(text("DELETE FROM memory_facts WHERE fact_id=:id"), {"id": fact_id})
            return result.rowcount > 0
