# Roadmap

> **Update:** the human-in-the-loop review mode and the backlog-health dashboard described
> below are now **implemented** in [`../dashboard/`](../dashboard/). This file records the
> design and what remains.

The goal is to make the governance logic transparent enough that a team would trust it in
the messy reality of sprint planning.

## 1. Human-in-the-loop review mode — IMPLEMENTED

The three-way gate (`pass` / `review` / `reject`) plus the configurable `review_band` and
`hard_blockers` route stories the gate can't confidently auto-decide to a person.

- **Review queue** — borderline and hard-blocked stories surface in the dashboard's review
  queue with their score, issues, blocker, and ageing. (`dashboard/`)
- **Human decision feeds back** — each approve/send-back is written to
  `data/human_decisions.jsonl` and appended to `data/feedback_labels.jsonl` as a new
  ground-truth example, so the gate improves on exactly the cases it found hard.
- **Hard blockers** — `unstated dependency` can never auto-pass; it is routed to review (or
  rejected in binary mode). Configurable per team.

**Remaining:** wire the review queue to a real channel (Teams / Azure DevOps work-item tag)
so reviewers act where they already work, and feed `feedback_labels.jsonl` back into the
portal evaluation dataset on a schedule.

## 2. Backlog-health dashboard — IMPLEMENTED

A web view that aggregates the structured verdicts into health signals:

- Gate **pass-rate** and the pass / review / reject split.
- **Recurring INVEST failures** by dimension.
- **Top recurring issues** across the backlog.
- **Story ageing** in the review queue.

Built with FastAPI + a dependency-free UI (`dashboard/`). Because every verdict is
structured, this is aggregation over existing data, not new instrumentation.

**Remaining:** read live traces from Application Insights (instead of the local backlog
store) so the dashboard reflects production gate activity over time.

## 3. Smaller refinements (from evaluation)

- **Measurable-criterion detector** for the acceptance-criteria check — removes the AC
  false positives (see [RESULTS.md](./RESULTS.md)); once reliable, missing AC can join
  `hard_blockers`.
- Expand the value/size heuristics flagged by the minor evaluation misses.
- Optionally let the LLM layer override a keyword rule when it sees a concrete testable
  outcome, with the override logged for audit.
