# GAIA Per-User Authentication

## Implemented development foundation

- Email/password registration and login HTTP routes.
- Password hashes use scrypt; plaintext passwords are not stored.
- Opaque random bearer sessions are stored as SHA-256 token hashes.
- Sessions expire after one hour and can be revoked on logout.
- Protected chat, conversation, and memory routes resolve the session to an
  immutable account user ID.
- Conversation and explicit-memory database operations filter by owner ID.
- The legacy shared bearer token is disabled unless
  `GAIA_ALLOW_SHARED_TOKEN=true` is explicitly set.
- The access preview keeps the session token in page memory rather than
  persistent browser storage.
- Persistent fixed-window counters protect registration, login, and per-account
  chat. Only HMAC digests are stored, not raw email addresses or account IDs.
- Account/chat endpoints fail closed with HTTP 503 if
  `GAIA_RATE_LIMIT_SECRET` is missing or is still a placeholder.

Routes: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`,
and `POST /auth/logout`.

## Still required before public multi-user deployment

1. Trusted per-IP limits at the reverse-proxy boundary, plus CAPTCHA or other
   adaptive controls where justified. Do not trust arbitrary `X-Forwarded-For`
   values; configure and test the proxy trust boundary first.
2. Refresh-token rotation, revocation, and reuse detection.
3. Email verification and secure account recovery.
4. Google and GitHub OAuth with server-side secrets, exact redirect validation,
   state verification, and PKCE where supported. The current buttons are
   disabled and do not claim to authenticate.
5. A reviewed browser session design, including CSRF/XSS protections.
6. Account export/deletion, operational logging without secrets, abuse
   monitoring, HTTPS, secret rotation, and tested database backup/restore.
7. Security review and cross-account isolation testing against the deployed
   database.

## Data isolation

Every new conversation and saved fact is scoped to the authenticated user ID.
All list/read/write/delete operations include that owner ID. A guessed record
ID from another account must return the same not-found result as an unknown
record. Legacy rows with NULL owner IDs remain hidden; they are not assigned
to the first account automatically.

## Development-only compatibility

The shared token is off by default. If a private developer needs it temporarily,
set `GAIA_ALLOW_SHARED_TOKEN=true` on the backend. Never embed the shared token
in website JavaScript, a mobile app, or a distributed client.

## Current rate-limit policy (private development)

- Registration: 20 requests per hour globally and 5 per hour per normalized
  email address.
- Login: 120 requests per minute globally and 10 per 15 minutes per normalized
  email address.
- Chat: 30 requests per minute and 200 per day per account.
- Rejections return HTTP 429 with a `Retry-After` header.
- Counters use atomic SQLite/PostgreSQL upserts and are shared only when all
  backend instances use the same durable database and the same private
  `GAIA_RATE_LIMIT_SECRET` (at least 32 random bytes).
- No client IP is currently used. This avoids trusting spoofable forwarding
  headers or accidentally treating every visitor behind an unconfigured proxy
  as one person. Per-IP enforcement is still required before public access.
- The shared development token maps all callers to one development owner and
  therefore one chat bucket; it remains disabled unless explicitly enabled.

This is an initial abuse-control layer, not a complete public-service defense.
Do not expose account registration publicly until trusted per-IP controls,
refresh/recovery, OAuth decisions, operational monitoring, and the remaining
security review are complete. PostgreSQL rate-limit behavior still needs a
live integration test against the selected durable database.
