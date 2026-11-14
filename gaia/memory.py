"""Small local JSON memory store for the GAIA prototype."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "memory.json"

class MemoryStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"notes": [], "events": []})

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("notes", [])
                data.setdefault("events", [])
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return {"notes": [], "events": []}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_note(self, text: str) -> dict[str, str]:
        note = {"text": text.strip(), "created_at": self._now()}
        data = self._read()
        data["notes"].append(note)
        self._write(data)
        self.add_event("Memory note saved.")
        return note

    def notes(self) -> list[dict[str, str]]:
        return list(self._read().get("notes", []))

    def add_event(self, message: str) -> None:
        data = self._read()
        data["events"].append({"message": message, "created_at": self._now()})
        data["events"] = data["events"][-100:]
        self._write(data)

    def events(self, limit: int = 12) -> list[dict[str, str]]:
        return list(self._read().get("events", []))[-limit:]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
