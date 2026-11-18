"""Persistent, privacy-preserving fixed-window rate limits for GAIA APIs."""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from dataclasses import dataclass

from sqlalchemy import BigInteger, Column, Index, Integer, MetaData, String, Table, delete
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine


_SCOPE = re.compile(r"^[a-z][a-z0-9:_-]{0,63}$")


class RateLimitConfigurationError(RuntimeError):
    """Rate limiting cannot run safely because its secret/configuration is invalid."""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int


class PersistentRateLimiter:
    """Atomic fixed-window counters shared by workers using the same database.

    Only a keyed HMAC digest of the scope and identifier is stored. The HMAC
    secret must be supplied from private server configuration and shared by all
    backend instances. SQLite and PostgreSQL use atomic UPSERT/RETURNING.
    """

    def __init__(self, *, engine: Engine) -> None:
        self.engine = engine
        metadata = MetaData()
        self._buckets = Table(
            "rate_limit_buckets",
            metadata,
            Column("bucket_key", String(64), primary_key=True),
            Column("window_start", BigInteger, primary_key=True),
            Column("count", Integer, nullable=False),
            Column("expires_at", BigInteger, nullable=False),
            Index("idx_rate_limit_buckets_expiry", "expires_at"),
        )
        metadata.create_all(self.engine)
        self._metadata = metadata

    @staticmethod
    def _bucket_key(scope: str, identifier: str, secret: str) -> str:
        if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
            raise RateLimitConfigurationError(
                "GAIA_RATE_LIMIT_SECRET must contain at least 32 UTF-8 bytes."
            )
        if secret.casefold().startswith(("put_", "your_", "replace_")):
            raise RateLimitConfigurationError(
                "GAIA_RATE_LIMIT_SECRET is still a placeholder."
            )
        if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
            raise ValueError("Invalid rate-limit scope.")
        if not isinstance(identifier, str) or not identifier or len(identifier) > 512:
            raise ValueError("Invalid rate-limit identifier.")
        message = f"gaia-rate-limit-v1\\0{scope}\\0{identifier}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def consume(
        self,
        scope: str,
        identifier: str,
        *,
        limit: int,
        window_seconds: int,
        secret: str,
        now: int | None = None,
    ) -> RateLimitDecision:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1_000_000:
            raise ValueError("Rate limit must be between 1 and 1000000.")
        if (
            isinstance(window_seconds, bool)
            or not isinstance(window_seconds, int)
            or not 1 <= window_seconds <= 31_536_000
        ):
            raise ValueError("Rate-limit window must be between 1 second and one year.")

        key = self._bucket_key(scope, identifier, secret)
        current = int(time.time()) if now is None else int(now)
        window_start = current - (current % window_seconds)
        retry_after = max(1, window_start + window_seconds - current)
        expires_at = window_start + max(window_seconds * 2, 86_400)

        if self.engine.dialect.name == "sqlite":
            insert = sqlite_insert
        elif self.engine.dialect.name == "postgresql":
            insert = postgresql_insert
        else:
            raise RateLimitConfigurationError(
                "Persistent rate limiting requires SQLite or PostgreSQL."
            )

        statement = (
            insert(self._buckets)
            .values(
                bucket_key=key,
                window_start=window_start,
                count=1,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                index_elements=[self._buckets.c.bucket_key, self._buckets.c.window_start],
                set_={"count": self._buckets.c.count + 1},
                where=self._buckets.c.count < limit,
            )
            .returning(self._buckets.c.count)
        )

        with self.engine.begin() as db:
            # Expired counters are safe to remove; no request identity is retained.
            db.execute(
                delete(self._buckets).where(self._buckets.c.expires_at < current)
            )
            row = db.execute(statement).first()

        if row is None:
            return RateLimitDecision(False, 0, retry_after)
        used = int(row[0])
        return RateLimitDecision(True, max(0, limit - used), 0)
