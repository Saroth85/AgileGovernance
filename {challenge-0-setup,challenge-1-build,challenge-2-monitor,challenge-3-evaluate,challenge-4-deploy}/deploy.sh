#!/bin/bash
set -euo pipefail

# =============================================================================
# AI Agile Delivery Governance — Infrastructure Deployment
# Provisions: Microsoft Foundry (account + project + model), Log Analytics,
#             Application Insights, and writes a ready-to-use .env at the repo root.
# Region default: swedencentral
#
# Usage:
#   az login
#   ./challenge-0-setup/deploy.sh                 # from the repo root
#   LOCATION=westeurope ./challenge-0-setup/deploy.sh   # override region
# =============================================================================

# --- Azure CLI extensions ----------------------------------------------------
az config set extension.use_dynamic_install=yes_without_prompt --only-show-errors >/dev/null 2>&1 || true
az extension add --name application-insights --only-show-errors >/dev/null 2>&1 || true

# --- Configuration -----------------------------------------------------------
SUFFIX="${SUFFIX:-$(openssl rand -hex 4)}"
RESOURCE_GROUP="${RESOURCE_GROUP:-agile-gov-rg-$SUFFIX}"
LOCATION="${LOCATION:-swedencentral}"
FOUNDRY_RESOURCE_NAME="${FOUNDRY_RESOURCE_NAME:-agile-gov-foundry-$SUFFIX}"
PROJECT_NAME="${PROJECT_NAME:-agile-governance-project}"
MODEL_DEPLOYMENT_NAME="${MODEL_DEPLOYMENT_NAME:-gpt-5.4}"
MODEL_NAME="${MODEL_NAME:-gpt-5.4}"
MODEL_VERSION="${MODEL_VERSION:-2026-03-05}"
LOG_ANALYTICS_NAME="${LOG_ANALYTICS_NAME:-agile-gov-logs-$SUFFIX}"
APP_INSIGHTS_NAME="${APP_INSIGHTS_NAME:-agile-gov-insights-$SUFFIX}"
WORKFLOW_AGENT_NAME="${WORKFLOW_AGENT_NAME:-agile-delivery-governance-workflow}"

# --- Tags --------------------------------------------------------------------
TAGS=("environment=hack" "project=agile-delivery-governance")
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tags)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do TAGS+=("$1"); shift; done
            ;;
        *) echo "Unknown argument: $1" >&2; echo "Usage: deploy.sh [--tags 'Key=Value' ...]" >&2; exit 1 ;;
    esac
done

echo "=============================================="
echo "  AI Agile Delivery Governance — Deploy"
echo "=============================================="
echo "Suffix:            $SUFFIX"
echo "Resource Group:    $RESOURCE_GROUP"
echo "Location:          $LOCATION"
echo "Foundry Resource:  $FOUNDRY_RESOURCE_NAME"
echo "Project:           $PROJECT_NAME"
echo "Model Deployment:  $MODEL_DEPLOYMENT_NAME ($MODEL_NAME $MODEL_VERSION)"
echo ""

# --- Resource Group ----------------------------------------------------------
echo ">>> Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --tags "${TAGS[@]}" --output none

