# GAIA — Advanced Intelligence Architecture

## Goal

Build a private AI platform around one central model-driven coordinator, nine specialist perspectives, owner-scoped memory, and permission-controlled capabilities.

## Current architecture

- **API layer:** FastAPI exposes liveness/readiness, account sessions, chat, conversation history, and explicit long-term-memory routes.
- **Central engine:** `gaia.ai.engine.GaiaAI` composes the central GAIA instruction with one specialist instruction.
- **Specialists:** APOLLO, ARTEMIS, HEPHAESTUS, MINERVA, POSEIDON, DEMETER, AETHER, ELEUTHIA, and HADES are prompt perspectives selected within one configured model call. They are not independent autonomous agents.
- **Model adapter:** OpenAI-compatible Chat Completions API. Configure the provider endpoint, model, and key through private backend environment variables.
- **Database layer:** SQLAlchemy supports local SQLite and externally managed PostgreSQL through `GAIA_DATABASE_URL`; SQLite is the local fallback. Conversation history, explicit facts, account sessions, action approvals, and rate-limit buckets use the shared engine. Existing SQLite data is not automatically migrated.
- **Conversation memory:** persistent chat history scoped to an immutable account owner ID.
- **Long-term memory:** `gaia.assistant.memory.LongTermMemory` stores facts explicitly submitted by the user. Facts can be listed by category and individually deleted. Credential-shaped text is rejected by a basic guardrail, not a complete secret detector.
- **Authentication:** `gaia.assistant.auth.UserAuth` supports email/password registration, login, current-account lookup, and logout. Passwords use scrypt hashes; opaque one-hour bearer sessions are stored as SHA-256 token hashes and can be revoked.
- **Rate limiting:** `gaia.assistant.rate_limit.PersistentRateLimiter` uses atomic SQLite/PostgreSQL fixed-window upserts. Registration and login have global and normalized-email limits; chat has per-account minute and daily limits. Only HMAC digests are stored. The same private `GAIA_RATE_LIMIT_SECRET` and database must be shared by all backend instances.
- **Action policy foundation:** `gaia.assistant.policy` defines safe, monitor, ask, and block decisions. Its `ApprovalLedger` stores short-lived approvals against exact action arguments and permits one-time consumption. It is not connected to an action executor.
- **Credential handling:** provider credentials and the rate-limit HMAC secret stay on the backend. Never put provider keys or shared backend secrets in website code, an APK, or GitHub.

## API routes

- `GET /health/live` — lightweight process-liveness check; does not depend on provider credentials.
- `GET /health` — readiness information for provider and rate-limit configuration plus a non-secret database-backend label.
- `POST /auth/register` — create an email/password account and issue a session.
- `POST /auth/login` — verify credentials and issue a session.
- `GET /auth/me` — inspect the account represented by a valid session.
- `POST /auth/logout` — revoke the current session.
- `POST /chat` — send a message, optionally selecting a conversation ID and specialist.
- `GET /conversations?limit=50` — list recent conversation summaries (limit 1–100).
- `GET /conversations/{conversation_id}` — inspect one owner's saved message history.
- `DELETE /conversations/{conversation_id}` — permanently delete one owner's conversation.
- `GET /memory/facts?category=projects&limit=100` — list explicitly saved facts.
- `POST /memory/facts` — save one explicitly submitted fact.
- `DELETE /memory/facts/{fact_id}` — delete one owner's fact; request body must include `{"confirm":true}`.

## Authentication, ownership, and rate limits

Protected chat, conversation, and memory routes resolve the account session to an immutable owner ID. All list/read/write/delete operations include that owner ID. A guessed record ID belonging to another account returns the same not-found result as an unknown record. Legacy rows with NULL owner IDs remain unowned and hidden; they are not automatically reassigned.

The legacy shared bearer token is disabled unless `GAIA_ALLOW_SHARED_TOKEN=true` is explicitly set for private development. When enabled, it maps every caller to one shared development owner and one chat rate-limit bucket. Never embed it in a distributed client.

Current private-development fixed-window defaults:

| Endpoint | Scope | Limit |
|---|---|---:|
| Registration | Global | 20 per hour |
| Registration | Normalized email | 5 per hour |
| Login | Global | 120 per minute |
| Login | Normalized email | 10 per 15 minutes |
| Chat | Account | 30 per minute |
| Chat | Account | 200 per day |

