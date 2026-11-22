"""Read-only preflight inventory for a quiescent GAIA SQLite database.

This module never exports row contents or writes to the source database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


_KNOWN_TABLES = frozenset({
    "messages",
    "memory_facts",
    "users",
    "auth_sessions",
    "action_approvals",
    "rate_limit_buckets",
})
_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


def _quote_identifier(value: str) -> str:
    """Quote a SQLite identifier obtained from sqlite_master."""
    return '"' + value.replace('"', '""') + '"'


def _file_signature(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, getattr(stat, "st_ino", 0)


def _existing_sidecars(path: Path) -> list[str]:
    """Return journal sidecar names without exposing the source directory."""
    return [
        Path(str(path) + suffix).name
        for suffix in _SIDECAR_SUFFIXES
        if Path(str(path) + suffix).exists()
    ]


def inspect_sqlite_database(source: str | Path) -> dict[str, Any]:
    """Inventory schema and counts without modifying or exposing source rows.

    The database must be closed and checkpointed. WAL/shared-memory/rollback
    journal sidecars are rejected before and after inspection so the immutable
    read-only connection cannot silently omit committed WAL data.
    """
    path = Path(source).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("SQLite source must be a regular file.")

    sidecars = _existing_sidecars(path)
    if sidecars:
        raise RuntimeError(
            "SQLite source has journal sidecars; close the application and "
            "create a clean, checkpointed copy before inspection."
        )

    before = _file_signature(path)
    uri = path.as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True, timeout=2)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")

        schema_rows = connection.execute(
            """
            SELECT type, name, tbl_name, COALESCE(sql, '')
            FROM sqlite_master
            WHERE type IN ('table', 'index', 'view', 'trigger')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()
        schema_material = "\n".join(
            "\0".join(str(value) for value in row) for row in schema_rows
        )
        schema_digest = hashlib.sha256(schema_material.encode("utf-8")).hexdigest()

        table_names = [
            row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        tables: list[dict[str, Any]] = []
        for table_name in table_names:
            quoted = _quote_identifier(table_name)
            column_rows = connection.execute(
                f"PRAGMA table_info({quoted})"
            ).fetchall()
            columns = [
                {
                    "name": row["name"],
                    "type": row["type"] or "",
                    "not_null": bool(row["notnull"]),
                    "primary_key_position": int(row["pk"]),
                }
                for row in column_rows
            ]
            row_count = int(
                connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
            )
            table_report: dict[str, Any] = {
                "name": table_name,
                "row_count": row_count,
                "columns": columns,
            }
            column_names = {column["name"] for column in columns}
            if "owner_id" in column_names:
                table_report["ownership"] = {
                    "assigned_owner_rows": int(connection.execute(
                        f"SELECT COUNT(*) FROM {quoted} WHERE owner_id IS NOT NULL"
                    ).fetchone()[0]),
                    "unassigned_legacy_rows": int(connection.execute(
                        f"SELECT COUNT(*) FROM {quoted} WHERE owner_id IS NULL"
                    ).fetchone()[0]),
                }
            tables.append(table_report)

        quick_check = [
            str(row[0]) for row in connection.execute("PRAGMA quick_check").fetchall()
        ]
        foreign_key_rows = connection.execute("PRAGMA foreign_key_check").fetchmany(20)
        foreign_key_samples = [
            {
                "table": row[0],
                "rowid": row[1],
                "parent_table": row[2],
                "foreign_key_index": row[3],
            }
            for row in foreign_key_rows
        ]
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    finally:
        connection.close()

    # immutable=1 deliberately ignores WAL files. Recheck after the read so a
    # sidecar appearing during inspection cannot produce a misleading report.
    sidecars_after = _existing_sidecars(path)
    if sidecars_after:
        raise RuntimeError(
            "SQLite source gained journal sidecars during inspection; discard "
            "the report and retry with a closed, checkpointed copy."
        )

    after = _file_signature(path)
    if before != after:
        raise RuntimeError(
            "SQLite source changed during inspection; use a closed, stable copy and retry."
        )

    unsupported_tables = sorted(set(table_names) - _KNOWN_TABLES)
    warnings: list[str] = []
    if quick_check != ["ok"]:
        warnings.append("SQLite quick_check reported integrity problems.")
    if foreign_key_samples:
        warnings.append("SQLite foreign_key_check reported violations (up to 20 shown).")
    if unsupported_tables:
        warnings.append("Unrecognized tables require manual migration review.")

    return {
        "format_version": 1,
        "source_name": path.name,
        "source_size_bytes": before[0],
        "sqlite_user_version": user_version,
        "schema_sha256": schema_digest,
        "integrity_check": quick_check,
        "foreign_key_violation_count_sampled": len(foreign_key_samples),
        "foreign_key_violation_samples": foreign_key_samples,
        "tables": tables,
        "unsupported_tables": unsupported_tables,
        "warnings": warnings,
        "status": "review_required" if warnings else "preflight_complete",
        "data_contents_exported": False,
        "source_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a read-only inventory of a closed GAIA SQLite database."
    )
    parser.add_argument("--source", required=True, help="Path to a closed, checkpointed SQLite copy.")
    args = parser.parse_args(argv)
    try:
        report = inspect_sqlite_database(args.source)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["status"] == "preflight_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
