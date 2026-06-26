# Challenge 4 — Workflow (orchestrate, deploy, invoke)

**Goal:** orchestrate the two agents into an automated pipeline, then deploy it as a
workflow agent you can invoke by name.

## Part A — Python orchestration with the quality gate

`deploy.py` ensures both agents are deployed, then runs the governed pipeline over every
story. **The gate branches:** a story that passes goes to the Sprint Planning Agent; a
story that fails is returned with explicit feedback and stops. This branch — not a linear
hand-off — is what makes it a *governed* workflow.

The run prints a report with the **gate pass-rate**, a metric that doubles as a quality KPI
for the backlog.

## Part B — Deployable workflow agent

A `WorkflowAgentDefinition` is created via the SDK (`allow_preview=True`), wiring the two
agents into a sequential workflow that appears in the Foundry portal under **Build →
Agents** (kind: workflow) and can be invoked by name through the Responses API.

```
governance step → planning step → end
```

The conditional gate lives in Part A's orchestration. To make the branch declarative,
open the workflow in the portal's visual builder and add a **Condition** node on
`gate_pass` between the two `InvokeAzureAgent` steps — pass routes to planning, fail routes
to a feedback/terminal node.

## Run

```bash
python challenge-4-deploy/deploy.py
```

This deploys the agents (if needed), runs the gate-branching pipeline, creates the workflow
agent, and invokes it once via a background poll.

## Verify

In the Foundry portal → **Build → Agents**, you should see `backlog-governance-agent`,
`sprint-planning-agent`, and the `agile-delivery-governance-workflow` (kind: workflow).

## Clean up

```bash
./cleanup.sh   # deletes the agents created by this scenario
```
