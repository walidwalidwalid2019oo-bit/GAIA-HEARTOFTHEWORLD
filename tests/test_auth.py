from __future__ import annotations
import pytest
from gaia.assistant.auth import AuthenticationError, UserAuth
from gaia.storage import create_database_engine

def test_user_auth_stores_password_hash_and_verifies_credentials(tmp_path):
    engine = create_database_engine(tmp_path / "auth.sqlite3")
    auth = UserAuth(engine=engine)
    created = auth.create_user("  Pilot@Example.com ", "a-long-test-password")
    assert created["email"] == "pilot@example.com"
    assert auth.verify_credentials("PILOT@example.com", "a-long-test-password")["user_id"] == created["user_id"]
    assert auth.verify_credentials("pilot@example.com", "incorrect-password") is None
    engine.dispose()

def test_user_auth_rejects_weak_password_and_duplicate_account(tmp_path):
    engine = create_database_engine(tmp_path / "auth.sqlite3")
    auth = UserAuth(engine=engine)
    with pytest.raises(AuthenticationError):
        auth.create_user("pilot@example.com", "short")
    auth.create_user("pilot@example.com", "a-long-test-password")
    with pytest.raises(AuthenticationError):
        auth.create_user("PILOT@example.com", "another-long-password")
    engine.dispose()

def test_sessions_are_hashed_revocable_and_expiring(tmp_path):
    engine = create_database_engine(tmp_path / "auth.sqlite3")
    auth = UserAuth(engine=engine)
    user = auth.create_user("pilot@example.com", "a-long-test-password")
    session = auth.issue_session(user["user_id"], ttl_seconds=900)
    assert auth.resolve_session(session["access_token"]) == user["user_id"]
    assert auth.revoke_session(session["access_token"]) is True
    assert auth.resolve_session(session["access_token"]) is None
    assert auth.revoke_session(session["access_token"]) is False
    with pytest.raises(AuthenticationError):
        auth.issue_session(user["user_id"], ttl_seconds=60)
    engine.dispose()