Rate-limit rejections return HTTP 429 with `Retry-After`. Registration, login, and chat fail closed with HTTP 503 if `GAIA_RATE_LIMIT_SECRET` is missing or is still a placeholder.

Per-IP limits are not enabled yet. GAIA does not trust arbitrary `X-Forwarded-For` values; the trusted reverse-proxy boundary must be explicitly configured and tested before IP-based enforcement is added. Fixed windows can permit bursts at a window boundary. See `docs/RATE_LIMITING.md`.

## Important current limitations

- The specialist system is one model call with a selected prompt, not nine independent models or autonomous agents.
- The provider adapter is tested with mocked responses, but no live provider request has been verified.
- No external action handlers are registered. GAIA cannot execute code, browse, send messages, read email, or control devices.
- The action-risk and approval classes are policy primitives only; they are not connected to an action executor.
- Long-term memory is explicit and user-submitted. Automatic extraction and semantic/vector retrieval are not implemented.
- Per-IP/adaptive abuse controls, refresh-token rotation and reuse detection, email verification/recovery, account export/deletion, and full session/XSS/CSRF review remain incomplete.
- PostgreSQL support exists, but no hosted database is provisioned and PostgreSQL concurrency, backup/restore, and SQLite migration have not been verified.
- The website includes an account access screen and explicit memory controls plus a read-only backend health check. Real frontend chat is not connected yet; CORS is opt-in through exact `GAIA_CORS_ORIGINS` values.
- The Render configuration is a staging proposal only. No service has been deployed. SQLite on an ephemeral host is not durable or shared across independent instances.
- Public release is forbidden before V19. Private feature branches and draft PRs are development work, not release candidates.

## Run locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to a private `.env`. Configure `GAIA_API_KEY`, `GAIA_MODEL`, and a random `GAIA_RATE_LIMIT_SECRET` of at least 32 bytes. Generate a value privately:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Optionally set `GAIA_DATABASE_URL` to a private durable PostgreSQL URL. If it is absent, the backend uses the local SQLite file configured by `GAIA_DB_PATH`. Set `GAIA_BASE_URL` only if using a different OpenAI-compatible provider. The legacy `GAIA_API_TOKEN` is only needed when `GAIA_ALLOW_SHARED_TOKEN=true` is deliberately enabled for private development.

Start the backend on localhost:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Check `GET /health/live` and `GET /health`. The latter reports `setup_required` until the provider and rate-limit secret are configured. Register or log in through the account routes and send the returned session as `Authorization: Bearer <session>` for protected requests. Do not put provider credentials or a shared backend token in the browser or Android client.

Run automated tests:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Security boundaries

- Keep `.env` out of Git; only the placeholder `.env.example` is tracked.
- Keep provider and rate-limit secrets on the backend. A client-side key or shared token is not a secure production authentication design.
- The local server binds to `127.0.0.1` by default. Do not expose it publicly as-is.
- Remote provider URLs must use HTTPS; the provider adapter rejects embedded URL credentials, bounds timeouts, and caps response size.
- The API validates request size and conversation ID syntax. SQL statements use parameters.
- The credential-shaped memory filter is a guardrail, not a guarantee. Never save passwords, API keys, recovery codes, or other credentials.
- Deleting a conversation or long-term fact is destructive; the client should ask for confirmation before calling the delete route.
- Generated code is not executed; HEPHAESTUS currently produces design guidance only.
- No real provider key, account, hosted database, or Android release credential has been configured or exposed by this development work.

## Next milestones

1. Add trusted per-IP and adaptive abuse controls after reverse-proxy trust is configured.
2. Add refresh-token rotation, reuse detection, email verification, and secure account recovery.
3. Connect real frontend chat using account sessions and an honest wake-up/retry state.
4. Select and test durable PostgreSQL, including concurrency, backup/restore, and explicit SQLite migration.
5. Complete browser-session, Android Keystore, permission, and APK secret-scanning reviews.
6. Add a typed action registry with explicit capability grants and input schemas.
7. Keep all public release work blocked until the V19 security and product checklist passes.
