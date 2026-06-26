# Evaluation

The system is measured three ways: **correctness** (does the gate decide right?),
**output quality** (are the agents' responses coherent and on-task?), and **safety**.

## 1. Correctness — offline harness (governance logic)

Run `python challenge-3-evaluate/run_local_eval.py` over the 15-story golden set.

| Metric | Score |
|--------|-------|
| Issue-detection precision | **0.91** |
| Issue-detection recall | **0.98** |
| Issue-detection F1 | **0.91** |
| Gate accuracy (decision vs. human label) | **0.93** (14/15) |

Policy: pass when `score ≥ 70` and no INVEST dimension `< 3`. Edge cases analysed in
[RESULTS.md](./RESULTS.md). This is the measure of *whether the gate is right*, scored
against ground-truth labels.

## 2. Output quality — Foundry LLM-as-judge

Run in the Foundry portal (judge model `gpt-5-mini`) over the same 15 cases. Real results:

| Evaluator | Score |
|-----------|-------|
| Coherence | **4.7 / 5** |
| Intent Resolution | **4.9 / 5** |
| Fluency | **4.0 / 5** |
| Customer Satisfaction | **4.3 / 5** |
| Task Adherence / Completion | **1.0** |
| QualityGrader | **pass** (15/15) |

## 3. Safety — Foundry safety evaluators

Clean sweep across every case and every dimension:

| Evaluator | Result |
|-----------|--------|
| Violence, Self-harm, Sexual, Hate & Unfairness | **0 / no harmful content** |
| Protected Material, Code Vulnerability, Indirect Attack | **pass** (15/15) |

## Finding from the Foundry runs (and the fix)

The first portal run was accidentally targeted at the **Sprint Planning Agent**, which
planned every story (even ones that should fail the gate) — so the quality scores above
describe the *planner's* output, and governance correctness was not measured.

Re-targeting the run at the **Backlog Governance Agent** exposed a deeper issue: the agent
**called its `check_story_quality` tool, but the portal evaluation environment does not
execute custom Python tools**, so no tool result returned and the agent stopped without a
verdict (empty output on all 15 items; it even guessed story_ids that weren't in the
dataset). Only the safety evaluators — which don't need a completed answer — produced scores.

**Fix applied:** the Backlog Governance Agent now evaluates the story **text directly** and
always returns the JSON verdict; the tool is an *optional* accelerator used only when a
`story_id` and a tool runtime are present. With this change the agent produces a complete
verdict in the portal, so Coherence / Intent / correctness become measurable there too. The
tool path remains intact for production and for code-based (SDK) evaluation, where the tool
*does* execute.

**How to re-run cleanly:** target `backlog-governance-agent`, upload
`challenge-3-evaluate/eval_portal.jsonl` (story text is inline — no tool needed), keep
Coherence + Fluency + the safety set. For gate-correctness in the portal, add a custom
ground-truth grader (the built-in quality evaluators do not read `ground_truth`); otherwise
use the offline correctness numbers in section 1.
