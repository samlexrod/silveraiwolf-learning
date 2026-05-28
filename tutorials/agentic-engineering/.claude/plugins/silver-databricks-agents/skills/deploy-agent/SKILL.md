---
description: "[Stage 8] Deploy the champion model to a Databricks serving endpoint — configure secrets, tracing, and UC permissions"
---

# Deploy Agent to Serving Endpoint

Deploy the `@champion` model to a live Databricks serving endpoint. This stage covers creating the endpoint, configuring secrets for UC access, enabling MLflow tracing, and testing with the Playground.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Instructions

---

### Step 1 — Explain Deployment Options

Present this comparison to the user:

```
┌──────────────────────────────────────────────────────────────────────┐
│  DEPLOYMENT OPTIONS                                                  │
├─────────────────────┬────────────────────┬───────────────────────────┤
│                     │  Model Serving     │  Databricks Apps          │
├─────────────────────┼────────────────────┼───────────────────────────┤
│  Interface          │  REST API          │  Web UI (Gradio/Streamlit)│
│  Primary consumer   │  Applications      │  Humans                   │
│  Scaling            │  Auto (managed)    │  App-level                │
│  Authentication     │  Token-based       │  Workspace SSO            │
│  Use case           │  Programmatic      │  Interactive exploration  │
│  Stage              │  THIS STAGE (8)    │  Stage 11                 │
└─────────────────────┴────────────────────┴───────────────────────────┘
```

Explain: Model Serving is for API consumers — other services, notebooks, pipelines that call the agent programmatically. Databricks Apps (Stage 11) is for humans who want a chat interface. Most production agents need both.

Pause and ask the user if they'd like to continue.

---

### Step 2 — Create Secret Scope

The serving endpoint runs as a system service principal that does NOT inherit your UC permissions. You must inject your credentials via a Databricks secret scope so the agent can query UC functions and Gold tables.

**Sub-step 2a: Create (or reuse) the secret scope:**

```bash
source .env
export DATABRICKS_HOST DATABRICKS_TOKEN

# Create scope (idempotent — skip if already exists)
databricks secrets create-scope risk-agent 2>/dev/null || echo "Scope already exists"

# Store credentials
databricks secrets put-secret risk-agent databricks-host --string-value "$DATABRICKS_HOST"
databricks secrets put-secret risk-agent databricks-token --string-value "$DATABRICKS_TOKEN"
```

**Sub-step 2b: Look up the SQL warehouse ID** (needed so the agent can query UC functions without `warehouses.list()` permission):

```bash
databricks warehouses list --output json | python3 -c "
import sys, json
for wh in json.load(sys.stdin):
    print(f\"  {wh['id']}  {wh['name']}  ({wh['state']})\")
"
```

Pick the warehouse ID from the output. You will use it in Step 3.

Use `AskUserQuestion` to confirm the secret scope is created and the warehouse ID is captured.

---

### Step 3 — Create the Serving Endpoint

> **Note:** We use the REST API directly instead of `agents.deploy()` because `agents.deploy()` requires inference tables, which are not available on Databricks Free Edition. The REST API works on all workspace tiers.

Create the endpoint with environment variables that reference the secrets and configure tracing:

```bash
source .env
export DATABRICKS_HOST DATABRICKS_TOKEN

databricks api post /api/2.0/serving-endpoints --json '{
  "name": "risk-agent-endpoint",
  "config": {
    "served_entities": [{
      "entity_name": "main.financial_risk.risk_agent",
      "entity_version": "<CHAMPION_VERSION>",
      "scale_to_zero_enabled": true,
      "workload_size": "Small",
      "environment_vars": {
        "DATABRICKS_HOST": "{{secrets/risk-agent/databricks-host}}",
        "DATABRICKS_TOKEN": "{{secrets/risk-agent/databricks-token}}",
        "MLFLOW_TRACKING_URI": "databricks",
        "MLFLOW_EXPERIMENT_NAME": "/Shared/risk-agent",
        "ENABLE_MLFLOW_TRACING": "true",
        "SQL_WAREHOUSE_ID": "<WAREHOUSE_ID>"
      }
    }]
  }
}'
```

Replace `<CHAMPION_VERSION>` with the version number from Stage 7 (e.g., `"1"`) and `<WAREHOUSE_ID>` with the ID from Step 2b. Get the champion version programmatically if needed:

```python
import mlflow
mlflow.set_tracking_uri("databricks")
client = mlflow.MlflowClient()
champion = client.get_model_version_by_alias("main.financial_risk.risk_agent", "champion")
print(f"Champion version: {champion.version}")
```

**If the endpoint already exists**, update the config instead:

```bash
databricks api put /api/2.0/serving-endpoints/risk-agent-endpoint/config --json '{...same payload as above...}'
```

**Why all these env vars?**

| Env Var | Purpose |
|---------|---------|
| `DATABRICKS_HOST` + `DATABRICKS_TOKEN` | UC access — the system SP can't access your tables without credentials injected via secrets |
| `MLFLOW_TRACKING_URI=databricks` | Routes traces to your workspace (not local ephemeral storage) |
| `MLFLOW_EXPERIMENT_NAME` | Where traces are logged — visible in MLflow UI |
| `ENABLE_MLFLOW_TRACING=true` | Activates MLflow 3.x tracing |
| `SQL_WAREHOUSE_ID` | Hardcoded warehouse ID — avoids SP needing `warehouses.list()` permission |

Run the deployment. Show the output.

---

### Step 4 — Wait for Endpoint Provisioning

Serving endpoints take 5-15 minutes to provision. Check status:

