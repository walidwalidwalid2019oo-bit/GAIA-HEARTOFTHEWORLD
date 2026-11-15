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
- SQLite conversation history
- Backend-only provider credentials
- A required shared bearer token for the chat endpoint
- Automated tests for API routes, specialist routing, SQLite persistence, and provider failures

The specialists are selectable prompt perspectives within one configured model; they are not separate model instances or autonomous agents.

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

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full setup, request format, test command, and security boundaries.

The provider adapter is tested with mocked responses, but a live provider request has **not** been verified. The backend is not deployed and is not ready for public multi-user access. Do not put real credentials in GitHub, the Android app, or browser code.

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
  test_core.py
  test_forge.py
  test_memory.py
  test_provider.py
  test_specialists.py
```
