# Challenge 0 — Setup

**Goal:** provision Microsoft Foundry, deploy a model, and verify authentication so the
rest of the scenario can run.

## What you provision
- A **Microsoft Foundry** project (the project endpoint URL is your `PROJECT_CONNECTION_STRING`).
- A **chat model deployment** (default `gpt-5.4`) — its name is `MODEL_DEPLOYMENT_NAME`.
- **Application Insights** for GenAI tracing (Challenge 2).

## Steps

1. **Provision the infrastructure.** The fastest path is the FrontierWeekHack deploy
   script, which creates Foundry + model + Log Analytics + App Insights in one go:
   ```bash
   # from a fork of microsoft/FrontierWeekHack
   ./claims/challenge-0-setup/deploy.sh
   ```
   Or create a Foundry project and a `gpt-5.4` deployment manually in
   [ai.azure.com](https://ai.azure.com).

2. **Fill in `.env`** at the repo root from the deploy output:
   ```bash
   cp challenge-0-setup/.env.template .env
   ```
   The critical values are `PROJECT_CONNECTION_STRING` (the project endpoint URL of the
   form `https://<resource>.services.ai.azure.com/api/projects/<project>`),
   `MODEL_DEPLOYMENT_NAME`, and `APPLICATIONINSIGHTS_CONNECTION_STRING`.

3. **Authenticate.** The SDK uses `DefaultAzureCredential`, which picks up your CLI login:
   ```bash
   az login
   ```

4. **Assign the Foundry User role** on the project to your account so you can create and
   run agents.

## Verify

You are ready for Challenge 1 when:
- `.env` contains a non-empty `PROJECT_CONNECTION_STRING` and `MODEL_DEPLOYMENT_NAME`.
- `az account show` returns your subscription.
- `pip install -r requirements.txt` completes.
