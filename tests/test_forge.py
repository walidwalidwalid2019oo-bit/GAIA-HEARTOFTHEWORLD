from pathlib import Path

import pytest

from gaia.forge import Forge


def test_forge_creates_pending_blueprint(tmp_path: Path) -> None:
    forge = Forge(tmp_path / "blueprints.json")

    item = forge.propose("Star Keeper", "Tracks astronomy learning projects", "violet")

    assert item["name"] == "STAR_KEEPER"
    assert item["status"] == "pending_review"
    assert item["permissions"] == []
    assert forge.pending() == [item]


def test_forge_rejects_duplicate_pending_name(tmp_path: Path) -> None:
    forge = Forge(tmp_path / "blueprints.json")
    forge.propose("Atlas", "Maps project notes")

    with pytest.raises(ValueError, match="already exists"):
        forge.propose("Atlas", "A second mapping system")


def test_gaia_can_review_a_blueprint_once(tmp_path: Path) -> None:
    forge = Forge(tmp_path / "blueprints.json")
    proposal = forge.propose("Minerva Two", "Compares research summaries")

    reviewed = forge.review(proposal["id"], "approved")

    assert reviewed["status"] == "approved"
    assert reviewed["reviewed_by"] == "GAIA"
    assert forge.pending() == []
    with pytest.raises(ValueError, match="already been reviewed"):
        forge.review(proposal["id"], "rejected")


def test_blueprint_activation_is_explicitly_unavailable(tmp_path: Path) -> None:
    forge = Forge(tmp_path / "blueprints.json")

    with pytest.raises(ValueError, match="not available"):
        forge.activate("BP-0001")
