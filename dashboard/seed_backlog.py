"""
Seed the dashboard demo backlog from sample_backlog.json.

    python dashboard/seed_backlog.py

Each story is assessed by the governance engine (dashboard-demo team policy, which has a
human-review band) and added with a staggered creation time so the ageing view has variety.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import governance_store as store

SAMPLE = ROOT / "sample_backlog.json"


def main():
    store.reset()
    stories = json.loads(SAMPLE.read_text(encoding="utf-8"))["stories"]
    now = datetime.now(timezone.utc)
    for s in stories:
        created = (now - timedelta(days=s.get("age_days", 0))).isoformat()
        store.assess_story(s["title"], s["description"], created_at=created)

    m = store.get_metrics()
    print(f"Seeded {m['total']} stories.")
    print(f"  pass={m['counts']['pass']}  review={m['counts']['review']}  "
          f"reject={m['counts']['reject']}")
    print(f"  in review (human queue): {m['in_review']}")
    print(f"  gate pass-rate (auto-decided): {m['gate_pass_rate']:.0%}")


if __name__ == "__main__":
    main()
