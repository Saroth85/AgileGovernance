# =============================================================================
# AI Agile Delivery Governance - One-click demo launcher (Windows)
# Sets PATH, prints portal links, then runs the governed pipeline + monitoring.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File demo.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File demo.ps1 -SkipMonitor
# =============================================================================

param(
    [switch]$SkipMonitor,
    [switch]$SkipPipeline
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AzCliPath {
    $candidates = @(
        "C:/Program Files/Microsoft SDKs/Azure/CLI2/wbin/az.cmd",
        "C:/Program Files (x86)/Microsoft SDKs/Azure/CLI2/wbin/az.cmd"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    throw "Azure CLI not found. Install Azure CLI first."
}

function Get-PythonPath {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    if (Test-Path "C:/Python314/python.exe") { return "C:/Python314/python.exe" }
    throw "Python not found. Install Python 3 first."
}

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

# --- Ensure Azure CLI is on PATH (so DefaultAzureCredential finds AzureCliCredential) ---
$azBin = Split-Path -Parent (Get-AzCliPath)
if ($env:Path -notlike "*$azBin*") { $env:Path = "$env:Path;$azBin" }
$az = Get-AzCliPath
$python = Get-PythonPath

# --- Load .env values for display ---
$envPath = Join-Path $repoRoot ".env"
if (-not (Test-Path $envPath)) {
    throw ".env not found. Run challenge-0-setup/deploy.ps1 first."
}

$envValues = @{}
Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $idx = $line.IndexOf("=")
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        $envValues[$key] = $val
    }
}

$resourceGroup = $envValues["RESOURCE_GROUP"]
$foundryResource = $envValues["FOUNDRY_RESOURCE_NAME"]
$projectName = $envValues["PROJECT_NAME"]
$modelName = $envValues["MODEL_DEPLOYMENT_NAME"]
$appInsightsName = "agile-gov-insights-" + ($foundryResource -replace '^agile-gov-foundry-', '')

# --- Verify Azure login ---
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  AI Agile Delivery Governance - DEMO" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$account = (& $az account show -o json 2>$null) | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Run: az login --use-device-code" -ForegroundColor Yellow
    throw "Azure login required."
}
Write-Host ("Signed in as:   {0}" -f $account.user.name)
Write-Host ("Subscription:   {0}" -f $account.name)
Write-Host ""

# --- Print demo links ---
Write-Host "--- DEMO LINKS -------------------------------" -ForegroundColor Green
Write-Host "Foundry portal:        https://ai.azure.com"
Write-Host ("  -> Project:          {0}" -f $projectName)
Write-Host ("  -> Build > Agents:   backlog-governance-agent, sprint-planning-agent,")
Write-Host ("                       agile-delivery-governance-workflow (kind: workflow)")
Write-Host ("  -> Model deployed:   {0}" -f $modelName)
Write-Host ""
Write-Host ("Resource Group:        {0}" -f $resourceGroup)
Write-Host ("App Insights:          {0}" -f $appInsightsName)
Write-Host  "  -> Azure portal > Application Insights > Transaction search (GenAI traces)"
Write-Host ""
Write-Host "Evaluation (manual):   Foundry portal > Build > Evaluations > Create > Agent"
Write-Host "  -> Target backlog-governance-agent, upload challenge-3-evaluate/eval_portal.jsonl"
Write-Host "----------------------------------------------" -ForegroundColor Green
Write-Host ""

# --- Run the governed pipeline (the gate that branches) ---
if (-not $SkipPipeline) {
    Write-Host ">>> Running governed pipeline (challenge-4-deploy/deploy.py)..." -ForegroundColor Cyan
    & $python (Join-Path $repoRoot "challenge-4-deploy/deploy.py")
    Write-Host ""
}

# --- Run the traced agent call (observability) ---
if (-not $SkipMonitor) {
    Write-Host ">>> Running traced agent call (challenge-2-monitor/monitor.py)..." -ForegroundColor Cyan
    & $python (Join-Path $repoRoot "challenge-2-monitor/monitor.py")
    Write-Host ""
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  DEMO READY" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Open https://ai.azure.com to show the agents and workflow live."
