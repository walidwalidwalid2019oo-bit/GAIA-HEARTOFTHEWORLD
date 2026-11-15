from __future__ import annotations

from gaia.storage import create_database_engine, configured_database_url, database_backend


def test_explicit_database_path_uses_sqlite_and_persists(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    first = create_database_engine(path)
    assert database_backend(first) == "sqlite"
    with first.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE sample (value TEXT)")
        connection.exec_driver_sql("INSERT INTO sample(value) VALUES ('saved')")
    first.dispose()

    reopened = create_database_engine(path)
    with reopened.connect() as connection:
        assert connection.exec_driver_sql("SELECT value FROM sample").scalar_one() == "saved"
    reopened.dispose()


def test_configured_postgres_url_is_normalized_for_psycopg(monkeypatch):
    monkeypatch.setenv("GAIA_DATABASE_URL", "postgres://gaia:secret@db.example:5432/gaia")
    assert configured_database_url() == "postgresql+psycopg://gaia:secret@db.example:5432/gaia"


def test_explicit_postgresql_url_uses_postgresql_dialect(monkeypatch):
    monkeypatch.setenv("GAIA_DATABASE_URL", "postgresql://gaia:secret@db.example:5432/gaia")
    engine = create_database_engine()
    try:
        assert database_backend(engine) == "postgresql"
    finally:
        engine.dispose()
