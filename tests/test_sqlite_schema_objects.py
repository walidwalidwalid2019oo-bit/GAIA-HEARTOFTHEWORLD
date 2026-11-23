from __future__ import annotations

import json
import sqlite3

from gaia.migrations.sqlite_inventory import inspect_sqlite_database


def test_inventory_lists_custom_schema_objects_without_emitting_sql(tmp_path):
    source = tmp_path / "schema-objects.sqlite3"
    with sqlite3.connect(source) as db:
        db.executescript(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY,
                owner_id TEXT,
                role TEXT
            );
            CREATE INDEX idx_messages_owner_role
                ON messages(owner_id, role);
            CREATE INDEX idx_messages_role_lower
                ON messages(lower(role))
                WHERE role IS NOT NULL;
            CREATE VIEW message_totals AS
                SELECT COUNT(*) AS total FROM messages;
            CREATE TRIGGER messages_after_insert
                AFTER INSERT ON messages
                BEGIN
                    SELECT 'private-trigger-literal';
                END;
            """
        )

    report = inspect_sqlite_database(source)
    rendered = json.dumps(report)
    objects = {
        (item["type"], item["name"]): item
        for item in report["schema_objects"]
    }

    assert report["status"] == "review_required"
    assert set(report["unsupported_schema_objects"]) == {
        ("index", "idx_messages_owner_role"),
        ("index", "idx_messages_role_lower"),
        ("view", "message_totals"),
        ("trigger", "messages_after_insert"),
    } or {
        (item["type"], item["name"])
        for item in report["unsupported_schema_objects"]
    } == {
        ("index", "idx_messages_owner_role"),
        ("index", "idx_messages_role_lower"),
        ("view", "message_totals"),
        ("trigger", "messages_after_insert"),
    }

    regular_index = objects[("index", "idx_messages_owner_role")]["index"]
    assert regular_index == {
        "unique": False,
        "origin": "c",
        "partial": False,
        "columns": [
            {"sequence": 0, "name": "owner_id", "expression": False},
            {"sequence": 1, "name": "role", "expression": False},
        ],
    }

    expression_index = objects[("index", "idx_messages_role_lower")]["index"]
    assert expression_index["partial"] is True
    assert expression_index["columns"] == [
        {"sequence": 0, "name": None, "expression": True}
    ]

    assert objects[("view", "message_totals")]["table_name"] == "message_totals"
    assert objects[("trigger", "messages_after_insert")]["table_name"] == "messages"
    assert "private-trigger-literal" not in rendered
    assert "CREATE TRIGGER" not in rendered
    assert "CREATE VIEW" not in rendered
    assert "Custom indexes, views, and triggers require manual migration review." in report["warnings"]
