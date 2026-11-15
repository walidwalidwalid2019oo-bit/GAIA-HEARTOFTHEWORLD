"""Account and revocable-session primitives; not exposed as public routes yet."""
from __future__ import annotations
import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from gaia.storage import create_database_engine

_EMAIL = re.compile(r"^[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+$")
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P, _SCRYPT_BYTES = 1 << 14, 8, 1, 64

class AuthenticationError(ValueError):
    """An account or session operation could not be completed safely."""

class UserAuth:
    """Password-hash and revocable opaque-session store.

    HTTP routes remain disabled until private records are owner-scoped.
    """
    def __init__(self, *, engine: Engine | None = None) -> None:
        self.engine = engine or create_database_engine()
        with self.engine.begin() as db:
            db.execute(text("""CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(36) PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL, created_at VARCHAR(40) NOT NULL
            )"""))
            db.execute(text("""CREATE TABLE IF NOT EXISTS auth_sessions (
                session_hash VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                created_at VARCHAR(40) NOT NULL, expires_at VARCHAR(40) NOT NULL,
                revoked_at VARCHAR(40)
            )"""))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id, expires_at)"))

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().casefold()
        if len(normalized) > 254 or not _EMAIL.fullmatch(normalized):
            raise AuthenticationError("Enter a valid email address.")
        return normalized

    @staticmethod
    def _hash_password(password: str) -> str:
        if not 12 <= len(password) <= 128:
            raise AuthenticationError("Password must be between 12 and 128 characters.")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N,
                                 r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_BYTES,
                                 maxmem=64 * 1024 * 1024)
        return "$".join(("scrypt", str(_SCRYPT_N), str(_SCRYPT_R), str(_SCRYPT_P),
                         base64.urlsafe_b64encode(salt).decode("ascii"),
                         base64.urlsafe_b64encode(digest).decode("ascii")))

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            algorithm, n, r, p, salt_text, digest_text = stored.split("$", 5)
            n, r, p = int(n), int(r), int(p)
            if algorithm != "scrypt" or n < 2 or n > (1 << 18) or r < 1 or r > 16 or p < 1 or p > 4:
                return False
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
            actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                                    dklen=len(expected), maxmem=64 * 1024 * 1024)
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError, UnicodeError):
            return False

    def create_user(self, email: str, password: str) -> dict[str, str]:
        normalized = self._normalize_email(email)
        password_hash = self._hash_password(password)
        user_id, now = str(uuid4()), datetime.now(timezone.utc).isoformat()
        try:
            with self.engine.begin() as db:
                db.execute(text("INSERT INTO users(user_id,email,password_hash,created_at) "
                                "VALUES (:id,:email,:password_hash,:created)"),
                           {"id": user_id, "email": normalized,
                            "password_hash": password_hash, "created": now})
        except IntegrityError as exc:
            raise AuthenticationError("Account could not be created.") from exc
        return {"user_id": user_id, "email": normalized, "created_at": now}

    def verify_credentials(self, email: str, password: str) -> dict[str, str] | None:
        try:
            normalized = self._normalize_email(email)
        except AuthenticationError:
            return None
        with self.engine.connect() as db:
            row = db.execute(text("SELECT user_id,email,password_hash,created_at FROM users WHERE email=:email"),
                             {"email": normalized}).mappings().one_or_none()
        if row is None or not self._verify_password(password, row["password_hash"]):
            return None
        return {"user_id": row["user_id"], "email": row["email"], "created_at": row["created_at"]}

    def issue_session(self, user_id: str, *, ttl_seconds: int = 3600) -> dict[str, str]:
        if not 900 <= ttl_seconds <= 86400:
            raise AuthenticationError("Session lifetime must be between 15 minutes and 24 hours.")
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        now, expires = datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        with self.engine.begin() as db:
            if db.execute(text("SELECT 1 FROM users WHERE user_id=:id"), {"id": user_id}).first() is None:
                raise AuthenticationError("Account not found.")
            db.execute(text("INSERT INTO auth_sessions(session_hash,user_id,created_at,expires_at) "
                            "VALUES (:hash,:user_id,:created,:expires)"),
                       {"hash": digest, "user_id": user_id, "created": now.isoformat(),
                        "expires": expires.isoformat()})
        return {"access_token": token, "token_type": "Bearer", "expires_at": expires.isoformat()}

    def resolve_session(self, token: str) -> str | None:
        if not token or len(token) > 256:
            return None
        digest, now = hashlib.sha256(token.encode("utf-8")).hexdigest(), datetime.now(timezone.utc)
        with self.engine.connect() as db:
            row = db.execute(text("SELECT user_id,expires_at,revoked_at FROM auth_sessions WHERE session_hash=:hash"),
                             {"hash": digest}).mappings().one_or_none()
        if row is None or row["revoked_at"] is not None or datetime.fromisoformat(row["expires_at"]) <= now:
            return None
        return row["user_id"]

    def revoke_session(self, token: str) -> bool:
        if not token or len(token) > 256:
            return False
        digest, now = hashlib.sha256(token.encode("utf-8")).hexdigest(), datetime.now(timezone.utc).isoformat()
        with self.engine.begin() as db:
            result = db.execute(text("UPDATE auth_sessions SET revoked_at=:now "
                                     "WHERE session_hash=:hash AND revoked_at IS NULL"),
                                {"now": now, "hash": digest})
            return result.rowcount == 1
