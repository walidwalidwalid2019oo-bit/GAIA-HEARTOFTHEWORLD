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
    """Persist exact-argument, expiring, single-use approvals in SQLite."""

    def __init__(self, path: Path = _DEFAULT_DB) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS action_approvals (
                    approval_id TEXT PRIMARY KEY,
                    action_name TEXT NOT NULL,
                    arguments_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(
                        status IN ('pending', 'approved', 'denied', 'consumed', 'expired')
                    ),
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    decided_at TEXT
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_approvals_status "
                "ON action_approvals(status, expires_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path), timeout=10)

    def create(
        self,
        action_name: str,
        arguments: dict[str, object],
        *,
        ttl_seconds: int = 300,
    ) -> dict[str, str]:
        if not 1 <= ttl_seconds <= 900:
            raise ValueError("Approval lifetime must be between 1 and 900 seconds.")
        digest = _fingerprint(action_name, arguments)
        now = datetime.now(timezone.utc)
        approval_id = str(uuid4())
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self._connect() as db:
            db.execute(
                """INSERT INTO action_approvals
                   (approval_id, action_name, arguments_hash, status, created_at, expires_at)
                   VALUES (?, ?, ?, 'pending', ?, ?)""",
                (approval_id, action_name, digest, now.isoformat(), expires_at.isoformat()),
            )
        return {
            "approval_id": approval_id,
            "action_name": action_name,
            "status": "pending",
            "expires_at": expires_at.isoformat(),
        }

    def decide(
        self,
        approval_id: str,
        action_name: str,
        arguments: dict[str, object],
        *,
        approve: bool,
    ) -> bool:
        """Approve or deny only the exact pending action and its exact arguments."""
        digest = _fingerprint(action_name, arguments)
        now = datetime.now(timezone.utc)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT action_name, arguments_hash, status, expires_at "
                "FROM action_approvals WHERE approval_id=?",
                (approval_id,),
            ).fetchone()
            if row is None or row[2] != "pending":
                return False
            stored_action, stored_digest, _, stored_expiry = row
            if datetime.fromisoformat(stored_expiry) <= now:
                db.execute(
                    "UPDATE action_approvals SET status='expired' WHERE approval_id=?",
                    (approval_id,),
                )
                return False
            if stored_action != action_name or stored_digest != digest:
                return False
            status = "approved" if approve else "denied"
            db.execute(
                "UPDATE action_approvals SET status=?, decided_at=? WHERE approval_id=?",
                (status, now.isoformat(), approval_id),
            )
            return True

    def consume(
        self,
        approval_id: str,
        action_name: str,
        arguments: dict[str, object],
    ) -> bool:
        """Consume an approval once; a changed payload or second use is rejected."""
        digest = _fingerprint(action_name, arguments)
        now = datetime.now(timezone.utc)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT action_name, arguments_hash, status, expires_at "
                "FROM action_approvals WHERE approval_id=?",
                (approval_id,),
            ).fetchone()
            if row is None or row[2] != "approved":
                return False
            stored_action, stored_digest, _, stored_expiry = row
            if datetime.fromisoformat(stored_expiry) <= now:
                db.execute(
                    "UPDATE action_approvals SET status='expired' WHERE approval_id=?",
                    (approval_id,),
                )
                return False
            if stored_action != action_name or stored_digest != digest:
                return False
            db.execute(
                "UPDATE action_approvals SET status='consumed' WHERE approval_id=?",
                (approval_id,),
            )
            return True

    def status(self, approval_id: str) -> dict[str, str] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT action_name, status, created_at, expires_at, decided_at "
                "FROM action_approvals WHERE approval_id=?",
                (approval_id,),
            ).fetchone()
        if row is None:
            return None
        action_name, status, created_at, expires_at, decided_at = row
        return {
            "approval_id": approval_id,
            "action_name": action_name,
            "status": status,
            "created_at": created_at,
            "expires_at": expires_at,
            "decided_at": decided_at or "",
        }
