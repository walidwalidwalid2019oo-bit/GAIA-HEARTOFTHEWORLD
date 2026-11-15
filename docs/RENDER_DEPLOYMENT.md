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
- Configures `/health` as the platform health-check path.
- Requests the provider key and model as dashboard-supplied secrets/settings.
- Generates a backend bearer token rather than putting one in source code.

## Important: do not use real personal memory on this free staging service

The current conversation history and long-term facts are stored in SQLite at
`GAIA_DB_PATH` (default: `data/gaia.sqlite3`). Render Free web services have
an ephemeral filesystem. They spin down after 15 minutes without inbound
traffic, and local filesystem changes are lost when the service spins down,
restarts, or redeploys.

Therefore this blueprint is suitable only for disposable staging tests with
non-sensitive test data. It is **not safe for storing real conversations or
personal memory**. Do not connect a real user account or publish the app while
this limitation remains.

Render's free Postgres database is not a permanent free solution either: its
documented lifetime is 30 days. Before GAIA stores real data, choose and test
a durable database plan, implement a database adapter/migration, and verify
backup and restore behavior. Do not simply point SQLite at a different path:
that does not make an ephemeral disk persistent.

## Required deployment checks

1. Keep this service private to development; do not announce it as a release.
2. Set `GAIA_API_KEY` and `GAIA_MODEL` in Render's environment UI. Never
   paste credentials into this file, GitHub commits, the website, or an APK.
3. Copy the generated `GAIA_API_TOKEN` into a secure development-only client
   configuration only for a private test. A shared token embedded in a
   distributed app is not production authentication.
4. Confirm `GET /health` reports provider and API auth configuration.
5. Test an authenticated chat request using disposable content.
6. Confirm expected sleep/wake behavior and inspect logs.
7. Delete disposable test data after the test.

## Current status

- [x] Render blueprint drafted.
- [x] Python/FastAPI start command matched to the repository's current layout.
- [x] Secret values are not committed.
- [x] SQLite data-loss limitation documented.
- [ ] Durable database selected and implemented.
- [ ] Per-user authentication implemented.
- [ ] Rate limits and abuse controls implemented.
- [ ] Backend deployed and verified.
- [ ] Frontend connected to the backend.
- [ ] Android client connected using per-user sessions.

Do not mark the unchecked items complete until they have been implemented and
tested.