```bash
databricks serving-endpoints get risk-agent-endpoint --output json | python3 -c "
import sys, json
data = json.load(sys.stdin)
state = data.get('state', {})
print(f\"State: {state.get('ready', 'UNKNOWN')}\")
print(f\"Config update: {state.get('config_update', 'UNKNOWN')}\")
"
```

Poll every 30 seconds until the state is `READY`. Display progress to the user:

```
┌─────────────────────────────────────────────┐
│  Endpoint Provisioning                      │
├─────────────────────────────────────────────┤
│  Endpoint: risk-agent-endpoint              │
│  Model:    main.financial_risk.risk_agent   │
│  Version:  @champion (v2)                   │
│  Status:   PROVISIONING ⏳                  │
│  Elapsed:  2m 30s                           │
└─────────────────────────────────────────────┘
```

Update the status display as it progresses. When `READY`, celebrate and move on.

**If deployment fails**, check the entity state:

```bash
databricks serving-endpoints get risk-agent-endpoint --output json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for e in d.get('config', {}).get('served_entities', []):
    state = e.get('state', {})
    print(f\"Deployment: {state.get('deployment', '?')}\")
    print(f\"Message: {state.get('deployment_status_message', 'none')}\")
"
```

**Common failures and fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: risk_agent.config` | Model logged without `code_paths` | Re-log model in Stage 7 with `code_paths=["src"]` |
| `python version 3.13 is not supported` | Serving only supports Python ≤3.12 | See Python version fix below |
| `mlflow[genai] is not a valid package` | Extras brackets in pip_requirements | Re-log with `mlflow>=2.18` (no `[genai]`) |
| Secret reference error | Secret scope not found | Re-run Step 2 to create the scope |

**Python version fix** (if model was logged with Python 3.13+): The model needs to be re-logged from Stage 7. Before re-logging, check your Python version with `python3 --version`. If it's 3.13+, the model artifact will embed that version and serving will reject it. The fix is to re-log the model — the skill instructions in Stage 7 handle `pip_requirements` correctly now, but if the Python version embedded in the artifact is still 3.13, you may need to manually patch the `python_env.yaml` in the artifact before registering, or use a Python 3.11 virtualenv for the log step.

Use `AskUserQuestion` to confirm the endpoint reached READY state or to help troubleshoot failures.

---

### Step 5 — Test the Live Endpoint

Query the endpoint with the Databricks CLI:

```bash
databricks serving-endpoints query risk-agent-endpoint \
  --input '{"messages": [{"role": "user", "content": "What is the risk tier for Acme Corp?"}]}'
```

Show the response. Then run a few more test queries:

- "Which counterparties have CRITICAL risk exposure?"
- "Summarize the portfolio concentration by sector"

Present responses in a formatted table. Compare with local responses from earlier stages — they should be identical, proving the endpoint serves the same model.

---

### Step 6 — Explain Alias-Based Routing

This is a critical concept for the Coliseum:

```
┌──────────────────────────────────────────────────────────────┐
│  ALIAS-BASED ROUTING                                         │
│                                                              │
│  Serving Endpoint ──→ @champion alias ──→ Model Version      │
│                                                              │
│  Today:    endpoint → @champion → v2                         │
│  After     endpoint → @champion → v3  (automatic!)           │
│  promotion:                                                  │
│                                                              │
│  No re-deploy needed. Reassigning the @champion alias        │
│  instantly routes all traffic to the new version.            │
│                                                              │
│  Rollback: reassign @champion back to v2 (instant)           │
└──────────────────────────────────────────────────────────────┘
```

Explain: When a new champion is promoted in Stage 9 (Human Gate), the serving endpoint automatically picks up the new version. This is why we deploy once and promote many times.

---

### Step 7 — Cost Warning

> **⚠️ Cost Warning**: Serving endpoints incur costs even with `scale_to_zero=True`.
> While the endpoint scales down when idle, you still pay for the underlying infrastructure.
> Cold starts after idle periods take ~30-60 seconds.
>
> When you're done experimenting, run `/silver-databricks-agents:cleanup` (Stage 12) to delete the endpoint and stop all charges.

Show the endpoint URL for the user to bookmark.

---

### Step 8 — Summary

Display the stage summary:

```
┌──────────────────────────────────────────────────────────────┐
│  Stage 8 Complete: Deploy Agent                              │
├──────────────────────────────────────────────────────────────┤
│  ✓ Serving endpoint created (risk-agent-endpoint)            │
│  ✓ Champion model deployed (@champion → v2)                  │
│  ✓ Endpoint tested with live queries                         │
│  ✓ Alias-based routing explained                             │
│                                                              │
│  Endpoint URL: https://<workspace>/serving-endpoints/...     │
│                                                              │
│  Next: Stage 9 — Review & Iterate (Human Gate)               │
│  The serving endpoint is live. Now collect human feedback     │
│  and decide whether to promote the challenger.               │
└──────────────────────────────────────────────────────────────┘
```

Show the tutorial progress tracker:

### Tutorial Progress
| Stage | Skill | Status |
|-------|-------|--------|
| 1 | scaffold-setup | ✓ |
| 2 | author-agent | ✓ |
| 3 | add-tools | ✓ |
| 4 | add-tracing | ✓ |
| 5 | evaluate-agent | ✓ |
| 6 | optimize-prompts | ✓ |
| 7 | register-agent | ✓ |
| 8 | deploy-agent | ✓ |
| 9 | review-iterate | ← next |
| 10 | align-judges | |
| 11 | deploy-app | |
| 12 | cleanup | |

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 9 — Review & Iterate" (Recommended)** — description: "Run `/silver-databricks-agents:review-iterate` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:review-iterate" })`.
