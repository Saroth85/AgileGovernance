# Evaluation results

> Consolidated three-pillar evaluation (correctness, quality, safety) including the
> Foundry LLM-as-judge results: see [EVALUATION.md](./EVALUATION.md).

Concrete numbers from the offline evaluation harness
(`challenge-3-evaluate/run_local_eval.py`) over the 15-story hand-labelled golden set in
`eval_portal.jsonl`. The harness scores the deterministic INVEST/DoR engine that the
Backlog Governance Agent's tool exposes — so these numbers measure the rule layer the
agent reasons over. Reproduce with:

```bash
python challenge-3-evaluate/run_local_eval.py
```

## Gate policy used

| Parameter | Value |
|-----------|-------|
| `gate_threshold` (pass/fail cut-off, 0–100) | **70** |
| `min_invest` (INVEST floor, any dimension below this → reject) | **3** |
| `review_band` (human-in-the-loop band around the threshold) | **0** (binary) |
| `issue_penalty` (points removed per detected issue) | **13** |

All configurable per team in `config/dor_policy.json`.

## Aggregate metrics (n = 15)

| Metric | Score |
|--------|-------|
| Issue-detection **precision** | **0.91** |
| Issue-detection **recall** | **0.98** |
| Issue-detection **F1** | **0.91** |
| **Gate accuracy** (decision vs. human label) | **0.93** (14 / 15) |

High recall (0.98) means the engine rarely misses a real problem; the lower precision
(0.91) means it occasionally flags a problem that isn't there. For a *governance gate*
that trade-off is the right one — it is safer to over-flag and send a borderline story to
review than to wave a weak story through.

## Edge cases — where it struggles (more instructive than the successes)

The single gate miss and the precision dip are **the same root cause**: the keyword-based
acceptance-criteria detector. Together they are the most instructive part of the result.

### 1. Wrong decision: a story with no acceptance criteria slips through
> *"As a risk manager, I want a limit-breach alert, so that I can react quickly. The alert
> should be reliable."*

- **Expected:** needs refinement (no acceptance criteria → not ready).
- **Engine:** detected *"missing acceptance criteria"*, but the story still scored 87 and
  **passed** — this is the one gate-accuracy miss (14/15).
- **Why:** a single missing-AC issue only removes 13 points and lowers `testable` to 3 (the
  floor, not below it), so a genuinely not-ready story clears a purely score-based gate.

### 2. False positive: testable criteria without the marker words
> *"As a trader, I want to cancel a pending order, so that I avoid erroneous execution. The
> order must disappear from the book within one second and a confirmation is logged."*

- **Expected:** ready, no issues.
- **Engine:** flagged *"missing acceptance criteria"* → precision 0.00 on this row (it still
  passed the gate, so the decision was right but the label was noisy).
- **Why:** the AC check looks for *Given/When/Then* or *"acceptance criteria"*. This story
  has a real, testable criterion ("within one second", "confirmation is logged") phrased
  without those markers, so the rule misses it.

### The linked fix
Both cases trace to the same weak detector. The fix is **not** to hard-block on missing AC —
case 2 shows the detector produces false positives, so hard-blocking would wrongly reject a
ready story. The fix is a **measurable-criterion detector** (numbers, units, "logged",
"recorded") added to the AC check. Once the detector is reliable, missing AC can safely
become a hard blocker via the policy's `hard_blockers` list — the same mechanism already
applied to `unstated dependency`, which can never auto-pass.

### Minor cases
- One story had *"missing user value"* over-detected (precision 0.67) — a phrasing the
  value-marker list didn't recognise.
- One oversized story had *"too large, not small"* under-detected (recall 0.75) — the
  conjunction/word-count heuristic didn't trip.

## Takeaway

The gate is accurate (0.93) and safe (recall 0.98). The one wrong decision and the
precision dip share a single, well-understood cause — the keyword acceptance-criteria check
— with a clear fix that does not require weakening the gate. The `hard_blockers` policy lever
is in place for signals that are reliable enough to block outright (currently
`unstated dependency`). Tracked in [ITERATION_LOG.md](./ITERATION_LOG.md) and
[ROADMAP.md](./ROADMAP.md).
