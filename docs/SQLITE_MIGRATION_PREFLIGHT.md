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
- Structural metadata for custom indexes, views, and triggers.
- SQLite quick_check and up to 20 foreign-key violation samples.
- Tables not yet recognized by GAIA's migration allowlist.

The report never includes row contents, email addresses, password hashes, session tokens, message text, memory facts, provider credentials, or raw schema SQL. Index metadata includes uniqueness, origin, partial-index status, and column names; expression-index entries are marked without returning their SQL expression. schema_sha256 is not a checksum of table data and must not be described as one.

## Read-only guarantees and constraints

- Opens SQLite with mode=ro and immutable=1, and enables query_only.
- Refuses to inspect a source while -wal, -shm, or -journal sidecars exist. It checks again after the read and rejects the report if a sidecar appears during inspection, because immutable=1 deliberately ignores WAL files.
- Checks file size, modification time, and inode before and after inspection.
- Performs only schema queries, aggregate counts, and integrity checks.
- Does not create a destination, write a migration manifest, or change owner_id values.

Close the application that owns the database and make a separate copy before running the tool. If the database has journal sidecars, do not delete them manually. Use the database application's normal shutdown/checkpoint process, then make a fresh copy. The pre/post checks reduce race risk but do not replace the requirement to use a closed, stable copy.

## Recognized current tables

- messages
- memory_facts
- users
- auth_sessions
- action_approvals
- rate_limit_buckets

Any other user table is reported as unsupported and requires explicit schema review. A missing recognized table is not automatically an error because some components may not have been initialized in a local database.

## Schema-object handling

Custom indexes, views, and triggers are listed in schema_objects and also appear in unsupported_schema_objects. This intentionally makes the preflight status review_required when any are present: the current migration tool does not recreate these objects automatically.

For indexes, the inventory reports uniqueness, SQLite origin, whether the index is partial, and the ordered named columns. Expression-index columns are identified without exposing their SQL expressions. For views and triggers, only the object type, name, and associated table name are returned. Raw CREATE statements are never included because schema SQL can contain developer-supplied literals.

A future migration allowlist must explicitly approve and recreate each required object, then compare its behavior in disposable SQLite and PostgreSQL databases. An inventory entry is not migration approval.

## What this does not do

This is not a data migration, backup, restore, or complete dry-run. It does not connect to PostgreSQL, export or import records, compare source and destination rows, compute row-content checksums, transform timestamps/identity columns, recreate indexes/views/triggers, or reassign legacy records with NULL owners. The schema digest only fingerprints SQLite schema definitions.

A later migration milestone must define a reviewed table/column/object allowlist, safe type conversion, keyed integrity checks that do not expose personal data, destination-side validation, idempotency, rollback, and explicit owner mapping. No real database should be migrated until the owner approves the destination and a separate backup/restore test has passed.

GAIA remains private development. Public release is forbidden before V19.
