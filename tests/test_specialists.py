import pytest

from gaia.ai.specialists import SPECIALISTS, choose_specialist


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Teach me the history of astronomy", "APOLLO"),
        ("Tell me about wildlife habitats", "ARTEMIS"),
        ("Help me debug this Python code", "HEPHAESTUS"),
        ("Compare these options and make a plan", "MINERVA"),
        ("Explain how ocean currents move", "POSEIDON"),
        ("How do I care for garden plants?", "DEMETER"),
        ("Hello GAIA, what can you do?", "GAIA"),
    ],
)
def test_specialist_routing(message, expected):
    assert choose_specialist(message) == expected


def test_routing_uses_whole_words_not_accidental_substrings():
    assert choose_specialist("I am researching the planet") == "GAIA"
    assert choose_specialist("The decoder is ready") == "GAIA"


def test_every_specialist_has_a_role_focus_and_instruction():
    expected = {"GAIA", "APOLLO", "ARTEMIS", "HEPHAESTUS", "MINERVA", "POSEIDON", "DEMETER"}

    assert set(SPECIALISTS) == expected
    for specialist in SPECIALISTS.values():
        assert specialist["role"]
        assert specialist["focus"]
        assert specialist["instruction"]
