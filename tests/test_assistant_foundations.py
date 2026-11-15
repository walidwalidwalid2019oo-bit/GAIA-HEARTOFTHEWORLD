from __future__ import annotations

import pytest

from gaia.assistant.memory import LongTermMemory, MemoryFactError
from gaia.assistant.policy import (
    ActionDecision,
    ActionRisk,
    ApprovalLedger,
    evaluate_action,
)


def test_action_policy_requires_approval_for_ask_and_never_overrides_block():
    assert evaluate_action(ActionRisk.SAFE) is ActionDecision.EXECUTE
    assert evaluate_action(ActionRisk.MONITOR) is ActionDecision.EXECUTE_AND_LOG
    assert evaluate_action(ActionRisk.ASK) is ActionDecision.REQUIRE_APPROVAL
    assert evaluate_action(ActionRisk.ASK, approved=True) is ActionDecision.EXECUTE
    assert evaluate_action(ActionRisk.BLOCK, approved=True) is ActionDecision.BLOCK


def test_action_policy_rejects_unknown_risk():
    with pytest.raises(ValueError):
        evaluate_action("unknown")


def test_approval_ledger_requires_exact_arguments_and_is_single_use(tmp_path):
    ledger = ApprovalLedger(tmp_path / "gaia.sqlite3")
    arguments = {"destination": "notes", "text": "Project checkpoint"}
    ticket = ledger.create("notes.create", arguments)

    assert ledger.decide(
        ticket["approval_id"], "notes.create", {"destination": "other"}, approve=True
    ) is False
    assert ledger.status(ticket["approval_id"])["status"] == "pending"

    assert ledger.decide(
        ticket["approval_id"], "notes.create", arguments, approve=True
    ) is True
    assert ledger.consume(ticket["approval_id"], "notes.create", arguments) is True
    assert ledger.consume(ticket["approval_id"], "notes.create", arguments) is False
    assert ledger.status(ticket["approval_id"])["status"] == "consumed"


def test_approval_ledger_persists_and_denial_cannot_be_reversed(tmp_path):
    database = tmp_path / "gaia.sqlite3"
    first = ApprovalLedger(database)
    ticket = first.create("calendar.create_reminder", {"title": "Review notes"})
    assert first.decide(
        ticket["approval_id"], "calendar.create_reminder",
        {"title": "Review notes"}, approve=False
    ) is True

    reopened = ApprovalLedger(database)
    assert reopened.status(ticket["approval_id"])["status"] == "denied"
    assert reopened.decide(
        ticket["approval_id"], "calendar.create_reminder",
        {"title": "Review notes"}, approve=True
    ) is False


def test_approval_ledger_rejects_invalid_action_names_and_payloads(tmp_path):
    ledger = ApprovalLedger(tmp_path / "gaia.sqlite3")
    with pytest.raises(ValueError):
        ledger.create("../delete", {})
    with pytest.raises(ValueError):
        ledger.create("notes.create", {"not_json": object()})


def test_long_term_memory_is_separate_and_persists(tmp_path):
    database = tmp_path / "gaia.sqlite3"
    first = LongTermMemory(database)
    saved = first.add("preferences", "I prefer concise project summaries.")

    reopened = LongTermMemory(database)
    assert reopened.list(category="preferences")[0]["fact_id"] == saved["fact_id"]
    assert reopened.list(category="preferences")[0]["content"] == (
        "I prefer concise project summaries."
    )


def test_long_term_memory_rejects_credential_like_text(tmp_path):
    memory = LongTermMemory(tmp_path / "gaia.sqlite3")
    with pytest.raises(MemoryFactError):
        memory.add("general", "api_key: example-value")
    with pytest.raises(MemoryFactError):
        memory.add("general", "password = example-value")


def test_long_term_memory_validates_category_and_content(tmp_path):
    memory = LongTermMemory(tmp_path / "gaia.sqlite3")
    with pytest.raises(MemoryFactError):
        memory.add("../private", "A valid note")
    with pytest.raises(MemoryFactError):
        memory.add("general", "   ")


def test_long_term_memory_delete_only_removes_selected_fact(tmp_path):
    memory = LongTermMemory(tmp_path / "gaia.sqlite3")
    first = memory.add("projects", "GAIA")
    second = memory.add("projects", "VOID PRINT")

    assert memory.delete(first["fact_id"]) is True
    assert memory.delete(first["fact_id"]) is False
    assert [fact["fact_id"] for fact in memory.list()] == [second["fact_id"]]
