Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AzCliPath {
    $candidates = @(
        "C:/Program Files/Microsoft SDKs/Azure/CLI2/wbin/az.cmd",
        "C:/Program Files (x86)/Microsoft SDKs/Azure/CLI2/wbin/az.cmd"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    throw "Azure CLI not found. Install Azure CLI first."
}

function New-HexSuffix {
    $chars = "0123456789abcdef".ToCharArray()
    return (-join (1..8 | ForEach-Object { $chars[(Get-Random -Minimum 0 -Maximum 16)] }))
}

$az = Get-AzCliPath
$suffix = if ($env:SUFFIX) { $env:SUFFIX } else { New-HexSuffix }

$resourceGroup = if ($env:RESOURCE_GROUP) { $env:RESOURCE_GROUP } else { "agile-gov-rg-$suffix" }
$location = if ($env:LOCATION) { $env:LOCATION } else { "swedencentral" }
$foundryResourceName = if ($env:FOUNDRY_RESOURCE_NAME) { $env:FOUNDRY_RESOURCE_NAME } else { "agile-gov-foundry-$suffix" }
$projectName = if ($env:PROJECT_NAME) { $env:PROJECT_NAME } else { "agile-governance-project" }
$modelDeploymentName = if ($env:MODEL_DEPLOYMENT_NAME) { $env:MODEL_DEPLOYMENT_NAME } else { "gpt-5.4" }
$modelName = if ($env:MODEL_NAME) { $env:MODEL_NAME } else { "gpt-5.4" }
$modelVersion = if ($env:MODEL_VERSION) { $env:MODEL_VERSION } else { "2026-03-05" }
$logAnalyticsName = if ($env:LOG_ANALYTICS_NAME) { $env:LOG_ANALYTICS_NAME } else { "agile-gov-logs-$suffix" }
$appInsightsName = if ($env:APP_INSIGHTS_NAME) { $env:APP_INSIGHTS_NAME } else { "agile-gov-insights-$suffix" }
$workflowAgentName = if ($env:WORKFLOW_AGENT_NAME) { $env:WORKFLOW_AGENT_NAME } else { "agile-delivery-governance-workflow" }

Write-Host "=============================================="
Write-Host "  AI Agile Delivery Governance - Deploy (PS)"
Write-Host "=============================================="
Write-Host "Suffix:            $suffix"
Write-Host "Resource Group:    $resourceGroup"
Write-Host "Location:          $location"
Write-Host "Foundry Resource:  $foundryResourceName"
Write-Host "Project:           $projectName"
Write-Host ("Model Deployment:  {0} ({1} {2})" -f $modelDeploymentName, $modelName, $modelVersion)

& $az config set extension.use_dynamic_install=yes_without_prompt --only-show-errors | Out-Null
& $az extension add --name application-insights --only-show-errors | Out-Null

& $az group create --name $resourceGroup --location $location --tags environment=hack project=agile-delivery-governance --output none

$subscriptionId = (& $az account show --query id -o tsv).Trim()

& $az cognitiveservices account create --name $foundryResourceName --resource-group $resourceGroup --kind AIServices --sku S0 --location $location --custom-domain $foundryResourceName --assign-identity --yes --output none

$foundryResourceId = (& $az cognitiveservices account show --name $foundryResourceName --resource-group $resourceGroup --query id -o tsv).Trim()
& $az resource update --ids $foundryResourceId --set properties.disableLocalAuth=false --output none
& $az resource update --ids $foundryResourceId --set properties.allowProjectManagement=true --output none

& $az cognitiveservices account project create --name $foundryResourceName --resource-group $resourceGroup --project-name $projectName --location $location --output none

& $az cognitiveservices account deployment create --name $foundryResourceName --resource-group $resourceGroup --deployment-name $modelDeploymentName --model-name $modelName --model-version $modelVersion --model-format OpenAI --sku-capacity 10 --sku-name GlobalStandard --output none

& $az monitor log-analytics workspace create --resource-group $resourceGroup --workspace-name $logAnalyticsName --location $location --output none
$logAnalyticsId = (& $az monitor log-analytics workspace show --resource-group $resourceGroup --workspace-name $logAnalyticsName --query id -o tsv).Trim()

& $az monitor app-insights component create --app $appInsightsName --resource-group $resourceGroup --location $location --workspace $logAnalyticsId --output none
$appInsightsConn = (& $az monitor app-insights component show --app $appInsightsName --resource-group $resourceGroup --query connectionString -o tsv).Trim()
$appInsightsKey = (& $az monitor app-insights component show --app $appInsightsName --resource-group $resourceGroup --query instrumentationKey -o tsv).Trim()
$appInsightsResourceId = (& $az monitor app-insights component show --app $appInsightsName --resource-group $resourceGroup --query id -o tsv).Trim()

$connBody = @{
    properties = @{
        category = "AppInsights"
        target = $appInsightsResourceId
        authType = "ApiKey"
        credentials = @{ key = $appInsightsConn }
        isSharedToAll = $true
        metadata = @{
            ApiType = "Azure"
            ResourceId = $appInsightsResourceId
        }
    }
} | ConvertTo-Json -Depth 10 -Compress

& $az rest --method PUT --url "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.CognitiveServices/accounts/${foundryResourceName}/connections/appinsights-conn?api-version=2025-06-01" --headers "Content-Type=application/json" --body $connBody --output none

try {
    $userOid = (& $az ad signed-in-user show --query id -o tsv).Trim()
    if ($userOid) {
        & $az role assignment create --assignee-object-id $userOid --assignee-principal-type User --role "Azure AI User" --scope $foundryResourceId --output none
    }
}
catch {
    Write-Host "NOTE: Azure AI User role assignment skipped. Add it manually if 403 errors occur."
}

$foundryEndpoint = (& $az cognitiveservices account show --name $foundryResourceName --resource-group $resourceGroup --query properties.endpoint -o tsv).Trim()
$projectConn = (& $az cognitiveservices account project show --name $foundryResourceName --resource-group $resourceGroup --project-name $projectName --query "properties.endpoints.\"AI Foundry API\"" -o tsv).Trim()

$rootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = Join-Path $rootDir ".env"

$envContent = @(
    "# =============================================================================",
    "# AI Agile Delivery Governance - Environment Variables",
    "# Auto-generated by challenge-0-setup/deploy.ps1 on $(Get-Date -Format s)",
    "# =============================================================================",
    "",
    "AZURE_SUBSCRIPTION_ID=$subscriptionId",
    "RESOURCE_GROUP=$resourceGroup",
    "",
    "# Microsoft Foundry",
    "FOUNDRY_RESOURCE_NAME=$foundryResourceName",
    "PROJECT_NAME=$projectName",
    "FOUNDRY_ENDPOINT=$foundryEndpoint",
    "PROJECT_CONNECTION_STRING=$projectConn",
    "MODEL_DEPLOYMENT_NAME=$modelDeploymentName",
    "",
    "# Application Insights & Monitoring",
    "APPLICATIONINSIGHTS_CONNECTION_STRING=$appInsightsConn",
    "APPINSIGHTS_INSTRUMENTATION_KEY=$appInsightsKey",
    "",
    "# Tracing (Challenge 2)",
    "AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true",
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true",
    "",
    "# Challenge 4 - workflow agent name",
    "WORKFLOW_AGENT_NAME=$workflowAgentName"
)

$envContent | Set-Content -Path $envPath -Encoding utf8NoBOM

Write-Host ""
Write-Host "=============================================="
Write-Host "  DEPLOYMENT COMPLETE"
Write-Host "=============================================="
Write-Host "  .env written to: $envPath"
Write-Host "  Resource Group:  $resourceGroup"
Write-Host "  Foundry:         $foundryResourceName"
Write-Host ""