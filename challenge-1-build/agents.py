"""
Challenge 1: Build Agents — AI Agile Delivery Governance.

Backlog Governance Agent (evaluates a user story against INVEST + Definition of Ready)
and Sprint Planning Agent (plans an approved story). Both are created in Microsoft
Foundry via the Agent Service and run through the Responses API — the same pattern the
FrontierWeekHack scenarios use.

Usage:
    python agents.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from quality_rules import analyse_story  # noqa: E402


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
STORIES_PATH = Path(__file__).resolve().parent / "stories_data.json"


def _load_stories() -> list[dict]:
    with open(STORIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("stories", [])


# =============================================================================
# Tool Function: check_story_quality
# The Backlog Governance Agent calls this to get a deterministic INVEST / DoR
# analysis, then reasons over the result. Analogous to the lab's assess_claim.
# =============================================================================

def check_story_quality(story_id: str) -> str:
    """Run INVEST / Definition-of-Ready checks on a story and return JSON."""
    story = next((s for s in _load_stories() if s["story_id"] == story_id), None)
    if not story:
        return json.dumps({"error": f"Story '{story_id}' not found"})
    analysis = analyse_story(story["description"])
    return json.dumps({"story_id": story_id, "title": story["title"], **analysis}, indent=2)


CHECK_STORY_TOOL = FunctionTool(
    name="check_story_quality",
    description=(
        "Run INVEST and Definition-of-Ready checks on a user story. Returns the INVEST "
        "scores, detected issues, an overall score and whether it passes the quality gate."
    ),
    parameters={
        "type": "object",
        "properties": {
            "story_id": {"type": "string", "description": "The story ID, e.g. 'STR-001'"}
        },
        "required": ["story_id"],
        "additionalProperties": False,
    },
    strict=False,
)


def _parse_json(text: str) -> dict:
    """Parse a model reply that should be a single JSON object (strip code fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
    return json.loads(cleaned)


# =============================================================================
# Backlog Governance Agent (Agent 1) — evaluate / critique
# =============================================================================

class BacklogGovernanceAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are the Backlog Governance Agent for an Agile delivery team.
        Your ONLY job is to EVALUATE a single user story. You do NOT propose tasks,
        estimates, or any plan — evaluation and critique only.

        Evaluate the story TEXT directly against INVEST and the Definition of Ready, and
        always return the final JSON verdict. If a story_id is provided AND the
        check_story_quality tool is available, you MAY call it first to ground your
        analysis; if no tool result is available, evaluate from the story text alone.
        Never stop at a tool call — always produce the verdict.

        Use these canonical issue labels when they apply: "missing acceptance criteria",
        "vague or ambiguous wording", "missing user value", "missing user role",
        "too large, not small", "not testable", "unstated dependency".

        Respond with ONE JSON object ONLY (no prose, no markdown fences) with exactly:
        {
          "story_id": str,
          "classification": "ready" | "needs_refinement",
          "overall_score": number,            // 0-100
          "gate_pass": boolean,
          "invest": {"independent":int,"negotiable":int,"valuable":int,
                     "estimable":int,"small":int,"testable":int},   // 0-5 each
          "issues": [str],
          "rationale": str
        }
        """

        self.agent = self.client.agents.create_version(
            agent_name="backlog-governance-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
                tools=[CHECK_STORY_TOOL],
            ),
        )
        return self.agent

    def assess(self, story_id: str) -> dict:
        """Evaluate one story and return the parsed verdict."""
        conversation = self.openai.conversations.create()
        agent_ref = {"agent_reference": {"name": self.agent.name, "type": "agent_reference"}}

        response = self.openai.responses.create(
            input=f"Evaluate story {story_id}. Call check_story_quality first.",
            conversation=conversation.id,
            extra_body=agent_ref,
        )

        while any(item.type == "function_call" for item in response.output):
            outputs = []
            for item in response.output:
                if item.type == "function_call" and item.name == "check_story_quality":
                    args = json.loads(item.arguments)
                    result = check_story_quality(args["story_id"])
                    outputs.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=result,
                        )
                    )
            response = self.openai.responses.create(
                input=outputs, conversation=conversation.id, extra_body=agent_ref
            )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return _parse_json(response.output_text)

    def cleanup(self):
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name, agent_version=self.agent.version
            )
        if self.client:
            self.client.close()


# =============================================================================
# Sprint Planning Agent (Agent 2) — generate a plan for an approved story
# =============================================================================

class SprintPlanningAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are the Sprint Planning Agent for an Agile delivery team.
        You receive a user story that has ALREADY been APPROVED by the quality gate.
        Take its quality as given — do NOT re-evaluate it. Produce a delivery plan.

        Respond with ONE JSON object ONLY (no prose, no markdown fences) with exactly:
        {
          "story_points": int,                 // Fibonacci 1,2,3,5,8,13
          "estimate_rationale": str,
          "tasks": [str],                       // small, non-overlapping
          "definition_of_done": [str],
          "risks": [str],
          "sprint_goal_contribution": str
        }
        """

        self.agent = self.client.agents.create_version(
            agent_name="sprint-planning-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
            ),
        )
        return self.agent

    def plan(self, story_text: str) -> dict:
        conversation = self.openai.conversations.create()
        agent_ref = {"agent_reference": {"name": self.agent.name, "type": "agent_reference"}}
        response = self.openai.responses.create(
            input=f"Plan this approved user story:\n\n{story_text}",
            conversation=conversation.id,
            extra_body=agent_ref,
        )
        self.openai.conversations.delete(conversation_id=conversation.id)
        return _parse_json(response.output_text)

    def cleanup(self):
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name, agent_version=self.agent.version
            )
        if self.client:
            self.client.close()


# =============================================================================
# Main — test both agents
# =============================================================================

def main():
    if not PROJECT_CONNECTION_STRING:
        print("PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    print("=== Backlog Governance Agent ===")
    gov = BacklogGovernanceAgent()
    gov.create()
    print(f"Created: {gov.agent.name} (version {gov.agent.version})\n")

    for story in _load_stories():
        verdict = gov.assess(story["story_id"])
        flag = "PASS" if verdict.get("gate_pass") else "REJECT"
        print(f"[{flag}] {story['story_id']} score={verdict.get('overall_score')} "
              f"issues={verdict.get('issues')}")

    print("\n=== Sprint Planning Agent ===")
    plan_agent = SprintPlanningAgent()
    plan_agent.create()
    print(f"Created: {plan_agent.agent.name} (version {plan_agent.agent.version})\n")

    good = _load_stories()[0]
    plan = plan_agent.plan(good["description"])
    print(f"Plan for {good['story_id']}: {plan.get('story_points')} SP, "
          f"{len(plan.get('tasks', []))} tasks")

    # Agents remain in the portal. Uncomment to remove them:
    # gov.cleanup(); plan_agent.cleanup()


if __name__ == "__main__":
    main()
