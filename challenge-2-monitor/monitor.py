"""
Challenge 2: Monitor with Application Insights — Agile Delivery Governance.
Enables GenAI tracing so agent calls appear in App Insights.

IMPORTANT: tracing env vars must be set BEFORE importing azure.ai.projects.

Usage:
    python monitor.py
"""

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


load_dotenv(_find_repo_root() / ".env")

if os.getenv("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING") != "true":
    print("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING is not 'true' in .env")
    print("   Add: AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true")
    sys.exit(1)

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
APPINSIGHTS_CONN_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")


def setup_tracing():
    print("=== Setting up tracing ===")
    from azure.ai.projects.telemetry import AIProjectInstrumentor

    AIProjectInstrumentor().instrument()
    print("AIProjectInstrumentor configured")

    if APPINSIGHTS_CONN_STRING:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=APPINSIGHTS_CONN_STRING,
            enable_live_metrics=True,
        )
        print("Azure Monitor exporter connected")
    else:
        print("APPLICATIONINSIGHTS_CONNECTION_STRING not set — export skipped")


def run_traced_agent_call():
    print("\n=== Running traced agent call ===")
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import PromptAgentDefinition
    from azure.identity import DefaultAzureCredential

    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )
    openai_client = client.get_openai_client()

    agent = client.agents.create_version(
        agent_name="tracing-test-agent",
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT_NAME,
            instructions=(
                "You are a backlog governance assistant. Briefly assess whether a user "
                "story is ready for sprint planning."
            ),
        ),
    )

    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        input=(
            "Assess readiness: 'As a back-office operator I want to filter executed "
            "orders by settlement date, so that I can reconcile positions. AC: Given a "
            "date, When I filter, Then matching orders show.'"
        ),
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"Agent responded: {response.output_text[:100]}...")

    openai_client.conversations.delete(conversation_id=conversation.id)
    client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
    client.close()


def verify_traces():
    print("\n=== Verifying traces ===")
    if not APPINSIGHTS_CONN_STRING:
        print("No App Insights connection string — check traces manually in the portal.")
        return
    print("Waiting 30s for traces to propagate...")
    time.sleep(30)
    print("Traces should be visible: Azure Portal -> Application Insights -> Transaction search")


def main():
    if not PROJECT_CONNECTION_STRING:
        print("PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)
    setup_tracing()
    run_traced_agent_call()
    verify_traces()
    print("\nMonitoring active. Check App Insights for the full GenAI trace view.")


if __name__ == "__main__":
    main()
