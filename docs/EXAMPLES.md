# Examples & prompts

Concrete inputs and outputs so the project is reusable, not just readable.

## System prompts (abridged)

**Backlog Governance Agent (Agent 1)**
```
You are the Backlog Governance Agent. Your ONLY job is to EVALUATE a single user story
against INVEST and the Definition of Ready. You do NOT propose tasks or plans. For each
story, call check_story_quality(story_id), then reason over the result. Use the canonical
issue labels. Set gate_pass=true only if overall_score >= threshold AND no INVEST
dimension is below the floor. Respond with ONE JSON object only.
```

**Sprint Planning Agent (Agent 2)**
```
You are the Sprint Planning Agent. You receive a story that has ALREADY passed the gate.
Take its quality as given — do NOT re-evaluate it. Produce a delivery plan: story-point
estimate with rationale, task breakdown, Definition of Done, risks, and sprint-goal
contribution. Respond with ONE JSON object only.
```

## Sample tool call

The Governance Agent calls the grounded tool:
```
check_story_quality(story_id="STR-003")
```

## A full verdict — story that PASSES the gate

> *"As a back-office operator, I want to filter executed orders by settlement date, so that
> I can reconcile end-of-day positions. Acceptance criteria: Given a settlement date, When I
> apply the filter, Then only orders settling on that date are shown."*

```json
{
  "classification": "ready",
  "invest": { "independent": 5, "negotiable": 4, "valuable": 5,
              "estimable": 4, "small": 5, "testable": 5 },
  "issues": [],
  "overall_score": 100.0,
  "gate_pass": true,
  "gate_status": "pass",
  "dor_checklist": { "has_user_role": true, "has_user_value": true,
                     "has_acceptance_criteria": true, "is_appropriately_small": true },
  "policy": { "team": "default", "threshold": 70, "min_invest": 3, "review_band": 0 }
}
```

## A full verdict — story that FAILS the gate

> *"We need a fast and user-friendly dashboard that shows everything about trades and also
> exports data and also sends email alerts."*

```json
{
  "classification": "needs_refinement",
  "invest": { "independent": 5, "negotiable": 4, "valuable": 2,
              "estimable": 4, "small": 5, "testable": 1 },
  "issues": [
    "missing acceptance criteria",
    "missing user role",
    "missing user value",
    "not testable",
    "vague or ambiguous wording"
  ],
  "overall_score": 35.0,
  "gate_pass": false,
  "gate_status": "reject",
  "dor_checklist": { "has_user_role": false, "has_user_value": false,
                     "has_acceptance_criteria": false, "is_appropriately_small": true },
  "policy": { "team": "default", "threshold": 70, "min_invest": 3, "review_band": 0 }
}
```

The Planning Agent never runs on this story. Instead the workflow returns the `issues` list
as refinement feedback and stops.

## Human-in-the-loop: the same story, two team policies

The Definition of Ready is configurable per team (`config/dor_policy.json`). A borderline
story routes differently depending on the team's `review_band`:

> *"I want the netting logic so that settlement nets correctly, but it depends on the Tobin
> tax module."*  (score 61)

| Team | threshold | review_band | `gate_status` |
|------|-----------|-------------|---------------|
| `default` | 70 | 0 | **reject** (binary) |
| `platform` | 65 | 8 | **review** → sent to a human |

With a non-zero `review_band`, scores within the band around the threshold are not
auto-decided — they are flagged for human review. This is the seed of the human-in-the-loop
mode described in [ROADMAP.md](./ROADMAP.md).

## Configuring a team

```jsonc
// config/dor_policy.json
"teams": {
  "back-office": { "gate_threshold": 75, "min_invest": 3, "review_band": 0 },
  "platform":    { "gate_threshold": 65, "review_band": 8 }
}
```
Then in code: `analyse_story(story_text, team="platform")`.
