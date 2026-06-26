# Challenge 0 — Setup

**Goal:** provision Microsoft Foundry, deploy a model, and verify authentication so the
rest of the scenario can run.

## What you provision
- A **Microsoft Foundry** project (the project endpoint URL is your `PROJECT_CONNECTION_STRING`).
- A **chat model deployment** (default `gpt-5.4`) — its name is `MODEL_DEPLOYMENT_NAME`.
- **Application Insights** for GenAI tracing (Challenge 2).

## Steps

1. **Authenticate.**
   ```bash
   az login
   ```

2. **Provision everything with the bundled script.** It creates the Foundry account,
   project, and model deployment, plus Log Analytics and Application Insights, and writes
   a ready-to-use `.env` at the repo root:
   ```bash
   ./challenge-0-setup/deploy.sh
   # override region/model if needed:
   # LOCATION=westeurope MODEL_DEPLOYMENT_NAME=gpt-4o-mini ./challenge-0-setup/deploy.sh
   ```
   The script also makes a best-effort attempt to grant your account the **Azure AI User**
   role on the Foundry resource. If agent calls later return 403, add that role manually in
   the portal.

   *(If you'd rather provision manually:* create a Foundry project and a `gpt-5.4`
   deployment in [ai.azure.com](https://ai.azure.com), then
   `cp challenge-0-setup/.env.template .env` and fill in `PROJECT_CONNECTION_STRING`,
   `MODEL_DEPLOYMENT_NAME`, and `APPLICATIONINSIGHTS_CONNECTION_STRING`.)*

## Verify

You are ready for Challenge 1 when:
- `.env` contains a non-empty `PROJECT_CONNECTION_STRING` and `MODEL_DEPLOYMENT_NAME`.
- `az account show` returns your subscription.
- `pip install -r requirements.txt` completes.
