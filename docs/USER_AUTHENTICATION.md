# GAIA Per-User Authentication — Implementation Plan

## Current security state

The API still uses one shared development bearer token (`GAIA_API_TOKEN`).
That is suitable only for private single-owner testing. It must never be
embedded in the website JavaScript, an Android APK, or another distributed
client. The current conversation and fact tables are not scoped to accounts.

This document is a design checkpoint, not a claim that account authentication
has been implemented.

## Required design

1. **Account identity:** each account receives a random immutable user ID.
   Email addresses, if used, must be verified before recovery or account
   security actions are enabled.
2. **Password storage:** use a maintained password-hashing library with
   Argon2id (or another currently recommended memory-hard password hash).
   Never store plaintext passwords or reversible password encryption.
3. **Sessions:** issue short-lived signed access tokens and rotateable,
   revocable refresh sessions. Store only hashes of refresh tokens. Enforce
   expiry, logout, rotation, and reuse detection.
4. **Data isolation:** every conversation and memory fact must carry an
   owner ID. Every list/read/write/delete query must include the authenticated
   owner ID. A guessed conversation or fact ID belonging to another account
   must return the same not-found response as an unknown ID.
5. **Legacy data:** existing unowned SQLite records must not silently become
   visible to every new account. Migration must require an explicit
   single-owner import decision or leave old rows inaccessible.
6. **Abuse controls:** rate-limit registration, login, refresh, and expensive
   model requests. Use generic login errors, bounded request sizes, and
   server-side logging that never records passwords or bearer tokens.
7. **Browser security:** use secure, HttpOnly, SameSite cookies when the
   deployment architecture supports them, with CSRF protection for
   cookie-authenticated state changes. If bearer tokens are used, keep them
   short-lived and out of persistent browser storage.
8. **Operations:** require HTTPS, secret rotation, backup/restore tests, and
   a documented account deletion/export process before real user data.

## Implementation order

- Add user and session tables to the durable database layer.
- Add registration/login/logout/refresh with strict validation and tests.
- Add owner IDs and ownership filters to conversation history and explicit
  long-term memory, including cross-account isolation tests.
- Switch protected routes to authenticated user identity.
- Remove shared-token authentication from the production path; retain it
  only behind an explicit development-only setting if still needed.
- Connect the website sign-in flow only after all data routes enforce owner
  isolation.

## Not implemented yet

No account registration, password hashing, refresh-token rotation, user
ownership columns, per-user route filtering, login rate limiting, or
production session management has been implemented by this checkpoint.
