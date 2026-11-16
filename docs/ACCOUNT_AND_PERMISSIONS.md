# GAIA Accounts, Memory, and Device Permissions

## Account entry

The new access preview is `website/access.html`. It offers email/password
registration and sign-in. The API provides:

- `POST /auth/register` — create an account and issue a one-hour session.
- `POST /auth/login` — verify credentials and issue a session.
- `GET /auth/me` — inspect the account represented by a valid session.
- `POST /auth/logout` — revoke the current session.

Passwords are hashed with scrypt; plaintext passwords are never stored.
Session tokens are opaque random values; only SHA-256 hashes are stored in
the database. The browser access preview keeps the returned bearer token in
JavaScript memory only, not localStorage. Reloading the page requires signing
in again; sessions expire after one hour.

The legacy shared API token is rejected unless
`GAIA_ALLOW_SHARED_TOKEN=true` is explicitly configured. Keep this false for
account-based testing.

## Provider sign-in

Google and GitHub buttons are displayed but disabled. OAuth is not implemented.
Before enabling either provider, GAIA needs registered OAuth applications,
server-side client secrets, exact redirect URI validation, one-time state
verification, PKCE where supported, account-linking rules, and callback tests.
Never place OAuth client secrets in website files or GitHub commits.

## Memory controls

Conversation transcripts and long-term facts are separate. Each account's
records are filtered by its immutable user ID. The access page can list,
create, and delete explicit memory facts. Saving is a user action; GAIA does
not silently promote every chat message into long-term memory. Deletion
requires a confirmation request and only affects the owning account's fact.

The existing credential-shaped text filter is a basic guardrail, not a
complete secret detector. Do not save passwords, API keys, recovery codes,
or other credentials.

## Device permissions

The web preview can request browser notifications only after the user presses
the permission button. It does not request microphone, phone, or SMS access.

Calling and SMS are not implemented. A future Android app must explain each
capability separately, request Android permissions only when the user enables
that feature, and show the destination/message before any call or message
action. Permission must never authorize unattended or automatic contact.
Notifications, calling, and texting must remain optional; core GAIA use should
not require them.

## Not production-ready

This milestone is a private development foundation, not a public account
service. Before deployment to real users, GAIA still needs persistent
registration/login rate limits, refresh-token rotation and reuse detection,
email verification and account recovery, account deletion/export, CSRF/XSS
review for the final session design, abuse monitoring, backup/restore tests,
and a full security review. OAuth is not active. Do not deploy this
registration endpoint publicly until those controls are implemented and
reviewed.
