# GAIA Persistent Rate Limits

## Purpose

This is an initial server-side abuse-control layer for private development. It
is not a declaration that account registration is safe for public use.

## Current fixed-window defaults

| Endpoint | Scope | Limit |
|---|---|---:|
| `POST /auth/register` | All registrations | 20 per hour |
| `POST /auth/register` | Normalized email | 5 per hour |
| `POST /auth/login` | All login attempts | 120 per minute |
| `POST /auth/login` | Normalized email | 10 per 15 minutes |
| `POST /chat` | Account | 30 per minute |
| `POST /chat` | Account | 200 per day |

Limits are enforced before password hashing or provider calls. Rejected requests
receive HTTP 429 and a `Retry-After` header. Missing or placeholder rate-limit
configuration fails closed with HTTP 503 on registration, login, and chat.

## Storage and privacy

- Counters are stored in `rate_limit_buckets` in the configured SQLAlchemy
  database.
- SQLite and PostgreSQL use atomic upsert operations, so workers sharing the
  same database and secret share counters.
- The database stores a keyed HMAC-SHA-256 digest of the scope and identifier;
  it does not store the raw email address or account ID in rate-limit rows.
- The private `GAIA_RATE_LIMIT_SECRET` must contain at least 32 random bytes
  and must be identical across all backend instances. Rotating it changes the
  HMAC bucket namespace, so coordinate rotation during a quiet maintenance
  window rather than assuming existing counters will carry over.
- Expired buckets are cleaned during subsequent requests; rows are retained
  only through the end of their fixed window.

Generate a local development value privately, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Do not commit the generated value. The Render blueprint requests a generated
secret, but this file does not prove that a service has been deployed.

## Verification

- The default test suite exercises SQLite behavior.
- GitHub Actions now starts an isolated PostgreSQL 16 service and runs
  `tests/test_rate_limit_postgres.py` separately.
- The PostgreSQL integration test creates multiple limiter instances to model
  separate workers, submits concurrent requests for one account/window, and
  verifies that exactly the configured number are admitted and that a newly
  created worker observes the persisted counter.
- To run the integration test locally, set `GAIA_POSTGRES_TEST_URL` to a
  disposable PostgreSQL test database URL. The test uses that URL through
  GAIA's normal `GAIA_DATABASE_URL` engine configuration. It does not drop
  tables or reset the database; use a dedicated disposable database.
- Passing this CI test verifies the PostgreSQL 16 rate-limit path under this
  test workload. It does not verify hosted-database backups, failover,
  connection limits, or the eventual production database provider.

## Important limits

- Per-IP enforcement is not enabled yet. GAIA deliberately does not trust
  arbitrary `X-Forwarded-For` values. Before adding IP limits, configure
  the exact trusted reverse-proxy boundary and test it; otherwise all visitors
  behind a proxy may appear as one address or attackers may spoof identities.
- Global registration/login buckets are coarse emergency caps, not a
  substitute for per-IP limits, email verification, CAPTCHA/adaptive controls,
  monitoring, or an operational abuse-response process.
- The optional shared development token maps callers to one fixed owner and
  one chat bucket. It remains disabled by default.
- SQLite on an ephemeral host is not durable or shared across independent
  instances. Configure a durable PostgreSQL database before relying on limits
  across restarts or replicas.
- Fixed windows can allow a burst at a window boundary. Consider a token-bucket
  or sliding-window policy after observing staging traffic.

## Release gate

Do not expose account registration publicly until trusted per-IP enforcement,
database durability, refresh-token controls, recovery, monitoring, and a full
security review are complete. Public release remains forbidden before V19.
