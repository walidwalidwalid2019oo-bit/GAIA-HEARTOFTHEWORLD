# GAIA — Advanced Intelligence Architecture

## Goal

Build an AI platform with one central model-driven coordinator, nine specialist perspectives, separate conversation and long-term memory, and a permission-controlled tool layer.

## Current architecture

- **API layer:** FastAPI exposes health, chat, authenticated conversation-memory endpoints, and explicit long-term memory endpoints.
- **Central engine:** `gaia.ai.engine.GaiaAI` composes the central GAIA instruction with one specialist instruction.
- **Specialists:** APOLLO, ARTEMIS, HEPHAESTUS, MINERVA, POSEIDON, DEMETER, AETHER, ELEUTHIA, and HADES are defined as specialist roles. The authenticated chat API accepts an optional explicit specialist selection; otherwise it uses deterministic routing.
- **Model adapter:** OpenAI-compatible Chat Completions API. Configure the endpoint and model through environment variables.
- **Database layer:** SQLAlchemy engine supports local SQLite and externally managed PostgreSQL through `GAIA_DATABASE_URL`; SQLite remains the local fallback. Conversation history, explicit facts, and action approvals use this shared engine. Existing SQLite data is not automatically migrated.
- **Conversation memory:** persistent chat history, separated by conversation ID.
- **Long-term memory:** `gaia.assistant.memory.LongTermMemory` stores facts explicitly submitted by the user in a separate database table. Facts can be listed by category and individually deleted. Credential-shaped text is rejected by a conservative pattern check.
- **Action policy foundation:** `gaia.assistant.policy` defines safe, monitor, ask, and block decisions. Its `ApprovalLedger` stores short-lived approvals against exact action arguments in the shared database and permits one-time consumption. BLOCK cannot be overridden by approval.
- **Credential handling:** the backend loads a private local `.env` for development or receives secrets from its deployment host. The Android/browser client must never contain provider credentials.
- **API access:** chat and private memory endpoints require a backend bearer token (`GAIA_API_TOKEN`) of at least 32 characters. Comparisons use constant-time comparison. The token is never returned by the health endpoint.

## API routes

- `GET /health/live` — lightweight process-liveness check; does not depend on AI provider credentials. Use this for the hosting platform's health check.
- `GET /health` — application readiness status for provider and backend-token configuration plus a non-secret database-backend label. The website can call this public read-only endpoint.
- `POST /chat` — send a message, optionally selecting a conversation ID and specialist.
- `GET /conversations?limit=50` — list recent conversation summaries (limit 1–100).
- `GET /conversations/{conversation_id}` — inspect the full saved message history for one conversation.
- `DELETE /conversations/{conversation_id}` — permanently delete one conversation's messages from the SQLite database.
- `GET /memory/facts?category=projects&limit=100` — list explicitly saved facts.
- `POST /memory/facts` — save one explicitly submitted fact, optionally categorized.
- `DELETE /memory/facts/{fact_id}` — delete one fact; request body must include `{"confirm":true}`.

All conversation and long-term-memory routes require the same bearer authentication as chat. Conversation IDs are restricted to a safe ASCII character set. These routes currently operate on the single backend database; they are not yet isolated by individual user accounts.

## Important current limitations

- This is one model call with a selected specialist prompt, not nine independent models or autonomous agents.
- The provider adapter is tested with mocked responses, but no live provider request has been verified.
- No external action handlers are registered yet. GAIA cannot execute code, browse, send messages, read email, or control devices.
- The action-risk and approval classes are policy primitives only; they are not yet connected to an action executor. A ticket is not evidence that an action ran.
- Long-term memory is explicit and user-submitted. GAIA does not automatically extract facts from chat, and semantic/vector retrieval is not implemented.
- The credential-text filter is a guardrail, not a guarantee. Users should never save passwords, API keys, recovery codes, or other credentials.
- The API has not been deployed. Authentication here is a simple shared development token, not production user authentication. Per-user accounts, session rotation, owner-scoped data isolation, and rate limits are not implemented. See `docs/USER_AUTHENTICATION.md`.
- PostgreSQL support is implemented but no hosted database is provisioned, configured, or backup/restore verified. Existing SQLite data is not automatically migrated.
- The website has a read-only backend health check only. It does not yet sign users in or send chat requests; CORS is opt-in through exact `GAIA_CORS_ORIGINS` values.

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
- Deleting a conversation or long-term fact is destructive; the client should ask for confirmation before calling the delete route.
- Generated code is not executed; HEPHAESTUS currently produces design guidance only.

## Next milestones

1. Add a typed action registry with explicit capability grants and input schemas.
2. Add a bounded task planner with saved steps, progress, cancellation, and evidence-based completion.
3. Connect read-only integrations first, such as user-selected documents or email summaries.
4. Connect write integrations only after exact-argument approvals are enforced by the executor.
5. Add opt-in scheduled routines with timezone handling, run history, and no permission escalation.
6. Add per-user authentication, rate limits, deployment configuration, and abuse protection before public hosting.
