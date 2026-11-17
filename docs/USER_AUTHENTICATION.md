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

Routes: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`,
and `POST /auth/logout`.

## Still required before public multi-user deployment

1. Persistent rate limits for registration, login, and expensive AI requests.
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

This implementation is not production-ready. In particular, do not expose
account registration publicly until persistent rate limiting, recovery,
OAuth decisions, and the remaining controls above are complete.
