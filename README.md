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

The request router is currently rule-based. A real AI model/API is **not connected yet**. Blueprint approval records a review decision; it does not execute code or activate a real autonomous subsystem.

### Website

Open `website/index.html` locally, or enable GitHub Pages in the repository settings to publish it. The website is a frontend demonstration; its Forge creates browser-local draft blueprints only.

## Android setup

See [ANDROID_SETUP.md](ANDROID_SETUP.md) for phone instructions using Pydroid 3.

## Architecture and safety

- GAIA coordinates specialized subsystems.
- HEPHAESTUS drafts declarative JSON blueprints.
- GAIA reviews proposals before they can be considered for future registration.
- Generated code is never executed.
- API keys must stay out of GitHub and should be stored only in a secure local/backend configuration.

## Project structure

```
app.py
main.py
gaia/
  __init__.py
  core.py
  forge.py
  memory.py
data/
  subsystems.json
  # memory.json and blueprints.json are created locally on first run
website/
  index.html
  styles.css
  app.js
ANDROID_SETUP.md
README.md
requirements.txt
```


## Advanced AI backend (foundation)

A separate FastAPI backend now provides a real model connection through an OpenAI-compatible API adapter, specialist prompts, and SQLite conversation history. See [ARCHITECTURE.md](ARCHITECTURE.md). The backend is not deployed or connected to a live model yet; configure `GAIA_API_KEY`, `GAIA_BASE_URL`, and `GAIA_MODEL` privately on the backend. Never put a real key in GitHub or the Android app.
