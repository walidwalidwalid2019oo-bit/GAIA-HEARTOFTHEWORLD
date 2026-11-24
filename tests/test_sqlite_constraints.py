from __future__ import annotations

import json
import sqlite3

from gaia.migrations.sqlite_inventory import inspect_sqlite_database


def test_inventory_reports_keys_foreign_keys_defaults_and_generated_columns(tmp_path):
    source = tmp_path / "constraints.sqlite3"
    with sqlite3.connect(source) as db:
        db.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE parents (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL UNIQUE DEFAULT 'private-default-marker',
                status TEXT NOT NULL CHECK(status IN ('active', 'inactive'))
            ) STRICT;
            CREATE TABLE children (
                id INTEGER PRIMARY KEY,
                parent_code TEXT NOT NULL,
                doubled TEXT GENERATED ALWAYS AS (parent_code || parent_code) STORED,
                FOREIGN KEY(parent_code) REFERENCES parents(code)
                    ON UPDATE RESTRICT ON DELETE CASCADE
            ) STRICT;
            CREATE TABLE stable_keys (
                key TEXT PRIMARY KEY,
                payload TEXT
            ) WITHOUT ROWID, STRICT;
            """
        )

    report = inspect_sqlite_database(source)
    rendered = json.dumps(report)
    tables = {table["name"]: table for table in report["tables"]}

    parents = tables["parents"]
    assert parents["primary_key_columns"] == ["id"]
    assert any(
        index["origin"] == "u"
        and index["unique"] is True
        and [column["name"] for column in index["columns"]] == ["code"]
        for index in parents["indexes"]
    )
    code_column = next(column for column in parents["columns"] if column["name"] == "code")
    assert code_column["has_default"] is True
    assert code_column["generated_kind"] is None
    assert parents["table_options"] == {"without_rowid": False, "strict": True}

    children = tables["children"]
    generated = next(column for column in children["columns"] if column["name"] == "doubled")
    assert generated["hidden_code"] == 3
    assert generated["generated_kind"] == "stored"
    assert children["foreign_keys"] == [{
        "id": 0,
        "sequence": 0,
        "referenced_table": "parents",
        "from_column": "parent_code",
        "to_column": "code",
        "on_update": "RESTRICT",
        "on_delete": "CASCADE",
        "match": "NONE",
    }]

    stable_keys = tables["stable_keys"]
    assert stable_keys["primary_key_columns"] == ["key"]
    assert stable_keys["table_options"] == {"without_rowid": True, "strict": True}

    assert all(
        table["check_constraints"] == {
            "status": "not_introspected",
            "requires_manual_review": True,
        }
        for table in tables.values()
    )
    assert "private-default-marker" not in rendered
    assert "active" not in rendered
    assert "inactive" not in rendered
    assert "CREATE TABLE" not in rendered
    assert report["format_version"] == 2
    assert report["status"] == "review_required"
    assert any("CHECK constraints are not parsed" in warning for warning in report["warnings"])
