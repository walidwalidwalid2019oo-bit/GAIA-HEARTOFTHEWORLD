from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from gaia.migrations.sqlite_inventory import inspect_sqlite_database, main


def create_database(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner_id TEXT
            );
            CREATE TABLE custom_plugin_records (payload TEXT NOT NULL);
            INSERT INTO users VALUES (
                'user-1', 'private@example.test', 'not-a-real-password-hash', '2026-01-01'
            );
            INSERT INTO messages VALUES (
                1, 'conversation-1', 'user', 'private conversation text', '2026-01-01', NULL
            );
            INSERT INTO messages VALUES (
                2, 'conversation-1', 'assistant', 'another private value', '2026-01-01', 'user-1'
            );
            INSERT INTO custom_plugin_records VALUES ('do not export this');
            """
        )


def test_inventory_is_read_only_and_does_not_export_row_contents(tmp_path):
    source = tmp_path / "gaia.sqlite3"
    create_database(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    report = inspect_sqlite_database(source)

    after = hashlib.sha256(source.read_bytes()).hexdigest()
    rendered = json.dumps(report)

    assert before == after
    assert report["source_modified"] is False
    assert report["data_contents_exported"] is False
    assert report["status"] == "review_required"
    assert report["integrity_check"] == ["ok"]
    assert report["unsupported_tables"] == ["custom_plugin_records"]
    assert "private@example.test" not in rendered
    assert "private conversation text" not in rendered
    assert "do not export this" not in rendered

    messages = next(table for table in report["tables"] if table["name"] == "messages")
    assert messages["row_count"] == 2
    assert messages["ownership"] == {
        "assigned_owner_rows": 1,
        "unassigned_legacy_rows": 1,
    }
    assert len(report["schema_sha256"]) == 64


def test_inventory_refuses_wal_or_journal_sidecars(tmp_path):
    source = tmp_path / "gaia.sqlite3"
    create_database(source)
    (tmp_path / "gaia.sqlite3-wal").write_bytes(b"pending journal data")

    with pytest.raises(RuntimeError, match="journal sidecars"):
        inspect_sqlite_database(source)


def test_inventory_reports_foreign_key_violations_without_row_values(tmp_path):
    source = tmp_path / "broken.sqlite3"
    with sqlite3.connect(source) as db:
        db.executescript(
            """
            CREATE TABLE parents (id INTEGER PRIMARY KEY);
            CREATE TABLE children (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER REFERENCES parents(id)
            );
            INSERT INTO children(id, parent_id) VALUES (1, 999);
            """
        )

    report = inspect_sqlite_database(source)

    assert report["status"] == "review_required"
    assert report["foreign_key_violation_count_sampled"] == 1
    assert report["foreign_key_violation_samples"][0]["table"] == "children"
    assert report["foreign_key_violation_samples"][0]["parent_table"] == "parents"


def test_cli_emits_json_and_returns_review_status(tmp_path, capsys):
    source = tmp_path / "gaia.sqlite3"
    create_database(source)

    exit_code = main(["--source", str(source)])
    output = capsys.readouterr().out
    report = json.loads(output)

    assert exit_code == 2
    assert report["status"] == "review_required"


def test_inventory_rejects_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        inspect_sqlite_database(tmp_path / "missing.sqlite3")
