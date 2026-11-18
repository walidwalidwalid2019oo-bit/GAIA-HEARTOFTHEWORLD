# GAIA — Heart of the World

An original, modular AI ecosystem prototype built around a central coordinator and specialized subsystems.

> Independent project. The website and app use original interface elements and symbolic motifs; no ripped Horizon game assets are included.

## Current builds

### Android-friendly Python app (prototype)

Run with Python 3.10+:

```bash
python app.py
```

The app currently includes:
- GAIA command-center menu
- Seven core subsystem profiles
- Registry status display
- Local JSON memory vault for notes and activity
- HEPHAESTUS blueprint drafting
- GAIA approval/rejection queue

The Android request router is rule-based. A real AI model/API is **not connected to this local app**. Blueprint approval records a review decision; it does not execute code or activate a real autonomous subsystem.

### Website

Open `website/index.html` locally, or enable GitHub Pages in the repository settings to publish it. The website is a frontend demonstration; its Forge creates browser-local draft blueprints only.

## Advanced AI backend

A separate FastAPI backend includes:
- A provider-independent OpenAI-compatible Chat Completions adapter
- One central GAIA coordinator and nine specialist perspectives
- SQLite/PostgreSQL conversation history through SQLAlchemy
- Separate, explicitly saved long-term memory facts
- A persistent, exact-argument, single-use action approval foundation
- Optional PostgreSQL storage via `GAIA_DATABASE_URL`
- A read-only website backend health check with no embedded API secret
- Email/password registration, login, logout, and expiring account sessions
- Per-account conversation and saved-memory ownership checks
- Persistent database-backed limits for registration, login, and per-account AI requests
- Backend-only provider credentials
- Account bearer sessions for chat and private memory endpoints; optional shared token is development-only
- Automated tests for API routes, specialist routing, SQLite persistence, policy decisions, and provider failures

The specialists are selectable prompt perspectives within one configured model; they are not separate model instances or autonomous agents. The action-policy module is groundwork only: no external action handlers or unrestricted device controls are enabled.

### Run locally

Install dependencies, copy `.env.example` to a private `.env`, and configure `GAIA_API_KEY`, `GAIA_MODEL`, and `GAIA_RATE_LIMIT_SECRET` (at least 32 random bytes). The legacy `GAIA_API_TOKEN` is only needed if you deliberately enable `GAIA_ALLOW_SHARED_TOKEN=true` for private development. Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start the backend on localhost:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `website/access.html` for the account-first access preview. See [ACCOUNT_AND_PERMISSIONS.md](docs/ACCOUNT_AND_PERMISSIONS.md) for the onboarding, memory, and device-permission boundaries. See [ARCHITECTURE.md](ARCHITECTURE.md) for setup, API routes, tests, and security boundaries. See [ASSISTANT_FOUNDATIONS.md](docs/ASSISTANT_FOUNDATIONS.md) for the memory and action-policy design, and [USER_AUTHENTICATION.md](docs/USER_AUTHENTICATION.md) for the per-user security implementation plan.

The backend applies database-backed fixed-window limits to registration, login, and per-account chat. Counters store HMAC digests rather than raw email addresses or account IDs; the same private `GAIA_RATE_LIMIT_SECRET` and shared database must be used by every backend instance. Per-IP limits are not enabled until trusted reverse-proxy handling is explicitly configured. The provider adapter is tested with mocked responses, but a live provider request has **not** been verified. PostgreSQL support is implemented but no hosted database is provisioned or backup/restore tested. Conversation and saved-fact storage now support owner filters, and legacy rows with no owner are hidden by default. Email/password account routes are now wired to the API, and the new `website/access.html` screen can sign in, create an account, and manage explicit saved facts. Its session token is held in page memory rather than persistent browser storage. Google/GitHub OAuth is not implemented yet; those buttons are intentionally disabled. The web preview can request browser notifications only after a click; native phone-call and SMS permissions are not available in a website. Authentication still needs trusted per-IP abuse controls, refresh-token rotation, email verification/recovery, and a security review before public access. The backend is not deployed and is not ready for public multi-user access. Do not put real credentials in GitHub, the Android app, or browser code.

### Hosting preparation (staging only)

A Render Python/FastAPI staging blueprint is in [render.yaml](render.yaml). Read [the Render deployment plan](docs/RENDER_DEPLOYMENT.md) before using it: configure an external durable PostgreSQL database through `GAIA_DATABASE_URL`; the default SQLite file on Render Free is ephemeral. The [GAIA wake-up UX plan](docs/WAKEUP_UX.md) specifies an honest elapsed-time indicator while the backend wakes; it does not use a fake 15-minute countdown.

**Public release target: V19.** This staging setup is not a public release.

## Android setup

See [ANDROID_SETUP.md](ANDROID_SETUP.md) for phone instructions using Pydroid 3.

## Project structure

```
app.py
main.py
gaia/
  storage.py
  core.py
  forge.py
  memory.py
  ai/
    engine.py
    provider.py
    memory.py
    specialists.py
  assistant/
    auth.py
    memory.py
    policy.py
backend/
  main.py
data/
  subsystems.json
website/
  index.html
  styles.css
  app.js
tests/
  test_api.py
  test_auth.py
  test_storage.py
  test_assistant_api.py
  test_assistant_foundations.py
  test_core.py
  test_forge.py
  test_memory.py
  test_provider.py
  test_specialists.py
```
