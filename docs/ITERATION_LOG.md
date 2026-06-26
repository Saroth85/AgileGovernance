# Iteration log

How the agents and the gate were refined — the reasoning behind the current design, and
what each change fixed.

## 1. One agent → two agents with opposite jobs
**Change:** split a single "story assistant" into a Governance Agent (evaluate) and a
Planning Agent (plan).
**Why:** a single prompt that both judged and planned blurred its own criteria — it would
soften a critique to make the plan it had already written look reasonable. Separating
critique from creation made each agent's responsibility testable in isolation.

## 2. Free-text verdict → structured JSON output
**Change:** forced the Governance Agent to return a fixed JSON schema (`gate_pass`,
`overall_score`, `invest`, `issues`).
**Why:** free text could not be branched on or scored. Structured output made the gate
*actionable* (branch on a boolean) and the agent *measurable* (score issues against ground
truth). This single change unlocked Challenges 3 and 4.

## 3. Vibes-based judgement → a grounded tool
**Change:** added the `check_story_quality` tool running deterministic INVEST/DoR checks;
the agent reasons over the tool result rather than judging from the prompt alone.
**Why:** prompt-only judgement drifted run to run. Anchoring on a deterministic check made
the verdicts stable and reproducible, and gave the evaluation something concrete to score.

## 4. Binary gate → three-way gate with a review band
**Change:** introduced `gate_status` ∈ {pass, review, reject} with a configurable
`review_band`.
**Why:** a hard pass/fail line is wrong for borderline stories. A band around the threshold
routes near-miss scores to a human instead of guessing. With `review_band: 0` the behaviour
stays binary (and matches the reported metrics).

## 5. Hard-coded rules → per-team policy file
**Change:** moved the threshold, INVEST floor, vague-term list, size limits and review band
into `config/dor_policy.json`, selectable per team.
**Why:** a fixed Definition of Ready limits adoption — a regulated back-office team and an
early-discovery team need different bars. Making the policy configurable turned a rigid
checker into something teams can own.

## 6. Workflow tool → backlog-health instrument (human-in-the-loop)
**Change:** added a backlog-health dashboard (`dashboard/`) with a human review queue.
Stories the gate can't auto-decide (borderline scores, or hard blockers like an unstated
dependency) are routed to a person, whose decision is logged and appended as a new
ground-truth label.
**Why:** the reviewer's feedback was right — a gate that only auto-decides isn't trusted in
messy reality. Putting a human in the loop for the uncertain cases, and surfacing
pass-rate, recurring INVEST failures and review ageing, turns a per-story workflow into a
backlog-health instrument that closes the feedback loop.

## 7. Tool-dependent → tool-optional (evaluable in the portal)
**Change:** the Backlog Governance Agent now evaluates the story text directly and always
returns a verdict; `check_story_quality` is an optional accelerator used only when a
story_id and a tool runtime exist.
**Why:** a Foundry portal evaluation targeted at the governance agent revealed that the
portal does not execute custom Python tools — the agent called the tool, got no result, and
stopped without a verdict (empty output on all 15 cases). Making the agent self-sufficient
means it produces a complete verdict in the portal, so quality and correctness become
measurable there, while the tool path stays intact for production and SDK-based evaluation.
See [EVALUATION.md](./EVALUATION.md).

## Open issues found by evaluation (see RESULTS.md)
- **AC false positives:** the keyword-based acceptance-criteria check misses measurable
  criteria phrased without *Given/When/Then*. Next: add a measurable-criterion detector.
- **Dependency slips the gate:** an unstated dependency is currently a soft score penalty,
  not a hard blocker, so a not-ready story can clear a score-based gate. Next: make
  `unstated dependency` a must-not-have rule or route it to review.

## Metric history

| Iteration | Issue precision | Issue recall | Gate accuracy |
|-----------|-----------------|--------------|---------------|
| Current (config-driven, threshold 70) | 0.91 | 0.98 | 0.93 |

Re-run `python challenge-3-evaluate/run_local_eval.py` after any change to update this row.
