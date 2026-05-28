---
description: "[Stage 12 / Cleanup] Delete serving endpoint, Databricks App, registered models, UC functions, and bootstrapped Gold tables — reset to fresh state"
---

# Cleanup

Delete all Databricks resources created by this tutorial — serving endpoint, Databricks App, registered models, Unity Catalog functions, and optionally Gold tables and schema. Safe to re-run (all operations use IF EXISTS or handle 404 gracefully).

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Instructions

---

### Step 1 — Confirm Cleanup

Use `AskUserQuestion` to confirm. Show what will be deleted:

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠️  CLEANUP — The following resources will be deleted:      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Serving Endpoint:                                           │
│    • risk-agent-endpoint                                     │
│                                                              │
│  Databricks App:                                             │
│    • risk-agent-playground                                   │
│                                                              │
│  Registered Model (all versions):                            │
│    • main.financial_risk.risk_agent                           │
│                                                              │
│  Unity Catalog Functions:                                    │
│    • main.financial_risk.get_risk_exposure                    │
│    • main.financial_risk.get_financial_ratios                 │
│    • main.financial_risk.get_portfolio_summary                │
│                                                              │
│  Gold Tables (conditional):                                  │
│    • main.financial_risk.gold_risk_exposure                   │
│    • main.financial_risk.gold_financial_ratios                │
│    • main.financial_risk.gold_portfolio_summary               │
│                                                              │
│  Schema (optional):                                          │
│    • main.financial_risk                                     │
│                                                              │
│  This action cannot be undone.                               │
└──────────────────────────────────────────────────────────────┘
```

Options:
- **Yes, delete everything** — Proceed with full cleanup
- **Delete infrastructure only** — Keep Gold tables and schema (useful if you plan to re-run the tutorial)
- **Cancel** — Do nothing

---

### Step 2 — Delete Serving Endpoint

```bash
databricks serving-endpoints delete risk-agent-endpoint 2>/dev/null || echo "Endpoint not found (already deleted or never created)"
```

Verify deletion:
```bash
databricks serving-endpoints get risk-agent-endpoint 2>/dev/null && echo "⚠️ Still exists" || echo "✓ Deleted"
```

---

### Step 3 — Delete Databricks App

```bash
databricks apps delete risk-agent-playground 2>/dev/null || echo "App not found (already deleted or never created)"
```

Verify deletion:
```bash
databricks apps get risk-agent-playground 2>/dev/null && echo "⚠️ Still exists" || echo "✓ Deleted"
```

---

### Step 4 — Delete Registered Model

Delete all versions and the registered model from Unity Catalog:

```python
import mlflow

client = mlflow.tracking.MlflowClient()
model_name = "main.financial_risk.risk_agent"

try:
    # Delete all aliases first
    for alias in ["champion", "challenger", "candidate"]:
        try:
            client.delete_registered_model_alias(model_name, alias)
        except Exception:
            pass

    # Delete all versions
    versions = client.search_model_versions(f"name='{model_name}'")
    for v in versions:
        client.delete_model_version(model_name, v.version)

    # Delete the model itself
    client.delete_registered_model(model_name)
    print(f"✓ Deleted registered model: {model_name}")
except Exception as e:
    print(f"Model not found or already deleted: {e}")
