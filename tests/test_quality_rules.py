"""Offline tests for the quality-gate logic (no Foundry required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from quality_rules import analyse_story


def test_good_story_passes():
    a = analyse_story(
        "As a back-office operator, I want to filter executed orders by settlement date, "
        "so that I can reconcile positions. Acceptance criteria: Given a date, When I "
        "filter, Then matching orders show."
    )
    assert a["gate_pass"] is True
    assert a["classification"] == "ready"
    assert a["issues"] == []


def test_vague_story_is_rejected():
    a = analyse_story("We need a fast and user-friendly dashboard for everything about trades.")
    assert a["gate_pass"] is False
    assert "vague or ambiguous wording" in a["issues"]
    assert "missing acceptance criteria" in a["issues"]


def test_missing_value_blocks_gate_via_invest():
    a = analyse_story("As a user I want reports.")
    assert a["gate_pass"] is False
    assert a["invest"]["valuable"] < 3
