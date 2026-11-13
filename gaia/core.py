"""Small, dependency-free GAIA coordinator prototype."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "subsystems.json"


class GaiaCore:
    """Loads approved subsystem metadata and routes simple requests."""

    def __init__(self, registry_path: Path = REGISTRY_PATH) -> None:
        self.registry_path = registry_path
        self.subsystems = self._load_registry()

    def _load_registry(self) -> dict[str, dict[str, Any]]:
        with self.registry_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict) or "GAIA" not in data:
            raise ValueError("Registry must be an object containing GAIA.")
        return data

    def status_report(self) -> str:
        active = [
            name for name, info in self.subsystems.items()
            if info.get("status") in {"active", "core"}
        ]
        planned = [
            name for name, info in self.subsystems.items()
            if info.get("status") == "planned"
        ]
        return (
            f"Core online: GAIA\n"
            f"Active systems: {', '.join(active)}\n"
            f"Planned systems: {', '.join(planned) or 'None'}"
        )

    def route(self, request: str) -> str:
        text = request.lower()

        if any(word in text for word in ("build", "create", "design", "subsystem")):
            target = "HEPHAESTUS"
        elif any(word in text for word in ("learn", "explain", "study", "what is")):
            target = "APOLLO"
        elif any(word in text for word in ("analyze", "compare", "solve", "reason")):
            target = "MINERVA"
        else:
            target = "GAIA"

        info = self.subsystems[target]
        return (
            f"[{target}] {info['role']}\n"
            f"Prototype routing only: your request was received. "
            f"The full AI connection is not installed yet."
        )