```

---

### Step 5 — Drop UC Functions

Run the cleanup SQL or execute directly:

```sql
DROP FUNCTION IF EXISTS main.financial_risk.get_risk_exposure;
DROP FUNCTION IF EXISTS main.financial_risk.get_financial_ratios;
DROP FUNCTION IF EXISTS main.financial_risk.get_portfolio_summary;
```

Via Databricks CLI:
```bash
databricks sql execute --statement "DROP FUNCTION IF EXISTS main.financial_risk.get_risk_exposure"
databricks sql execute --statement "DROP FUNCTION IF EXISTS main.financial_risk.get_financial_ratios"
databricks sql execute --statement "DROP FUNCTION IF EXISTS main.financial_risk.get_portfolio_summary"
```

Verify:
```bash
databricks sql execute --statement "SHOW FUNCTIONS IN main.financial_risk" 2>/dev/null || echo "Schema or functions not found"
```

---

### Step 6 — Drop Gold Tables (Conditional)

Use `AskUserQuestion` to ask the user:

**"Did you bootstrap Gold tables in Stage 1, or do they come from the silver-databricks-batch tutorial?"**

Options:
- **Bootstrapped in Stage 1** — "I created them fresh with synthetic data. Safe to delete."
- **From batch tutorial** — "They were created by the silver-databricks-batch tutorial. Don't delete another tutorial's data."
- **Not sure** — "Check the table properties and decide."

If **bootstrapped**, drop them:
```sql
DROP TABLE IF EXISTS main.financial_risk.gold_risk_exposure;
DROP TABLE IF EXISTS main.financial_risk.gold_financial_ratios;
DROP TABLE IF EXISTS main.financial_risk.gold_portfolio_summary;
```

If **from batch tutorial**, skip with a message:
```
→ Skipping Gold table deletion — these belong to the silver-databricks-batch tutorial.
  Run /silver-databricks-batch:cleanup if you want to remove them.
```

---

### Step 7 — Drop Schema (Optional)

Use `AskUserQuestion`:

**"Do you want to drop the entire financial_risk schema?"**

Options:
- **Yes, drop it** — "I'm done with all financial risk tutorials. Remove the schema."
- **No, keep it** — "I might use this schema for other tutorials or experiments."

If yes:
```sql
DROP SCHEMA IF EXISTS main.financial_risk CASCADE;
```

If no:
```
→ Schema main.financial_risk preserved.
```

---

### Step 8 — Verify Cleanup

Run verification checks and display results:

```
┌──────────────────────────────────────────────────────────────┐
│  CLEANUP VERIFICATION                                        │
├──────────────────────────────┬───────────────────────────────┤
│  Resource                    │  Status                       │
├──────────────────────────────┼───────────────────────────────┤
│  Serving endpoint            │  ✓ Deleted                    │
│  Databricks App              │  ✓ Deleted                    │
│  Registered model            │  ✓ Deleted (all versions)     │
│  UC function: risk_exposure  │  ✓ Dropped                    │
│  UC function: ratios         │  ✓ Dropped                    │
│  UC function: portfolio      │  ✓ Dropped                    │
│  Gold tables                 │  ✓ Dropped / ⊘ Kept (batch)  │
│  Schema                      │  ✓ Dropped / ⊘ Kept          │
├──────────────────────────────┴───────────────────────────────┤
│  All tutorial resources cleaned up.                          │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 9 — Summary

```
┌──────────────────────────────────────────────────────────────┐
│  Stage 12 Complete: Cleanup                                  │
├──────────────────────────────────────────────────────────────┤
│  ✓ All Databricks resources deleted                          │
│  ✓ Workspace is clean                                        │
│                                                              │
│  Thank you for completing the Databricks Agents Tutorial!    │
│                                                              │
│  What you learned:                                           │
│  • Build agents with ResponsesAgent (MLflow)                 │
│  • Add governed tools with Unity Catalog functions            │
│  • Observe with MLflow tracing                               │
│  • Evaluate with LLM-as-judge (mlflow.evaluate)              │
│  • Optimize prompts with DSPy                                │
│  • Align judges with MemAlign                                │
│  • Deploy with agents.deploy() and Databricks Apps           │
│  • Promote safely with the Coliseum (3 gates)                │
│                                                              │
│  The Optimization Flywheel:                                  │
│  DSPy (agent) + MemAlign (judges) + Human Feedback           │
│  → Coliseum → Production                                     │
└──────────────────────────────────────────────────────────────┘
```

Show the final tutorial progress tracker:

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
| 9 | review-iterate | ✓ |
| 10 | align-judges | ✓ |
| 11 | deploy-app | ✓ |
| 12 | cleanup | ✓ |

🎓 **Tutorial complete!**
