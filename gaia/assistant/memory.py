"""Explicitly saved long-term facts, separate from chat transcripts."""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(os.getenv("GAIA_DB_PATH", "data/gaia.sqlite3"))
_CATEGORY = re.compile(r"[a-z][a-z0-9_-]{0,39}")
_SECRET_PATTERN = re.compile(
    r"(?i)(?:api[_ -]?key|access[_ -]?token|password|recovery code|secret)\s*[:=]"
)


class MemoryFactError(ValueError):
    """A fact is invalid or appears to contain a credential."""


class LongTermMemory:
    """Store only facts explicitly submitted by the user."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS memory_facts (
                    fact_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_facts_created "
                "ON memory_facts(created_at DESC)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path), timeout=10)

    @staticmethod
    def _validate(category: str, content: str) -> tuple[str, str]:
        category = category.strip().casefold()
        content = content.strip()
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
        with self._connect() as db:
            db.execute(
                "INSERT INTO memory_facts(fact_id, category, content) VALUES (?, ?, ?)",
                (fact_id, category, content),
            )
            row = db.execute(
                "SELECT created_at FROM memory_facts WHERE fact_id=?",
                (fact_id,),
            ).fetchone()
        return {
            "fact_id": fact_id,
            "category": category,
            "content": content,
            "created_at": row[0],
        }

    def list(self, *, category: str | None = None, limit: int = 100) -> list[dict[str, str]]:
        if not 1 <= limit <= 200:
            raise ValueError("Limit must be between 1 and 200.")
        if category is not None and not _CATEGORY.fullmatch(category):
            raise ValueError("Invalid memory category.")
        with self._connect() as db:
            if category is None:
                rows = db.execute(
                    "SELECT fact_id, category, content, created_at "
                    "FROM memory_facts ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT fact_id, category, content, created_at FROM memory_facts "
                    "WHERE category=? ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
        return [
            {"fact_id": fact_id, "category": item_category,
             "content": content, "created_at": created_at}
            for fact_id, item_category, content, created_at in rows
        ]

    def delete(self, fact_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM memory_facts WHERE fact_id=?", (fact_id,))
            return cursor.rowcount > 0
