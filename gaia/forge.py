"""HEPHAESTUS creates safe, declarative subsystem blueprints."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "blueprints.json"
VALID_COLORS = {"cyan", "green", "gold", "violet", "blue", "copper", "white"}

class Forge:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, data: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def propose(self, name: str, purpose: str, color: str = "cyan") -> dict[str, Any]:
        clean_name = re.sub(r"[^A-Z0-9_-]", "", name.upper().replace(" ", "_"))[:24]
        clean_purpose = " ".join(purpose.split())[:280]
        clean_color = color.lower().strip()
        if not clean_name or not clean_purpose:
            raise ValueError("A valid name and purpose are required.")
        if clean_color not in VALID_COLORS:
            raise ValueError("Choose a supported color: " + ", ".join(sorted(VALID_COLORS)))
        proposals = self._read()
        if any(p["name"] == clean_name and p["status"] != "rejected" for p in proposals):
            raise ValueError("A non-rejected proposal with that name already exists.")
        proposal = {
            "id": f"BP-{len(proposals) + 1:04d}",
            "name": clean_name,
            "purpose": clean_purpose,
            "color": clean_color,
            "role": "Proposed specialized subsystem",
            "permissions": [],
            "memory_boundary": "isolated",
            "version": "0.1.0",
            "status": "pending_review",
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "created_by": "HEPHAESTUS"
        }
        proposals.append(proposal)
        self._write(proposals)
        return proposal

    def all(self) -> list[dict[str, Any]]:
        return self._read()

    def pending(self) -> list[dict[str, Any]]:
        return [p for p in self._read() if p.get("status") == "pending_review"]

    def review(self, proposal_id: str, decision: str) -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be approved or rejected.")
        proposals = self._read()
        for proposal in proposals:
            if proposal.get("id", "").upper() == proposal_id.upper():
                if proposal.get("status") != "pending_review":
                    raise ValueError("This proposal has already been reviewed.")
                proposal["status"] = decision
                proposal["reviewed_by"] = "GAIA"
                proposal["reviewed_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
                self._write(proposals)
                return proposal
        raise ValueError("Blueprint ID not found.")

    def activate(self, proposal_id: str) -> None:
        raise ValueError("Activation is not available in this prototype. Approval records a decision only; no code is executed.")
