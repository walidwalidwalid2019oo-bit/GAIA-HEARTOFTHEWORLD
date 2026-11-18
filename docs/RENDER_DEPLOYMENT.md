# GAIA on Render — Staging Deployment Plan

## Purpose

This is a staging-only deployment blueprint for testing the existing FastAPI
backend. It is **not** a public-release configuration. GAIA's public release
target remains V19.

## What the blueprint does

- Uses Render's native Python runtime.
- Installs the pinned project requirements from `requirements.txt`.
- Starts the existing FastAPI app as `backend.main:app`.
- Uses Render's assigned `PORT`.
- Configures `/health/live` as the platform health-check path.
- Supports an externally managed PostgreSQL database through the private `GAIA_DATABASE_URL` setting.
- Allows browser origins only when exact values are supplied through `GAIA_CORS_ORIGINS`.
- Requests the provider key and model as dashboard-supplied secrets/settings.
- Generates a private rate-limit HMAC secret rather than putting one in source code.
- Keeps the legacy shared bearer token disabled for account-based staging.

## Important: do not use real personal memory on this free staging service

The backend now has a SQLAlchemy storage adapter for local SQLite and hosted
PostgreSQL. Set `GAIA_DATABASE_URL` to a separately managed PostgreSQL URL to
keep conversation history, explicit facts, and action-approval records outside
the web service's ephemeral filesystem. If it is absent, GAIA falls back to
SQLite at `GAIA_DB_PATH`.

The Render Free web service still has an ephemeral filesystem and sleeps after
15 minutes without inbound traffic. SQLite data on that filesystem is lost on
spin-down, restart, or redeploy. The database adapter does not itself create a
managed database, provision backups, or migrate existing SQLite records.

Before using real data, choose a durable PostgreSQL provider/plan, configure
its URL privately, test schema creation and backup/restore, and explicitly
migrate any existing SQLite records. Render's free Postgres database is not a
permanent free solution; its documented lifetime is 30 days. Do not use that
short-lived database for long-term personal memory.

## Required deployment checks

1. Keep this service private to development; do not announce it as a release.
2. Set `GAIA_API_KEY` and `GAIA_MODEL` in Render's environment UI. Keep the
   generated `GAIA_RATE_LIMIT_SECRET` private and consistent across every
   backend instance. Never paste credentials into this file, GitHub commits,
   the website, or an APK.
3. Configure `GAIA_DATABASE_URL` with a private, durable PostgreSQL URL and
   verify backups and restore before using non-disposable data.
4. Set `GAIA_CORS_ORIGINS` to exact trusted website origins only. Do not use
   wildcards for authenticated APIs.
5. Keep `GAIA_ALLOW_SHARED_TOKEN=false` for account-based staging. The legacy
   `GAIA_API_TOKEN` is not needed for normal account sessions; never embed it
   in website code or a distributed app.
6. Confirm `GET /health` reports the selected database backend and readiness.
7. Test authenticated requests with disposable content, then inspect logs.

## Current status

- [x] Render blueprint drafted.
- [x] Python/FastAPI start command matched to the repository's current layout.
- [x] Secret values are not committed.
- [x] SQLite data-loss limitation documented.
- [x] SQLAlchemy adapter supports SQLite and PostgreSQL for conversation history, explicit facts, and approval records.
- [ ] Durable PostgreSQL provider selected, provisioned, configured, and backup/restore verified.
- [ ] Existing SQLite data explicitly migrated (no automatic migration is performed).
- [x] Development email/password sessions and owner-scoped API routes implemented in the account feature branch.
- [ ] Refresh-token rotation, recovery, and full authentication hardening.
- [x] Initial persistent registration, login, and per-account chat limits implemented in the private feature branch.
- [ ] Trusted per-IP limits and adaptive abuse controls configured and tested.
- [ ] PostgreSQL rate-limit concurrency tested against the selected durable database.
- [ ] Backend deployed and verified.
- [x] Website can perform a public read-only backend health check without embedding a secret.
- [ ] Authenticated frontend chat connected after per-user sessions and data isolation.
- [ ] Android client connected using per-user sessions.

Do not mark the unchecked items complete until they have been implemented and
tested.
