import json
from pathlib import Path

from gaia.core import GaiaCore


def test_core_loads_registry_and_reports_status(tmp_path: Path) -> None:
    registry = {
        "GAIA": {"role": "Central coordinator", "status": "core"},
        "APOLLO": {"role": "Learning specialist", "status": "active"},
        "HEPHAESTUS": {"role": "Forge specialist", "status": "planned"},
    }
    registry_path = tmp_path / "subsystems.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    core = GaiaCore(registry_path)

    assert "Core online: GAIA" in core.status_report()
    assert "APOLLO" in core.status_report()
    assert "HEPHAESTUS" in core.status_report()


def test_core_routes_creation_requests_to_hephaestus(tmp_path: Path) -> None:
    registry = {
        "GAIA": {"role": "Central coordinator", "status": "core"},
        "HEPHAESTUS": {"role": "Forge specialist", "status": "planned"},
    }
    registry_path = tmp_path / "subsystems.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    response = GaiaCore(registry_path).route("Create a new subsystem")

    assert response.startswith("[HEPHAESTUS]")
    assert "Prototype routing only" in response


def test_core_rejects_registry_without_gaia(tmp_path: Path) -> None:
    registry_path = tmp_path / "subsystems.json"
    registry_path.write_text(json.dumps({"APOLLO": {}}), encoding="utf-8")

    try:
        GaiaCore(registry_path)
    except ValueError as error:
        assert "GAIA" in str(error)
    else:
        raise AssertionError("A registry without GAIA should be rejected.")
