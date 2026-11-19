"""PostgreSQL integration tests for shared, atomic GAIA rate limits.

The CI workflow supplies an isolated PostgreSQL service. Local runs skip this
module unless GAIA_POSTGRES_TEST_URL points to a disposable test database.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from gaia.assistant.rate_limit import PersistentRateLimiter
from gaia.storage import create_database_engine


POSTGRES_URL = os.getenv("GAIA_POSTGRES_TEST_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="Set GAIA_POSTGRES_TEST_URL to run PostgreSQL integration tests.",
)
TEST_SECRET = "gaia-postgres-integration-secret-" + ("x" * 32)


def test_postgres_rate_limit_is_atomic_across_worker_instances(monkeypatch):
    # Exercise GAIA's actual URL normalization and SQLAlchemy engine factory.
    monkeypatch.setenv("GAIA_DATABASE_URL", POSTGRES_URL)
    engine = create_database_engine()
    identifier = f"concurrency-test-{uuid4().hex}"
    now = 1_700_000_003
    limit = 4
    window_seconds = 60

    try:
        # Separate limiter objects model independent application workers sharing
        # one PostgreSQL database.
        workers = [PersistentRateLimiter(engine=engine) for _ in range(4)]

        def consume(index: int):
            return workers[index % len(workers)].consume(
                "chat:account:minute",
                identifier,
                limit=limit,
                window_seconds=window_seconds,
                secret=TEST_SECRET,
                now=now,
            )

        with ThreadPoolExecutor(max_workers=12) as pool:
            decisions = list(pool.map(consume, range(24)))

        allowed = [decision for decision in decisions if decision.allowed]
        rejected = [decision for decision in decisions if not decision.allowed]

        assert len(allowed) == limit
        assert len(rejected) == 24 - limit
        assert sorted(decision.remaining for decision in allowed) == [0, 1, 2, 3]
        assert all(1 <= decision.retry_after <= window_seconds for decision in rejected)

        # A newly constructed worker must observe the same persisted counter.
        another_worker = PersistentRateLimiter(engine=engine)
        persisted = another_worker.consume(
            "chat:account:minute",
            identifier,
            limit=limit,
            window_seconds=window_seconds,
            secret=TEST_SECRET,
            now=now,
        )
        assert persisted.allowed is False
    finally:
        engine.dispose()