# --- Foundry account (AIServices) --------------------------------------------
echo ">>> Creating Microsoft Foundry account (AIServices)..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
az rest --method PUT \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY_RESOURCE_NAME?api-version=2026-03-01" \
    --body "{\"kind\": \"AIServices\", \"sku\": {\"name\": \"S0\"}, \"location\": \"$LOCATION\", \"identity\": {\"type\": \"SystemAssigned\"}, \"properties\": {\"customSubDomainName\": \"$FOUNDRY_RESOURCE_NAME\", \"publicNetworkAccess\": \"Enabled\", \"allowProjectManagement\": true}}" \
    --output none || true

echo ">>> Waiting for the Foundry account to reach Succeeded state..."
for i in $(seq 1 36); do
    PROV_STATE=$(az cognitiveservices account show --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.provisioningState" -o tsv 2>/dev/null || echo "Pending")
    if [ "$PROV_STATE" = "Succeeded" ]; then echo "    OK — provisioning complete."; break
    elif [ "$PROV_STATE" = "Failed" ]; then echo "ERROR: Foundry account provisioning failed. Check the Azure portal."; exit 1; fi
    echo "    State: $PROV_STATE — retrying in 10s... ($i/36)"; sleep 10
done

FOUNDRY_RESOURCE_ID=$(az cognitiveservices account show --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
az resource update --ids "$FOUNDRY_RESOURCE_ID" --set properties.disableLocalAuth=false --output none || true
az resource update --ids "$FOUNDRY_RESOURCE_ID" --set properties.allowProjectManagement=true --output none

DISABLE_LOCAL_AUTH=$(az cognitiveservices account show --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --query properties.disableLocalAuth -o tsv)
if [ "$DISABLE_LOCAL_AUTH" = "true" ]; then
    echo "NOTE: API key auth is disabled by tenant policy — the code uses DefaultAzureCredential (Entra ID), so this is fine."
fi

# --- Foundry project ---------------------------------------------------------
echo ">>> Creating Foundry project..."
az cognitiveservices account project create --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --project-name "$PROJECT_NAME" --location "$LOCATION" --output none

# --- Model deployment --------------------------------------------------------
echo ">>> Deploying model: $MODEL_NAME ($MODEL_VERSION)..."
az cognitiveservices account deployment create \
    --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$MODEL_DEPLOYMENT_NAME" --model-name "$MODEL_NAME" --model-version "$MODEL_VERSION" \
    --model-format OpenAI --sku-capacity 10 --sku-name GlobalStandard --output none

# --- Log Analytics + Application Insights -------------------------------------
echo ">>> Creating Log Analytics workspace..."
az monitor log-analytics workspace create --resource-group "$RESOURCE_GROUP" --workspace-name "$LOG_ANALYTICS_NAME" --location "$LOCATION" --output none
LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show --resource-group "$RESOURCE_GROUP" --workspace-name "$LOG_ANALYTICS_NAME" --query id -o tsv)

echo ">>> Creating Application Insights (linked to Log Analytics)..."
az monitor app-insights component create --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --workspace "$LOG_ANALYTICS_ID" --output none
APP_INSIGHTS_CONN_STRING=$(az monitor app-insights component show --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --query connectionString -o tsv)
APP_INSIGHTS_INSTRUMENTATION_KEY=$(az monitor app-insights component show --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --query instrumentationKey -o tsv)
APP_INSIGHTS_RESOURCE_ID=$(az monitor app-insights component show --app "$APP_INSIGHTS_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

echo ">>> Connecting Application Insights to the Foundry account..."
az rest --method PUT \
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY_RESOURCE_NAME/connections/appinsights-conn?api-version=2025-06-01" \
    --body "{\"properties\": {\"category\": \"AppInsights\", \"target\": \"$APP_INSIGHTS_RESOURCE_ID\", \"authType\": \"ApiKey\", \"credentials\": {\"key\": \"$APP_INSIGHTS_CONN_STRING\"}, \"isSharedToAll\": true, \"metadata\": {\"ApiType\": \"Azure\", \"ResourceId\": \"$APP_INSIGHTS_RESOURCE_ID\"}}}" \
    --output none || echo "NOTE: could not auto-link App Insights — you can connect it later from the Foundry portal."

# --- Best-effort role assignment (so you can create/run agents) ---------------
# Requires you to have Owner/User Access Administrator. If it fails, assign the
# "Azure AI User" role to your account on the Foundry resource in the portal.
echo ">>> Granting your account the Azure AI User role on the Foundry resource..."
CURRENT_USER_OID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
if [ -n "$CURRENT_USER_OID" ]; then
    az role assignment create --assignee-object-id "$CURRENT_USER_OID" --assignee-principal-type User \
        --role "Azure AI User" --scope "$FOUNDRY_RESOURCE_ID" --output none 2>/dev/null \
        || echo "NOTE: role assignment skipped/failed — if agent calls return 403, add 'Azure AI User' to your account on $FOUNDRY_RESOURCE_NAME."
fi

# --- Retrieve endpoint / project connection ----------------------------------
echo ">>> Retrieving Foundry endpoint and project connection..."
FOUNDRY_ENDPOINT=$(az cognitiveservices account show --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.endpoint" -o tsv)
PROJECT_CONNECTION_STRING=$(az cognitiveservices account project show --name "$FOUNDRY_RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --project-name "$PROJECT_NAME" --query "properties.endpoints.\"AI Foundry API\"" -o tsv)

# --- Write .env at the repo root ---------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
echo ">>> Writing .env to: $ENV_FILE"

cat > "$ENV_FILE" << EOF
# =============================================================================
# AI Agile Delivery Governance — Environment Variables
# Auto-generated by deploy.sh on $(date)
# =============================================================================

AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
RESOURCE_GROUP=$RESOURCE_GROUP

# Microsoft Foundry
FOUNDRY_RESOURCE_NAME=$FOUNDRY_RESOURCE_NAME
PROJECT_NAME=$PROJECT_NAME
FOUNDRY_ENDPOINT=$FOUNDRY_ENDPOINT
PROJECT_CONNECTION_STRING=$PROJECT_CONNECTION_STRING
MODEL_DEPLOYMENT_NAME=$MODEL_DEPLOYMENT_NAME

# Application Insights & Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_CONN_STRING
APPINSIGHTS_INSTRUMENTATION_KEY=$APP_INSIGHTS_INSTRUMENTATION_KEY

# Tracing (Challenge 2) — must be set before importing azure.ai.projects
AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true

# Challenge 4 — workflow agent name
WORKFLOW_AGENT_NAME=$WORKFLOW_AGENT_NAME
EOF

echo ""
echo "=============================================="
echo "  DEPLOYMENT COMPLETE"
echo "=============================================="
echo "  .env written to: $ENV_FILE"
echo ""
echo "  Next:"
echo "    pip install -r requirements.txt"
echo "    python challenge-1-build/agents.py"
echo "    python challenge-2-monitor/monitor.py"
echo "    python challenge-4-deploy/deploy.py"
echo ""
