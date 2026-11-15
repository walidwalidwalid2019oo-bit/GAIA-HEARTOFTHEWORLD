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
- Internal account/password/session primitives (not yet exposed to clients)
- Backend-only provider credentials
- A required shared bearer token for chat and private memory endpoints
- Automated tests for API routes, specialist routing, SQLite persistence, policy decisions, and provider failures

The specialists are selectable prompt perspectives within one configured model; they are not separate model instances or autonomous agents. The action-policy module is groundwork only: no external action handlers or unrestricted device controls are enabled.

### Run locally

Install dependencies, copy `.env.example` to a private `.env`, and configure `GAIA_API_KEY`, `GAIA_MODEL`, and a random `GAIA_API_TOKEN` (at least 32 characters). Generate a token with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start the backend on localhost:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for setup, API routes, tests, and security boundaries. See [ASSISTANT_FOUNDATIONS.md](docs/ASSISTANT_FOUNDATIONS.md) for the memory and action-policy design, and [USER_AUTHENTICATION.md](docs/USER_AUTHENTICATION.md) for the per-user security implementation plan.

The provider adapter is tested with mocked responses, but a live provider request has **not** been verified. PostgreSQL support is implemented but no hosted database is provisioned or backup/restore tested. The website health check does not yet provide login or live chat. Internal password/session primitives exist, but account routes and per-user data isolation are still pending. The backend is not deployed and is not ready for public multi-user access. Do not put real credentials in GitHub, the Android app, or browser code.

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
  core.py
  forge.py
  memory.py
  ai/
    engine.py
    provider.py
    memory.py
    specialists.py
  assistant/
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
  test_assistant_api.py
  test_assistant_foundations.py
  test_core.py
  test_forge.py
  test_memory.py
  test_provider.py
  test_specialists.py
```
