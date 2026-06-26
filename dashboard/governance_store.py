"""
Data layer for the backlog-health dashboard + human-in-the-loop review.

Stories are assessed by the governance rule engine (quality_rules.analyse_story). Borderline
results (gate_status == "review") land in a human review queue; a reviewer's accept/reject
is recorded and appended to a feedback label file, closing the loop so the gate can be
improved on exactly the cases it found hard.

State is persisted as plain JSON files under ./data so the demo needs no database.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT))
from quality_rules import analyse_story  # noqa: E402

DATA_DIR = ROOT / "data"
BACKLOG_FILE = DATA_DIR / "backlog.json"
DECISIONS_FILE = DATA_DIR / "human_decisions.jsonl"
FEEDBACK_FILE = DATA_DIR / "feedback_labels.jsonl"
TEAM = "dashboard-demo"

INVEST_DIMS = ["independent", "negotiable", "valuable", "estimable", "small", "testable"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_backlog() -> List[dict]:
    if not BACKLOG_FILE.exists():
        return []
    return json.loads(BACKLOG_FILE.read_text(encoding="utf-8"))


def _write_backlog(items: List[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    BACKLOG_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def assess_story(title: str, description: str, created_at: Optional[str] = None) -> dict:
    """Assess a story and add it to the backlog."""
    verdict = analyse_story(description, team=TEAM)
    items = _read_backlog()
    sid = f"STR-{len(items) + 1:03d}"
    item = {
        "story_id": sid,
        "title": title,
        "description": description,
        "verdict": verdict,
        "created_at": created_at or _now(),
        "human_decision": None,   # None | "approved" | "rejected"
        "reviewer": None,
        "reviewed_at": None,
    }
    items.append(item)
    _write_backlog(items)
    return item


def record_decision(story_id: str, decision: str, reviewer: str = "reviewer") -> Optional[dict]:
    """Record a human review decision and append it to the feedback log."""
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")
    items = _read_backlog()
    target = next((it for it in items if it["story_id"] == story_id), None)
    if not target:
        return None
    target["human_decision"] = decision
    target["reviewer"] = reviewer
    target["reviewed_at"] = _now()
    _write_backlog(items)

    DATA_DIR.mkdir(exist_ok=True)
    with open(DECISIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"story_id": story_id, "decision": decision,
                            "reviewer": reviewer, "at": _now()}) + "\n")
    # Feedback label = a new ground-truth example for the next evaluation round
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "query": target["description"],
            "ground_truth": {"gate_pass": decision == "approved",
                             "issues": target["verdict"]["issues"]},
            "source": "human_review",
        }) + "\n")
    return target


def _effective_status(item: dict) -> str:
    """Final state: a human decision overrides a 'review' verdict."""
    if item["human_decision"] == "approved":
        return "pass"
    if item["human_decision"] == "rejected":
        return "reject"
    return item["verdict"]["gate_status"]


def _age_days(created_at: str) -> float:
    created = datetime.fromisoformat(created_at)
    return round((datetime.now(timezone.utc) - created).total_seconds() / 86400, 1)


def get_queue() -> List[dict]:
    """Stories awaiting a human decision (gate_status == review, not yet decided)."""
    queue = []
    for it in _read_backlog():
        if it["verdict"]["gate_status"] == "review" and it["human_decision"] is None:
            queue.append({
                "story_id": it["story_id"], "title": it["title"],
                "description": it["description"],
                "score": it["verdict"]["overall_score"],
                "issues": it["verdict"]["issues"],
                "blocked_by": it["verdict"].get("blocked_by", []),
                "age_days": _age_days(it["created_at"]),
            })
    return sorted(queue, key=lambda x: x["age_days"], reverse=True)


def get_metrics() -> dict:
    items = _read_backlog()
    total = len(items)
    counts = {"pass": 0, "review": 0, "reject": 0}
    invest_fail = {d: 0 for d in INVEST_DIMS}
    issue_freq: dict[str, int] = {}
    review_ages: List[float] = []

    for it in items:
        eff = _effective_status(it)
        counts[eff] = counts.get(eff, 0) + 1
        v = it["verdict"]
        for d in INVEST_DIMS:
            if v["invest"][d] < v["policy"]["min_invest"]:
                invest_fail[d] += 1
        for iss in v["issues"]:
            issue_freq[iss] = issue_freq.get(iss, 0) + 1
        if v["gate_status"] == "review" and it["human_decision"] is None:
            review_ages.append(_age_days(it["created_at"]))

    decided = counts["pass"] + counts["reject"]
    pass_rate = round(counts["pass"] / decided, 3) if decided else 0.0
    human_reviewed = sum(1 for it in items if it["human_decision"])

    return {
        "total": total,
        "counts": counts,
        "gate_pass_rate": pass_rate,
        "in_review": counts["review"],
        "human_reviewed": human_reviewed,
        "invest_failures": invest_fail,
        "top_issues": sorted(issue_freq.items(), key=lambda x: x[1], reverse=True),
        "review_ageing": {
            "count": len(review_ages),
            "oldest_days": max(review_ages) if review_ages else 0,
            "avg_days": round(sum(review_ages) / len(review_ages), 1) if review_ages else 0,
        },
        "policy_team": TEAM,
    }


def reset():
    for f in (BACKLOG_FILE, DECISIONS_FILE, FEEDBACK_FILE):
        if f.exists():
            f.unlink()
