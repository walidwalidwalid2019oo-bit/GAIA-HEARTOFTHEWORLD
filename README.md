# GAIA — Heart of the World

An original, modular AI ecosystem prototype built around a central coordinator and specialized subsystems.

> Independent project. The website and app use original interface elements and symbolic motifs; no ripped Horizon game assets are included.

## Current builds

### Android-friendly Python app (prototype)

Run with Python 3.10+:

\`\`\`bash
python app.py
\`\`\`

The app currently includes:
- GAIA command-center menu
- Seven core subsystem profiles
- Registry status display
- Local JSON memory vault for notes and activity
- HEPHAESTUS blueprint drafting
- GAIA approval/rejection queue

The Android request router is rule-based. A real AI model/API is **not connected to this local app**. Blueprint approval records a review decision; it does not execute code or activate a real autonomous subsystem.

### Website

Open \`website/index.html\` locally, or enable GitHub Pages in the repository settings to publish it. The website is a frontend demonstration; its Forge creates browser-local draft blueprints only.

## Android setup

See [ANDROID_SETUP.md](ANDROID_SETUP.md) for phone instructions using Pydroid 3.

## Architecture and safety

- GAIA coordinates specialized subsystems.
- HEPHAESTUS drafts declarative JSON blueprints.
- GAIA reviews proposals before they can be considered for future registration.
- Generated code is never executed.
- API keys stay on the private backend, never in GitHub or the Android app.

## Project structure

\`\`\`
app.py
main.py
gaia/
  __init__.py
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
ANDROID_SETUP.md
README.md
requirements.txt
requirements-dev.txt
\`\`\`

## Advanced AI backend foundation

A separate FastAPI backend now includes an OpenAI-compatible Chat Completions adapter, specialist prompts, and SQLite conversation history. It can be configured with \`GAIA_API_KEY\`, \`GAIA_BASE_URL\`, and \`GAIA_MODEL\`; see [ARCHITECTURE.md](ARCHITECTURE.md). Local development can use a private \`.env\` copied from \`.env.example\`.

The provider adapter has mocked unit tests, but a live provider request has **not** been verified. The backend is not deployed and is not yet protected for public multi-user access. Do not put a real key in GitHub, the Android app, or browser code.
