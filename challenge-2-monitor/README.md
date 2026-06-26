# Challenge 2 — Monitor with Application Insights

**Goal:** instrument the agents with GenAI tracing so every call is observable in
Application Insights.

## What gets traced

With tracing enabled, each agent call becomes a span carrying the model, token usage,
latency, inputs and outputs. Because the Governance Agent emits a structured verdict, the
quality signal (`overall_score`, `gate_pass`) flows through the trace too — so the **gate
pass-rate** and **score distribution** become queryable operational metrics, not just
log lines.

## How it works

Two environment variables must be set **before** `azure.ai.projects` is imported:

```
AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
```

Then the SDK is instrumented and the exporter is connected:

```python
from azure.ai.projects.telemetry import AIProjectInstrumentor
AIProjectInstrumentor().instrument()

from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor(connection_string=APPINSIGHTS_CONN_STRING, enable_live_metrics=True)
```

## Run

```bash
python challenge-2-monitor/monitor.py
```

The script emits a traced agent call, then waits for the trace to propagate.

## Verify

In the Azure Portal → your Application Insights resource → **Transaction search**, filter
to the last few minutes and look for the GenAI dependency spans from the agent call.

> Monitoring tells you the system is *running*. Challenge 3 tells you it is doing the
> *right thing*.
