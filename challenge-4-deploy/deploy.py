"""
Challenge 4: Production Workflow — AI Agile Delivery Governance.

Part A: Python orchestration of the two agents with the QUALITY GATE that BRANCHES —
        a story that passes goes to planning; a story that fails is returned with
        feedback and stops. This is what makes it a governed workflow, not a pipe.

Part B: A deployable workflow agent created via WorkflowAgentDefinition, visible in the
        Foundry portal (Build -> Agents, kind: workflow) and invocable by name.

Usage:
    python deploy.py
"""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")

sys.path.insert(0, str(REPO_ROOT))
from quality_rules import analyse_story  # noqa: E402

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
STORIES_PATH = REPO_ROOT / "challenge-1-build" / "stories_data.json"

GOVERNANCE_AGENT_NAME = "backlog-governance-agent"
PLANNING_AGENT_NAME = "sprint-planning-agent"
WORKFLOW_AGENT_NAME = os.getenv("WORKFLOW_AGENT_NAME", "agile-delivery-governance-workflow")

GOVERNANCE_PROMPT = """
You are the Backlog Governance Agent. Evaluate ONE user story against INVEST and the
Definition of Ready. Do NOT plan or estimate. Respond with ONE JSON object only:
{"story_id":str,"classification":"ready"|"needs_refinement","overall_score":number,
"gate_pass":boolean,"issues":[str],"rationale":str}
"""

PLANNING_PROMPT = """
You are the Sprint Planning Agent. The story is already APPROVED — do not re-judge it.
Produce a plan. Respond with ONE JSON object only:
{"story_points":int,"estimate_rationale":str,"tasks":[str],
"definition_of_done":[str],"risks":[str],"sprint_goal_contribution":str}
"""


def _load_stories() -> list[dict]:
    with open(STORIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("stories", [])


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
    try:
        return json.loads(cleaned)
    except Exception:
        return {}


# -----------------------------------------------------------------------------
# Part A — deploy agents + Python orchestration with the gate branch
# -----------------------------------------------------------------------------

def ensure_agents_deployed():
    print("=== Step 1: Ensure agents are deployed ===")
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
    from azure.identity import DefaultAzureCredential

    check_tool = FunctionTool(
        name="check_story_quality",
        description="Run INVEST / Definition-of-Ready checks on a story.",
        parameters={
            "type": "object",
            "properties": {"story_id": {"type": "string"}},
            "required": ["story_id"],
        },
        strict=False,
    )

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    existing = {a.name for a in client.agents.list()}

    if GOVERNANCE_AGENT_NAME not in existing:
        client.agents.create_version(
            agent_name=GOVERNANCE_AGENT_NAME,
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=GOVERNANCE_PROMPT,
                tools=[check_tool],
            ),
        )
        print(f"  Deployed: {GOVERNANCE_AGENT_NAME}")
    else:
        print(f"  Found existing: {GOVERNANCE_AGENT_NAME}")

    if PLANNING_AGENT_NAME not in existing:
        client.agents.create_version(
            agent_name=PLANNING_AGENT_NAME,
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=PLANNING_PROMPT,
            ),
        )
        print(f"  Deployed: {PLANNING_AGENT_NAME}")
    else:
        print(f"  Found existing: {PLANNING_AGENT_NAME}")

    client.close()


def _run_agent(agent_name: str, input_text: str) -> str:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    openai_client = client.get_openai_client()
    agent_ref = {"agent_reference": {"name": agent_name, "type": "agent_reference"}}

    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        input=input_text, conversation=conversation.id, extra_body=agent_ref
    )
    text = response.output_text
    openai_client.conversations.delete(conversation_id=conversation.id)
    client.close()
    return text


def run_governed_pipeline() -> dict:
    """Run governance -> gate -> planning for every story. THE GATE BRANCHES."""
    print("\n=== Step 2: Governed pipeline (gate branches) ===")
    planned, rejected = [], []

    for story in _load_stories():
        # Pre-compute the deterministic analysis to embed (avoids tool-call loops here).
        analysis = analyse_story(story["description"])
        gov_input = (
            f"Story {story['story_id']}. INVEST/DoR analysis:\n"
            f"{json.dumps(analysis, indent=2)}\n\nReturn your JSON verdict."
        )
        verdict = _parse_json(_run_agent(GOVERNANCE_AGENT_NAME, gov_input))
        gate_pass = verdict.get("gate_pass", analysis["gate_pass"])

        if not gate_pass:  # <-- the branch
            rejected.append({"story_id": story["story_id"],
                             "issues": verdict.get("issues", analysis["issues"])})
            print(f"  [REJECT] {story['story_id']} -> sent back for refinement")
            continue

        plan = _parse_json(_run_agent(PLANNING_AGENT_NAME, story["description"]))
        planned.append({"story_id": story["story_id"], "plan": plan})
        print(f"  [PASS]   {story['story_id']} -> planned "
              f"({plan.get('story_points', '?')} SP)")

    return {"planned": planned, "rejected": rejected,
            "total": len(_load_stories())}


