from __future__ import annotations

import pytest
from sqlalchemy import text

from gaia.assistant.rate_limit import (
    PersistentRateLimiter,
    RateLimitConfigurationError,
)
from gaia.storage import create_database_engine


SECRET = "test-rate-limit-secret-" + ("x" * 32)


def test_fixed_window_limit_is_atomic_and_shared_between_instances(tmp_path):
    engine = create_database_engine(tmp_path / "rate-limits.sqlite3")
    first_worker = PersistentRateLimiter(engine=engine)
    second_worker = PersistentRateLimiter(engine=engine)

    first = first_worker.consume(
        "auth:login:email", "Pilot@Example.com",
        limit=2, window_seconds=60, secret=SECRET, now=1_700_000_000,
    )
    second = second_worker.consume(
        "auth:login:email", "Pilot@Example.com",
        limit=2, window_seconds=60, secret=SECRET, now=1_700_000_001,
    )
    blocked = first_worker.consume(
        "auth:login:email", "Pilot@Example.com",
        limit=2, window_seconds=60, secret=SECRET, now=1_700_000_002,
    )

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after == 58

    # A new fixed window admits requests again.
    next_window = second_worker.consume(
        "auth:login:email", "Pilot@Example.com",
        limit=2, window_seconds=60, secret=SECRET, now=1_700_000_060,
    )
    assert next_window.allowed is True
    engine.dispose()


def test_rate_limit_keys_are_hmac_digests_not_raw_identifiers(tmp_path):
    engine = create_database_engine(tmp_path / "privacy.sqlite3")
    limiter = PersistentRateLimiter(engine=engine)
    email = "private-person@example.com"

    limiter.consume(
        "auth:register:email", email,
        limit=5, window_seconds=3600, secret=SECRET, now=1_700_000_000,
    )

    with engine.connect() as db:
        rows = db.execute(
            text("SELECT bucket_key FROM rate_limit_buckets")
        ).scalars().all()

    assert len(rows) == 1
    assert len(rows[0]) == 64
    assert email not in rows[0]
    assert all(char in "0123456789abcdef" for char in rows[0])
    engine.dispose()


def test_different_accounts_and_scopes_have_separate_buckets(tmp_path):
    engine = create_database_engine(tmp_path / "scopes.sqlite3")
    limiter = PersistentRateLimiter(engine=engine)

    assert limiter.consume(
        "chat:account:minute", "account-a",
        limit=1, window_seconds=60, secret=SECRET, now=1000,
    ).allowed
    assert limiter.consume(
        "chat:account:minute", "account-b",
        limit=1, window_seconds=60, secret=SECRET, now=1000,
    ).allowed
    assert limiter.consume(
        "auth:login:email", "account-a",
        limit=1, window_seconds=60, secret=SECRET, now=1000,
    ).allowed
    engine.dispose()


def test_rate_limit_requires_a_real_private_secret(tmp_path):
    engine = create_database_engine(tmp_path / "secret.sqlite3")
    limiter = PersistentRateLimiter(engine=engine)

    with pytest.raises(RateLimitConfigurationError):
        limiter.consume(
            "auth:login:email", "pilot@example.com",
            limit=5, window_seconds=60, secret="short",
        )
    with pytest.raises(RateLimitConfigurationError):
        limiter.consume(
            "auth:login:email", "pilot@example.com",
            limit=5, window_seconds=60,
            secret="put_a_real_secret_here_" + ("x" * 32),
        )
    engine.dispose()


@pytest.mark.parametrize(
    "limit,window",
    [(0, 60), (5, 0), (-1, 60), (5, 31_536_001)],
)
def test_rate_limit_rejects_invalid_bounds(tmp_path, limit, window):
    engine = create_database_engine(tmp_path / "bounds.sqlite3")
    limiter = PersistentRateLimiter(engine=engine)
    with pytest.raises(ValueError):
        limiter.consume(
            "auth:login:email", "pilot@example.com",
            limit=limit, window_seconds=window, secret=SECRET,
        )
    engine.dispose()
