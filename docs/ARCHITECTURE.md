# Architecture

## One sentence

A governed two-agent pipeline on Microsoft Foundry that turns a raw user story into either
*ready-to-plan work* or *actionable refinement feedback*, with a quality gate in between,
full observability, and measured output quality.

## The flow

```
                         New user story
                               │
                               ▼
                ┌──────────────────────────────┐
                │   Backlog Governance Agent     │   evaluate / critique
                │   (INVEST + Definition of Ready)│
                └──────────────────────────────┘
                               │
                  structured verdict (gate_pass, score, issues)
                               │
                          ┌────┴────┐
                     fail │  GATE   │ pass
                          ▼         ▼
              feedback for     ┌──────────────────────────┐
              refinement       │   Sprint Planning Agent   │   generate plan
              (stop)           │   (Definition of Done)     │
                               └──────────────────────────┘
                                          │
                                          ▼
                              plan ready for the team
```

## Why two agents

The two agents have **opposite cognitive jobs**: one *critiques*, the other *creates*.
Keeping them separate is what makes this a genuine multi-agent system instead of a single
prompt split in two. The Governance Agent must never propose tasks; the Planning Agent
must never re-judge quality. Each is independently testable, independently traceable, and
independently evaluable.

## Why a gate, not a pipe

A linear hand-off (story → critique → plan) would plan stories that aren't ready. The gate
**branches** on the Governance Agent's `gate_pass` decision:

- **Pass** → the story flows to planning and becomes ready-to-build work.
- **Fail** → the story is returned with explicit, atomic issues and stops.

The branch makes the system *governed*: bad stories never reach planning, and the gate
pass-rate becomes a measurable quality signal for the backlog.

## How it maps to Microsoft Foundry

| Concern | Foundry capability | In this repo |
|---------|--------------------|--------------|
| Purpose-built agents | Agent Service (`PromptAgentDefinition`, `create_version`) | `challenge-1-build/agents.py` |
| Tools + grounding | `FunctionTool` + domain rules | `check_story_quality`, `quality_rules.py` |
| Observability | `AIProjectInstrumentor` → App Insights | `challenge-2-monitor/monitor.py` |
| Quality evaluation | LLM-as-judge over a dataset | `challenge-3-evaluate/eval_portal.jsonl` |
| Orchestration | Responses API + `WorkflowAgentDefinition` | `challenge-4-deploy/deploy.py` |

## Structured output is the linchpin

The Governance Agent returns a JSON verdict with a schema. That single design choice does
double duty:

1. It makes the **gate actionable** — the workflow can branch on `gate_pass`.
2. It makes the agent **measurable** — the evaluation can score `issues` and the gate
   decision against ground truth.

Without structured output you have neither a reliable gate nor a meaningful evaluation.

## A system that is itself governed

The deeper idea: this is a governance system that is *itself* governed. Every agent call is
traced; every agent decision is evaluated against a labelled set. You don't just trust the
output because it sounds confident — you trust it because it is measured.
