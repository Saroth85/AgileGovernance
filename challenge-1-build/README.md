# Challenge 1 — Build the two agents

**Goal:** create two purpose-built agents in the Foundry Agent Service, each with its own
system prompt, tools, and domain grounding.

## The two agents

| Agent | Cognitive job | Tool | Output |
|-------|---------------|------|--------|
| **Backlog Governance Agent** | *Evaluate / critique* a user story against INVEST + Definition of Ready | `check_story_quality` | Structured JSON verdict (`gate_pass`, `overall_score`, `invest`, `issues`) |
| **Sprint Planning Agent** | *Generate a plan* for an already-approved story | — | Structured JSON plan (`story_points`, `tasks`, `definition_of_done`, `risks`) |

The separation is deliberate: **Agent 1 only judges, Agent 2 only plans.** Agent 1 never
proposes tasks; Agent 2 never re-evaluates quality. That clean split is what makes this a
real multi-agent system rather than one prompt cut in two.

## How it works on Foundry

Each agent is created with `client.agents.create_version(...)` and a
`PromptAgentDefinition` — this registers a versioned agent that appears in the Foundry
portal under **Build → Agents**. The agent runs through the **Responses API**: a
conversation is created, the request is sent with an `agent_reference`, and any tool calls
are resolved in a function-call loop (the Governance Agent calls `check_story_quality`,
which runs the deterministic INVEST/DoR checks in `quality_rules.py`).

## Run

```bash
python challenge-1-build/agents.py
```

You should see the Governance Agent classify each sample story as `PASS` or `REJECT` with
its detected issues, then the Planning Agent produce a plan for an approved story. Both
agents remain deployed and visible in the portal.

## Grounding

The agents are grounded on the INVEST criteria, the team Definition of Ready, and the
Definition of Done (encoded in the prompts and the `check_story_quality` rules). To scale
the grounding, promote these to a `file_search` tool or an Azure AI Search index and
attach it to the agent definition.