def print_report(report: dict):
    print("\n" + "=" * 60)
    print("AGILE DELIVERY GOVERNANCE — PIPELINE REPORT")
    print("=" * 60)
    print(f"  Stories assessed : {report['total']}")
    print(f"  Planned          : {len(report['planned'])}")
    print(f"  Sent back        : {len(report['rejected'])}")
    pass_rate = len(report["planned"]) / report["total"] if report["total"] else 0
    print(f"  Gate pass-rate   : {pass_rate:.0%}")
    print("=" * 60)


# -----------------------------------------------------------------------------
# Part B — deployable workflow agent (visible & invocable in the portal)
# -----------------------------------------------------------------------------

def create_workflow_agent(name: str = WORKFLOW_AGENT_NAME) -> str:
    """Create a WorkflowAgentDefinition agent: governance -> planning -> end.

    The conditional quality gate is enforced in Part A's Python orchestration. In the
    portal visual builder you can add a Condition node on `gate_pass` between the two
    InvokeAzureAgent steps to branch declaratively.
    """
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import WorkflowAgentDefinition
    from azure.identity import DefaultAzureCredential

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )

    workflow_yaml = (
        "kind: Workflow\n"
        f"name: {name}\n"
        "description: Agile delivery governance - backlog governance then sprint planning\n"
        "trigger:\n"
        "  kind: OnConversationStart\n"
        "  id: trigger_start\n"
        "  actions:\n"
        "    - kind: InvokeAzureAgent\n"
        "      id: step_governance\n"
        "      agent:\n"
        "        name: backlog-governance-agent\n"
        "      conversationId: =System.ConversationId\n"
        "      input:\n"
        '        messages: ""\n'
        "      output:\n"
        "        autoSend: true\n"
        "    - kind: InvokeAzureAgent\n"
        "      id: step_planning\n"
        "      agent:\n"
        "        name: sprint-planning-agent\n"
        "      conversationId: =System.ConversationId\n"
        "      input:\n"
        '        messages: ""\n'
        "      output:\n"
        "        autoSend: true\n"
        "    - kind: EndConversation\n"
        "      id: step_end\n"
    )

    result = client.agents.create_version(
        agent_name=name,
        definition=WorkflowAgentDefinition(workflow=workflow_yaml),
        description="Agile delivery governance workflow (SDK-created)",
    )
    print(f"  Workflow agent: {result.name} (version {result.version})")
    print("  Visible in Foundry portal -> Build -> Agents (kind: workflow)")
    client.close()
    return result.name


def run_portal_workflow(name: str):
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )
    openai_client = client.get_openai_client()
    story = _load_stories()[0]["description"]

    conversation = openai_client.conversations.create()
    resp = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": name, "type": "agent_reference"}},
        input=f"Evaluate then plan this story:\n\n{story}",
        background=True,
    )
    print(f"  Response ID: {resp.id}  status={resp.status}")
    for attempt in range(12):
        time.sleep(8)
        r = openai_client.responses.retrieve(resp.id)
        print(f"  [{attempt + 1}] status={r.status}")
        if r.status in ("completed", "failed", "cancelled"):
            if r.output_text:
                print("\nWorkflow output:\n" + r.output_text)
            break
    openai_client.conversations.delete(conversation_id=conversation.id)
    client.close()


def main():
    if not PROJECT_CONNECTION_STRING:
        print("PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    ensure_agents_deployed()
    report = run_governed_pipeline()
    print_report(report)

    print("\n" + "=" * 60)
    print("CREATING WORKFLOW AGENT VIA SDK")
    print("=" * 60)
    name = create_workflow_agent()

    print("\n" + "=" * 60)
    print("INVOKING WORKFLOW (BACKGROUND POLL)")
    print("=" * 60)
    run_portal_workflow(name)

    print("\nChallenge 4 complete — workflow deployed and invocable by name.")


if __name__ == "__main__":
    main()
