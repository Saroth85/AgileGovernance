"""
Local evaluation of the Backlog Governance rule engine over the golden set.

    python eval/run_local_eval.py

This runs the deterministic INVEST/DoR analysis (the logic the Governance Agent's tool
exposes) against the hand-labelled dataset in eval_portal.jsonl and reports concrete
precision / recall / F1 on issue detection plus gate-decision accuracy — and flags the
cases where the engine struggles. It needs no Foundry resources, so you can validate and
tune the gate policy offline before running the LLM-as-judge evaluation in the portal.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from quality_rules import analyse_story, get_policy

GOLDEN = Path(__file__).resolve().parent / "eval_portal.jsonl"
REPORT = Path(__file__).resolve().parent / "local_eval_report.json"
SUFFIX = " Evaluate this story."


def _parse_ground_truth(s: str) -> dict:
    # ground_truth is a single-quoted, JSON-valued dict string -> make it valid JSON
    return json.loads(s.replace("'", '"'))


def load_cases():
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        story = row["query"]
        if story.endswith(SUFFIX):
            story = story[: -len(SUFFIX)].strip()
        yield story, _parse_ground_truth(row["ground_truth"])


def score_issues(detected, expected):
    f, tr = set(detected), set(expected)
    tp = len(f & tr)
    precision = tp / len(f) if f else (1.0 if not tr else 0.0)
    recall = tp / len(tr) if tr else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def main():
    pol = get_policy()
    print(f"\n=== Local evaluation over the golden set ===")
    print(f"Policy: threshold={pol['gate_threshold']}  min_invest={pol['min_invest']}  "
          f"review_band={pol['review_band']}\n")
    print(f"{'#':<3}{'gate':<7}{'exp':<6}{'prec':<7}{'rec':<7}{'f1':<7}ok")
    print("-" * 42)

    rows, struggles = [], []
    for i, (story, gt) in enumerate(load_cases(), 1):
        a = analyse_story(story)
        precision, recall, f1 = score_issues(a["issues"], gt.get("issues", []))
        gate_correct = a["gate_pass"] == gt["gate_pass"]
        rows.append({"precision": precision, "recall": recall, "f1": f1,
                     "gate_correct": gate_correct})
        ok = "OK" if gate_correct else "XX"
        print(f"{i:<3}{str(a['gate_pass']):<7}{str(gt['gate_pass']):<6}"
              f"{precision:<7.2f}{recall:<7.2f}{f1:<7.2f}{ok}")
        if (not gate_correct) or f1 < 1.0:
            struggles.append({
                "story": story, "expected_gate": gt["gate_pass"],
                "predicted_gate": a["gate_pass"], "score": a["overall_score"],
                "expected_issues": sorted(gt.get("issues", [])),
                "detected_issues": a["issues"],
                "precision": round(precision, 2), "recall": round(recall, 2),
            })

    n = len(rows)
    agg = {
        "issue_precision": round(mean(r["precision"] for r in rows), 3),
        "issue_recall": round(mean(r["recall"] for r in rows), 3),
        "issue_f1": round(mean(r["f1"] for r in rows), 3),
        "gate_accuracy": round(mean(1.0 if r["gate_correct"] else 0.0 for r in rows), 3),
        "n": n,
    }
    print("-" * 42)
    print(f"\nAggregate over {n} stories:")
    print(f"  issue precision : {agg['issue_precision']:.2f}")
    print(f"  issue recall    : {agg['issue_recall']:.2f}")
    print(f"  issue F1        : {agg['issue_f1']:.2f}")
    print(f"  gate accuracy   : {agg['gate_accuracy']:.2f}")
    print(f"\nStruggle cases: {len(struggles)}")
    for s in struggles:
        print(f"  - score {s['score']}: pred gate={s['predicted_gate']} "
              f"exp={s['expected_gate']} | det={s['detected_issues']} exp={s['expected_issues']}")

    REPORT.write_text(json.dumps({"policy": pol, "aggregate": agg, "struggles": struggles},
                                 indent=2), encoding="utf-8")
    print(f"\nReport written to {REPORT.name}\n")


if __name__ == "__main__":
    main()
