"""Shared backlog-quality rules — configurable per team.

Deterministic INVEST / Definition-of-Ready checks. Used by the `check_story_quality`
tool that the Backlog Governance Agent calls (the agent reasons over the tool output),
and by the offline tests / local evaluation so the gate logic can be validated without
Foundry.

The Definition of Ready and gate policy are NOT hard-coded: they are loaded from
``config/dor_policy.json``. A ``default`` policy applies unless a team override is
selected via ``analyse_story(text, team="<name>")``. This makes the bar adoptable —
each team can tune its threshold, INVEST floor, vague-term list, size limits, and an
optional human-review band for borderline scores — without touching code.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

# Canonical issue labels (stable identifiers used by the evaluator)
ISSUE_MISSING_AC = "missing acceptance criteria"
ISSUE_VAGUE = "vague or ambiguous wording"
ISSUE_NO_VALUE = "missing user value"
ISSUE_NO_ROLE = "missing user role"
ISSUE_TOO_LARGE = "too large, not small"
ISSUE_NOT_TESTABLE = "not testable"
ISSUE_DEP = "unstated dependency"

# Language markers (English + Italian) for the structural checks
ROLE_MARKERS = ["come ", "in qualità di", "as a", "as an"]
VALUE_MARKERS = ["così che", "cosi che", "in modo da", "so that", "per poter", "to be able"]
AC_MARKERS = [
    "criteri di accettazione", "acceptance criteria", "given", "when", "then",
    "dato che", "quando", "allora",
]
DEP_MARKERS = ["dipende da", "dopo che", "richiede", "depends on", "after", "blocked by"]

_POLICY_PATH = Path(__file__).resolve().parent / "config" / "dor_policy.json"


@lru_cache(maxsize=1)
def _load_policy_file() -> dict:
    with open(_POLICY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_policy(team: Optional[str] = None) -> dict:
    """Return the effective policy for a team (default + team overrides)."""
    data = _load_policy_file()
    policy = {k: v for k, v in data["default"].items() if not k.startswith("_")}
    if team and team in data.get("teams", {}):
        for k, v in data["teams"][team].items():
            if not k.startswith("_"):
                policy[k] = v
    return policy


def _has(text: str, markers: List[str]) -> bool:
    return any(m in text for m in markers)


def analyse_story(story_text: str, team: Optional[str] = None) -> Dict[str, object]:
    """Return INVEST scores, detected issues, score and the gate decision.

    The gate decision is three-way (``gate_status``): ``pass`` / ``review`` / ``reject``.
    ``review`` only occurs when the selected team policy sets a non-zero ``review_band``,
    seeding human-in-the-loop for borderline scores. ``gate_pass`` (bool) is kept for
    backward compatibility and is True only for ``pass``.
    """
    policy = get_policy(team)
    vague_terms = policy["vague_terms"]
    t = story_text.lower()
    words = re.findall(r"\w+", t)
    issues: List[str] = []

    if not _has(t, AC_MARKERS):
        issues.append(ISSUE_MISSING_AC)
    if any(term in t for term in vague_terms):
        issues.append(ISSUE_VAGUE)
    if not _has(t, VALUE_MARKERS):
        issues.append(ISSUE_NO_VALUE)
    if not _has(t, ROLE_MARKERS):
        issues.append(ISSUE_NO_ROLE)
    conj = t.count(" e ") + t.count(" and ")
    if (len(words) > policy["max_words"] or conj >= policy["max_conjunctions"]
            or "tutti" in t or " all " in t):
        issues.append(ISSUE_TOO_LARGE)
    if ISSUE_MISSING_AC in issues and ISSUE_VAGUE in issues:
        issues.append(ISSUE_NOT_TESTABLE)
    if _has(t, DEP_MARKERS):
        issues.append(ISSUE_DEP)

    issues = sorted(set(issues))

    invest = {
        "independent": 3 if ISSUE_DEP in issues else 5,
        "negotiable": 4,
        "valuable": 2 if ISSUE_NO_VALUE in issues else 5,
        "estimable": 2 if ISSUE_TOO_LARGE in issues else 4,
        "small": 2 if ISSUE_TOO_LARGE in issues else 5,
        "testable": 1 if ISSUE_NOT_TESTABLE in issues
        else (3 if ISSUE_MISSING_AC in issues else 5),
    }
    overall = max(0.0, 100.0 - policy["issue_penalty"] * len(issues))
    min_invest = min(invest.values())

    threshold = policy["gate_threshold"]
    band = policy.get("review_band", 0)
    hard_blockers = set(policy.get("hard_blockers", []))
    invest_ok = min_invest >= policy["min_invest"]
    blocked = bool(hard_blockers & set(issues))

    # Three-way gate decision. A hard blocker (e.g. an unstated dependency) can never
    # auto-pass regardless of score: it is rejected (binary) or sent to a human (HITL).
    if blocked:
        gate_status = "review" if band > 0 else "reject"
    elif not invest_ok or overall < threshold - band:
        gate_status = "reject"
    elif overall >= threshold + band and invest_ok:
        gate_status = "pass"
    else:
        gate_status = "review"  # borderline -> human-in-the-loop

    gate_pass = gate_status == "pass"
    classification = "ready" if gate_pass else "needs_refinement"

    # Definition-of-Ready checklist (which configured items are satisfied)
    dor_all = {
        "has_user_role": _has(t, ROLE_MARKERS),
        "has_user_value": _has(t, VALUE_MARKERS),
        "has_acceptance_criteria": _has(t, AC_MARKERS),
        "is_appropriately_small": ISSUE_TOO_LARGE not in issues,
    }
    dor_checklist = {k: dor_all[k] for k in policy["required_dor"] if k in dor_all}

    return {
        "classification": classification,
        "invest": invest,
        "issues": issues,
        "overall_score": round(overall, 1),
        "gate_pass": gate_pass,
        "gate_status": gate_status,
        "blocked_by": sorted(hard_blockers & set(issues)),
        "dor_checklist": dor_checklist,
        "policy": {"team": team or "default", "threshold": threshold,
                   "min_invest": policy["min_invest"], "review_band": band},
    }
