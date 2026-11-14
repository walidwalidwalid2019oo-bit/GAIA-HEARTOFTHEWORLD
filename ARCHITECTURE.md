# GAIA — Advanced Intelligence Architecture

## Goal

Build an advanced AI platform with one central model-driven coordinator, six specialist perspectives, persistent conversation memory, and a permission-controlled tool layer.

## Current architecture

- **API layer:** FastAPI exposes health and chat endpoints.
- **Central engine:** `gaia.ai.engine.GaiaAI` composes the central GAIA instruction with one specialist instruction.
- **Specialists:** APOLLO, ARTEMIS, HEPHAESTUS, MINERVA, POSEIDON, and DEMETER are defined as distinct roles and routing hints.
- **Model adapter:** OpenAI-compatible Chat Completions API. Configure provider URL and model through environment variables.
- **Memory:** SQLite conversation history, separated by conversation ID.
- **Security:** API key is read only by the backend from `GAIA_API_KEY`. The mobile client must call the backend and must never contain provider credentials.

## Important current limitations

- This is one model call with a selected specialist prompt, not six independent models or autonomous agents.
- No external tools are enabled yet. The model cannot execute code, browse, send messages, or control devices.
- Conversation history is stored locally in SQLite on the backend. It is not semantic/vector memory yet.
- The API has not been deployed or tested against a live provider. A valid provider key and model ID are required.

## Run locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Set environment variables in the private backend environment (do not commit secrets):

- `GAIA_API_KEY`
- `GAIA_BASE_URL` (defaults to Groq's OpenAI-compatible endpoint)
- `GAIA_MODEL`

Start the service:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Check `GET /health`, then send `POST /chat` with JSON containing `message` and optionally `conversation_id`.

## Next milestones

1. Add tests and provider-specific adapters (Gemini, OpenAI, Groq, OpenRouter).
2. Add explicit memory controls: inspect, delete, and opt-in facts.
3. Add a typed tool registry with per-tool permissions and user confirmation for consequential actions.
4. Add a mobile-friendly client that talks only to the GAIA backend.
5. Add deployment configuration, rate limits, authentication, and abuse protection before public hosting.
