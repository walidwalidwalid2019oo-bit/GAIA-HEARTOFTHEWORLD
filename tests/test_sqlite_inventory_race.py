from __future__ import annotations

import sqlite3

import pytest

from gaia.migrations import sqlite_inventory as inventory_module


def test_inventory_rechecks_sidecars_after_read(tmp_path, monkeypatch):
    source = tmp_path / "gaia.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT)")

    original_check = inventory_module._existing_sidecars
    checks = 0

    def add_sidecar_on_final_check(path):
        nonlocal checks
        checks += 1
        if checks == 2:
            (tmp_path / "gaia.sqlite3-wal").write_bytes(b"appeared during inspection")
        return original_check(path)

    monkeypatch.setattr(inventory_module, "_existing_sidecars", add_sidecar_on_final_check)

    with pytest.raises(RuntimeError, match="gained journal sidecars"):
        inventory_module.inspect_sqlite_database(source)

    assert checks == 2
