# GAIA — Advanced Intelligence Architecture

## Goal

Build an AI platform with one central model-driven coordinator, nine specialist perspectives, persistent conversation memory, and a permission-controlled tool layer.

## Current architecture

- **API layer:** FastAPI exposes health and chat endpoints.
- **Central engine:** `gaia.ai.engine.GaiaAI` composes the central GAIA instruction with one specialist instruction.
- **Specialists:** APOLLO, ARTEMIS, HEPHAESTUS, MINERVA, POSEIDON, DEMETER, AETHER, ELEUTHIA, and HADES are defined as specialist roles. The authenticated chat API accepts an optional explicit specialist selection; otherwise it uses deterministic routing.
- **Model adapter:** OpenAI-compatible Chat Completions API. Configure the endpoint and model through environment variables.
- **Memory:** SQLite conversation history, separated by conversation ID.
- **Credential handling:** the backend loads a private local `.env` for development or receives secrets from its deployment host. The Android/browser client must never contain provider credentials.
- **API access:** `POST /chat` requires a backend bearer token (`GAIA_API_TOKEN`) of at least 32 characters. Comparisons use constant-time comparison. The token is never returned by the health endpoint.

## Important current limitations

- This is one model call with a selected specialist prompt, not nine independent models or autonomous agents.
- The provider adapter is tested with mocked responses, but no live provider request has been verified.
- No external tools are enabled yet. The model cannot execute code, browse, send messages, or control devices.
- Conversation history is stored locally in SQLite on the backend. It is not semantic/vector memory yet.
- The API has not been deployed. Authentication here is a simple shared development token, not production user authentication. Add per-user identity, rate limits, abuse protection, TLS termination, and operational monitoring before public hosting.

## Run locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and replace the placeholders privately:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use the generated random value for `GAIA_API_TOKEN` in your private `.env`. Set `GAIA_API_KEY` and `GAIA_MODEL` there too; optionally change `GAIA_BASE_URL`. Remote provider URLs must use HTTPS; plain HTTP is accepted only for localhost development. `python-dotenv` loads `.env` for the backend process. Never commit `.env`, paste a key into source code, or place a provider key in the Android app.

Start the service on the local machine only:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Check `GET /health`. It reports `setup_required` until both the provider and API access token are configured. Send `POST /chat` with JSON containing `message` and optionally `conversation_id`, plus an `Authorization: Bearer <GAIA_API_TOKEN>` header. Message length is capped at 12,000 characters; conversation IDs are limited to 100 safe ASCII characters; unknown request fields are rejected.

Run automated tests:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Security boundaries

- Keep `.env` out of Git; only the placeholder `.env.example` is tracked.
- Keep provider and backend access tokens on the server. A shared token embedded in a distributed mobile app is not a secure production authentication design.
- The local server binds to `127.0.0.1` by default. Do not expose it publicly as-is.
- The provider adapter validates remote HTTPS URLs, rejects embedded URL credentials, bounds timeouts, and caps response size.
- The API validates request size and conversation ID syntax. SQLite queries use parameters.
- Generated code is not executed; HEPHAESTUS currently produces design guidance only.

## Next milestones

1. Verify one real provider request using a privately configured test key.
2. Add explicit memory controls: inspect, delete, and opt-in facts.
3. Add a typed tool registry with per-tool permissions and user confirmation for consequential actions.
4. Add a mobile-friendly client that talks only to an authenticated GAIA backend.
5. Design per-user authentication, rate limits, deployment configuration, and abuse protection before public hosting.
