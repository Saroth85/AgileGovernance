# AI Agile Delivery Governance — Microsoft Foundry scenario

A governed two-agent system built on **Microsoft Foundry**, in the exact idiom of the
[FrontierWeekHack](https://github.com/microsoft/FrontierWeekHack) scenarios (Factory /
Claims / Call Center). Drop this folder into a fork of that repo, or run it standalone
after provisioning Foundry.

Two agents with opposite cognitive jobs, plus a quality gate that **branches**:

- **Backlog Governance Agent** — evaluates a user story against INVEST + Definition of
  Ready and returns a structured verdict (`gate_pass`, `issues`, INVEST scores). It only
  judges; it never plans.
- **Sprint Planning Agent** — takes an *approved* story and produces a plan (story points,
  tasks, DoD, risks). It only plans; it never re-judges.

```
story → Backlog Governance Agent → gate ──fail──▶ feedback for refinement (stop)
                                     │
                                    pass
                                     ▼
                            Sprint Planning Agent → plan ready for the team
```

Both agents are **created in the Foundry Agent Service** (`client.agents.create_version`
with `PromptAgentDefinition`), run through the **Responses API** with `agent_reference`,
traced into **Application Insights**, evaluated with **LLM-as-judge** in the portal, and
orchestrated by a deployable **workflow agent** invocable by name.

## The 5 challenges

| # | Challenge | File | What runs on Foundry |
|---|-----------|------|----------------------|
| 0 | Setup | `challenge-0-setup/.env.template` | Provision Foundry + model + App Insights |
| 1 | Build agents | `challenge-1-build/agents.py` | Creates the two agents + `check_story_quality` tool |
| 2 | Monitor | `challenge-2-monitor/monitor.py` | `AIProjectInstrumentor` → GenAI traces in App Insights |
| 3 | Evaluate | `challenge-3-evaluate/eval_portal.jsonl` | Portal LLM-as-judge over the governance golden set |
| 4 | Workflow | `challenge-4-deploy/deploy.py` | Gate-branching orchestration + deployable workflow agent |

## Run it on Foundry

```bash
# 0 — provision (uses the FrontierWeekHack deploy.sh; or your own Foundry project)
#     then fill in .env from the deploy output
cp challenge-0-setup/.env.template .env

pip install -r requirements.txt
az login          # DefaultAzureCredential uses this session

# 1 — build & test the two agents (they appear in the Foundry portal)
python challenge-1-build/agents.py

# 2 — enable tracing and emit a traced agent call
python challenge-2-monitor/monitor.py

# 3 — evaluate in the portal: Build → Evaluations → Create → Agent
#     (target backlog-governance-agent, upload challenge-3-evaluate/eval_portal.jsonl,
#      keep Coherence + Fluency; the ground_truth field also enables correctness checks)

# 4 — orchestrate with the gate branch + deploy the workflow agent
python challenge-4-deploy/deploy.py
```

> `.env` uses `PROJECT_CONNECTION_STRING` (the project endpoint URL,
> `https://<resource>.services.ai.azure.com/api/projects/<project>`) and
> `MODEL_DEPLOYMENT_NAME` (default `gpt-5.4`) — same variables as the lab.

## Offline check (no Foundry)

The gate logic is a pure function and is unit-tested without any cloud calls:

```bash
pytest -q
```

## Documentation & presentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — architecture deep-dive (the gate, the
  two agents, how it maps to Foundry).
- Per-challenge guides: [0](challenge-0-setup/README.md) ·
  [1](challenge-1-build/README.md) · [2](challenge-2-monitor/README.md) ·
  [3](challenge-3-evaluate/README.md) · [4](challenge-4-deploy/README.md).
- [`presentation/VIDEO_SCRIPT.md`](presentation/VIDEO_SCRIPT.md) — narration for the demo
  video, with slide cues.
- `presentation/AI-Agile-Delivery-Governance-Overview.docx` — the project overview document.
- `presentation/AI-Agile-Delivery-Governance-Slides.pptx` — the slide deck.

## Files

```
agile-governance/
├─ quality_rules.py                 # shared INVEST/DoR logic (tool + tests)
├─ challenge-0-setup/               # .env.template + setup guide
├─ challenge-1-build/agents.py      # the two Foundry agents + tool
├─ challenge-1-build/stories_data.json
├─ challenge-2-monitor/monitor.py   # GenAI tracing into App Insights
├─ challenge-3-evaluate/eval_portal.jsonl   # labelled golden set
├─ challenge-4-deploy/deploy.py     # gate-branching orchestration + workflow agent
├─ docs/ARCHITECTURE.md
├─ presentation/                    # video script, overview doc, slide deck
├─ tests/test_quality_rules.py
├─ cleanup.sh                       # delete the deployed agents
└─ requirements.txt
```

## License

MIT — see [LICENSE](LICENSE).
