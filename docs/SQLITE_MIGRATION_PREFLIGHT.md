# GAIA SQLite migration preflight

## Purpose

gaia.migrations.sqlite_inventory is the first, read-only preparation step for a future SQLite-to-PostgreSQL migration. It does not connect to a destination database, export records, change ownership, create tables, or modify the source.

Run it against a separate, closed, checkpointed copy of the local database:

```bash
python -m gaia.migrations.sqlite_inventory --source /path/to/gaia.sqlite3
```

The command prints a JSON inventory. A non-zero exit status means the inventory requires review; inspect the JSON warnings rather than treating it as a migration approval.

## What it reports

- Source filename and byte size (not the full local path).
- SQLite user_version and a SHA-256 digest of schema definitions only.
- Table names, column names/types, and row counts.
- Assigned and unassigned (owner_id IS NULL) row counts for owner-scoped tables.
- SQLite quick_check and up to 20 foreign-key violation samples.
- Tables not yet recognized by GAIA's migration allowlist.

The report never includes row contents, email addresses, password hashes, session tokens, message text, memory facts, or provider credentials. schema_sha256 is not a checksum of table data and must not be described as one.

## Read-only guarantees and constraints

- Opens SQLite with mode=ro and immutable=1, and enables query_only.
- Refuses to inspect a source while -wal, -shm, or -journal sidecars exist. This avoids silently ignoring uncheckpointed WAL data or creating sidecars while inspecting.
- Checks file size, modification time, and inode before and after inspection.
- Performs only schema queries, aggregate counts, and integrity checks.
- Does not create a destination, write a migration manifest, or change owner_id values.

Close the application that owns the database and make a separate copy before running the tool. If the database has journal sidecars, do not delete them manually. Use the database application's normal shutdown/checkpoint process, then make a fresh copy.

## Recognized current tables

- messages
- memory_facts
- users
- auth_sessions
- action_approvals
- rate_limit_buckets

Any other user table is reported as unsupported and requires explicit schema review. A missing recognized table is not automatically an error because some components may not have been initialized in a local database.

## What this does not do

This is not a data migration, backup, restore, or complete dry-run. It does not compare source and destination rows, compute row-content checksums, transform timestamps/identity columns, migrate indexes/constraints, or reassign legacy records with NULL owners. The schema digest only fingerprints SQLite schema definitions.

A later migration milestone must define a reviewed table/column allowlist, safe type conversion, keyed integrity checks that do not expose personal data, destination-side validation, idempotency, rollback, and explicit owner mapping. No real database should be migrated until the owner approves the destination and a separate backup/restore test has passed.

GAIA remains private development. Public release is forbidden before V19.
