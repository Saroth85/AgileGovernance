# Challenge 3 — Evaluate (LLM-as-judge)

**Goal:** measure whether the Backlog Governance Agent's decisions are actually correct,
using a labelled dataset and LLM-as-judge scoring.

## Why this challenge wins points

Monitoring tells you the agent *ran*; evaluation tells you it was *right*. For a governance
agent this is the whole game: an agent that confidently approves a vague, untestable story
looks perfectly healthy to monitoring and is caught only by evaluation.

The evaluation here is **crisp**, not a soft "looks good". Each story in the golden set is
hand-labelled with its expected classification, gate decision, and issues — so the judge
measures real correctness against ground truth.

## The dataset

[`eval_portal.jsonl`](./eval_portal.jsonl) — 15 user stories spanning ready and
needs-refinement cases. Each row has:
- `query` — the story to evaluate
- `ground_truth` — the expected `{classification, gate_pass, issues}`

The mix is intentional: clean stories that must pass, and stories with specific seeded
problems (vague wording, missing acceptance criteria, oversized scope, unstated
dependency) that the agent must catch — without flagging problems that aren't there.

## Run the evaluation (Foundry portal)

1. Go to [ai.azure.com](https://ai.azure.com) → your project → **Build → Evaluations →
   Create**.
2. Choose **Agent** as the target and select `backlog-governance-agent`.
3. Select **Individual Turns → Existing Dataset → Upload new dataset**, name it
   (e.g. `agile-eval`), and upload `challenge-3-evaluate/eval_portal.jsonl`.
4. In **Criteria**, keep **Coherence** and **Fluency** (LLM-as-judge). Deselect Tool Call
   Accuracy — tools don't execute during portal evaluation.
5. Submit and review the per-criterion scores and per-row reasoning in the report.

## Interpreting results

A low score is a signal, not a conclusion: the score says something went wrong, the
judge's reasoning says why, and the trace (Challenge 2) says where. The `ground_truth`
field also lets you add correctness-based evaluators if you want to track classification
accuracy and gate correctness over time.
