# PostgreSQL storage verification

## Scope

The PostgreSQL 16 CI job exercises two independent persistence boundaries:

- `tests/test_rate_limit_postgres.py` verifies atomic fixed-window counters across several limiter instances.
- `tests/test_postgres_account_storage.py` verifies account credentials and revocable sessions, plus owner-scoped conversation and explicit-fact storage across separately created SQLAlchemy engines.

The account/storage test also inserts a legacy conversation row with a NULL owner and verifies that authenticated owner queries do not expose it. It checks that one account cannot delete another account's conversation or saved fact.

## Running locally

Use a dedicated, disposable PostgreSQL database and set:

```bash
export GAIA_POSTGRES_TEST_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/DEDICATED_TEST_DB'
python -m pytest -q tests/test_rate_limit_postgres.py tests/test_postgres_account_storage.py
```

The tests create uniquely named accounts and records. They do not drop tables, truncate tables, or reset the database. A local test database will retain test rows; do not point the tests at a personal, staging, or production database.

## What a pass means

A passing CI job verifies the exercised PostgreSQL 16 schema creation, session lookup/revocation, owner filters, hidden NULL-owner history, cross-engine visibility, and rate-limit concurrency.

It does not prove that a hosted provider is configured, that the selected provider has identical operational behavior, or that backups, restore, failover, connection pooling under load, encryption-at-rest, or SQLite migration are ready.

## SQLite migration preparation

A read-only SQLite source inventory is now available in [SQLITE_MIGRATION_PREFLIGHT.md](SQLITE_MIGRATION_PREFLIGHT.md). It reports schema, row counts, owner-assigned versus legacy NULL-owner counts, integrity checks, foreign-key findings, and unrecognized tables without exporting row contents or modifying the source.

This is only a preflight inventory. Its SHA-256 digest covers schema definitions, not row data; it does not compare a destination, migrate records, or constitute a complete migration dry-run. Run it only against a separate, closed, checkpointed database copy. Unknown tables and integrity findings require manual review.

## Remaining storage work

- Select and provision a durable PostgreSQL service only after an explicit owner decision.
- Design and test a reviewed SQLite export/import process with privacy-preserving data checksums, row-count reconciliation, idempotency, and rollback.
- Test backup and restore using disposable data.
- Define migration versioning and operational rollback before any real-data migration.

GAIA remains private development. Public release is forbidden before V19.
