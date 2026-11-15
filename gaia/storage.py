"""Shared SQLAlchemy engine factory for SQLite development and PostgreSQL hosting."""
from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

def configured_database_url() -> str:
    configured = os.getenv("GAIA_DATABASE_URL", "").strip()
    if configured.startswith("postgres://"):
        return "postgresql+psycopg://" + configured[len("postgres://"):]
    if configured.startswith("postgresql://"):
        return "postgresql+psycopg://" + configured[len("postgresql://"):]
    if configured:
        return configured
    path = Path(os.getenv("GAIA_DB_PATH", "data/gaia.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + str(path.resolve())

def create_database_engine(path: str | Path | None = None) -> Engine:
    if path is not None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        url = "sqlite:///" + str(file_path.resolve())
    else:
        url = configured_database_url()
    parsed = make_url(url)
    options: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if parsed.get_backend_name() == "sqlite":
        options["connect_args"] = {"timeout": 10, "check_same_thread": False}
    else:
        options["pool_recycle"] = 300
    return create_engine(url, **options)

def database_backend(engine: Engine) -> str:
    return engine.dialect.name
