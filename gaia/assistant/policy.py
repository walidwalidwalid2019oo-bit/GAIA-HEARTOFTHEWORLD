"""Risk decisions and one-time approvals for future GAIA actions.

This module deliberately does not execute actions. Integrations must evaluate
risk before execution and consume an exact, one-time approval for ASK actions.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

_ACTION_NAME = re.compile(r"[a-z][a-z0-9_.-]{1,79}")
_DEFAULT_DB = Path("data/gaia.sqlite3")


class ActionRisk(str, Enum):
    SAFE = "safe"
    MONITOR = "monitor"
    ASK = "ask"
    BLOCK = "block"


class ActionDecision(str, Enum):
    EXECUTE = "execute"
    EXECUTE_AND_LOG = "execute_and_log"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


def evaluate_action(risk: ActionRisk | str, *, approved: bool = False) -> ActionDecision:
    """Return the policy decision; approval can never override BLOCK."""
    try:
        level = ActionRisk(risk)
    except ValueError as exc:
        raise ValueError("Unknown action risk level.") from exc

    if level is ActionRisk.BLOCK:
        return ActionDecision.BLOCK
    if level is ActionRisk.ASK and not approved:
        return ActionDecision.REQUIRE_APPROVAL
    if level is ActionRisk.MONITOR:
        return ActionDecision.EXECUTE_AND_LOG
    return ActionDecision.EXECUTE


def _fingerprint(action_name: str, arguments: dict[str, object]) -> str:
    if not _ACTION_NAME.fullmatch(action_name):
        raise ValueError("Action name must be a short lowercase identifier.")
    try:
        canonical = json.dumps(
            {"action": action_name, "arguments": arguments},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Action arguments must be JSON-compatible data.") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ApprovalLedger:
    """Persist exact-argument, expiring, single-use approvals in the shared database."""

    def __init__(self, path: Path | None = None, *, engine: Engine | None = None) -> None:
        self.engine = engine or create_database_engine(path)
        with self.engine.begin() as db:
            db.execute(text("""CREATE TABLE IF NOT EXISTS action_approvals (
                approval_id VARCHAR(36) PRIMARY KEY,
                action_name VARCHAR(80) NOT NULL,
                arguments_hash VARCHAR(64) NOT NULL,
                status VARCHAR(9) NOT NULL CHECK(
                    status IN ('pending', 'approved', 'denied', 'consumed', 'expired')
                ),
                created_at VARCHAR(40) NOT NULL,
                expires_at VARCHAR(40) NOT NULL,
                decided_at VARCHAR(40)
            )"""))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_action_approvals_status ON action_approvals(status, expires_at)"))

    def create(self, action_name: str, arguments: dict[str, object], *, ttl_seconds: int = 300) -> dict[str, str]:
        if not 1 <= ttl_seconds <= 900:
            raise ValueError("Approval lifetime must be between 1 and 900 seconds.")
        digest = _fingerprint(action_name, arguments)
        now = datetime.now(timezone.utc)
        approval_id = str(uuid4())
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self.engine.begin() as db:
            db.execute(text("""INSERT INTO action_approvals
                (approval_id, action_name, arguments_hash, status, created_at, expires_at)
                VALUES (:id, :action, :digest, 'pending', :created, :expires)"""),
                {"id": approval_id, "action": action_name, "digest": digest,
                 "created": now.isoformat(), "expires": expires_at.isoformat()})
        return {"approval_id": approval_id, "action_name": action_name,
                "status": "pending", "expires_at": expires_at.isoformat()}

    def decide(self, approval_id: str, action_name: str, arguments: dict[str, object], *, approve: bool) -> bool:
        """Approve or deny only the exact pending action and its exact arguments."""
        digest = _fingerprint(action_name, arguments)
        now = datetime.now(timezone.utc)
        with self.engine.begin() as db:
            query = "SELECT action_name, arguments_hash, status, expires_at FROM action_approvals WHERE approval_id=:id"
            if self.engine.dialect.name == "postgresql":
                query += " FOR UPDATE"
            row = db.execute(text(query), {"id": approval_id}).mappings().one_or_none()
            if row is None or row["status"] != "pending":
                return False
            if datetime.fromisoformat(row["expires_at"]) <= now:
                db.execute(text("UPDATE action_approvals SET status='expired' WHERE approval_id=:id AND status='pending'"),
                           {"id": approval_id})
                return False
            if row["action_name"] != action_name or row["arguments_hash"] != digest:
                return False
            status = "approved" if approve else "denied"
            result = db.execute(text("""UPDATE action_approvals SET status=:status, decided_at=:now
                WHERE approval_id=:id AND status='pending'"""),
                {"status": status, "now": now.isoformat(), "id": approval_id})
            return result.rowcount == 1

    def consume(self, approval_id: str, action_name: str, arguments: dict[str, object]) -> bool:
        """Consume an approval once; a changed payload or second use is rejected."""
        digest = _fingerprint(action_name, arguments)
        now = datetime.now(timezone.utc)
        with self.engine.begin() as db:
            query = "SELECT action_name, arguments_hash, status, expires_at FROM action_approvals WHERE approval_id=:id"
            if self.engine.dialect.name == "postgresql":
                query += " FOR UPDATE"
            row = db.execute(text(query), {"id": approval_id}).mappings().one_or_none()
            if row is None or row["status"] != "approved":
                return False
            if datetime.fromisoformat(row["expires_at"]) <= now:
                db.execute(text("UPDATE action_approvals SET status='expired' WHERE approval_id=:id AND status='approved'"),
                           {"id": approval_id})
                return False
            if row["action_name"] != action_name or row["arguments_hash"] != digest:
                return False
            result = db.execute(text("UPDATE action_approvals SET status='consumed' WHERE approval_id=:id AND status='approved'"),
                                {"id": approval_id})
            return result.rowcount == 1

    def status(self, approval_id: str) -> dict[str, str] | None:
        with self.engine.connect() as db:
            row = db.execute(text("""SELECT action_name, status, created_at, expires_at, decided_at
                FROM action_approvals WHERE approval_id=:id"""), {"id": approval_id}).mappings().one_or_none()
        if row is None:
            return None
        return {"approval_id": approval_id, "action_name": row["action_name"],
                "status": row["status"], "created_at": row["created_at"],
                "expires_at": row["expires_at"], "decided_at": row["decided_at"] or ""}
