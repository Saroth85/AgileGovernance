#!/bin/bash
set -euo pipefail
# Deletes the agents created by this scenario from your Foundry project.
python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv(".env")
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

endpoint = os.environ["PROJECT_CONNECTION_STRING"]
client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential(), allow_preview=True)
targets = {"backlog-governance-agent", "sprint-planning-agent",
           "agile-delivery-governance-workflow", "tracing-test-agent"}
for a in client.agents.list():
    if a.name in targets:
        try:
            client.agents.delete_version(agent_name=a.name, agent_version=a.version)
            print("deleted", a.name, a.version)
        except Exception as e:
            print("skip", a.name, e)
client.close()
PY
