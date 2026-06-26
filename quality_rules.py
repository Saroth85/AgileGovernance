"""Shared backlog-quality rules.

Deterministic INVEST / Definition-of-Ready checks. Used by the `check_story_quality`
tool that the Backlog Governance Agent calls (the agent reasons over the tool output),
and by the offline tests so the gate logic can be validated without Foundry.
"""
from __future__ import annotations

import re
from typing import Dict, List

ISSUE_MISSING_AC = "missing acceptance criteria"
ISSUE_VAGUE = "vague or ambiguous wording"
ISSUE_NO_VALUE = "missing user value"
ISSUE_NO_ROLE = "missing user role"
ISSUE_TOO_LARGE = "too large, not small"
ISSUE_NOT_TESTABLE = "not testable"
ISSUE_DEP = "unstated dependency"

VAGUE_TERMS = [
    "veloce", "facile", "user-friendly", "intuitivo", "performante", "ottimale",
    "robusto", "scalabile", "semplice", "migliore", "rapido", "efficiente",
    "fast", "easy", "intuitive", "robust", "scalable", "seamless", "better",
]
ROLE_MARKERS = ["come ", "in qualità di", "as a", "as an"]
VALUE_MARKERS = ["così che", "cosi che", "in modo da", "so that", "per poter", "to be able"]
AC_MARKERS = [
    "criteri di accettazione", "acceptance criteria", "given", "when", "then",
    "dato che", "quando", "allora",
]
DEP_MARKERS = ["dipende da", "dopo che", "richiede", "depends on", "after", "blocked by"]

GATE_THRESHOLD = 70.0
GATE_MIN_INVEST = 3


def _has(text: str, markers: List[str]) -> bool:
    t = text.lower()
    return any(m in t for m in markers)


def analyse_story(story_text: str) -> Dict[str, object]:
    """Return INVEST scores, detected issues, score and gate decision."""
    t = story_text.lower()
    words = re.findall(r"\w+", t)
    issues: List[str] = []

    if not _has(t, AC_MARKERS):
        issues.append(ISSUE_MISSING_AC)
    if any(term in t for term in VAGUE_TERMS):
        issues.append(ISSUE_VAGUE)
    if not _has(t, VALUE_MARKERS):
        issues.append(ISSUE_NO_VALUE)
    if not _has(t, ROLE_MARKERS):
        issues.append(ISSUE_NO_ROLE)
    conj = t.count(" e ") + t.count(" and ")
    if len(words) > 60 or conj >= 4 or "tutti" in t or " all " in t:
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
    overall = max(0.0, 100.0 - 13.0 * len(issues))
    gate_pass = overall >= GATE_THRESHOLD and min(invest.values()) >= GATE_MIN_INVEST
    classification = "ready" if gate_pass else "needs_refinement"

    return {
        "classification": classification,
        "invest": invest,
        "issues": issues,
        "overall_score": round(overall, 1),
        "gate_pass": gate_pass,
    }
