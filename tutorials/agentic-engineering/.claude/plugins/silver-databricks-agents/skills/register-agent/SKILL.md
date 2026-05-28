---
description: "[Stage 7] Log and register the agent in Unity Catalog with the Coliseum promotion pipeline — Automated Gate evaluates candidate vs champion"
---

# Register Agent — Coliseum Promotion Pipeline + Automated Gate

Log the agent as an MLflow model, register it in Unity Catalog, and run the Automated Gate. The Automated Gate uses `mlflow.evaluate()` to compare the candidate against the current champion (and challenger, if one exists). Only candidates that beat the competition advance to challenger status.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 6 (optimize-prompts), the learner has:
- A `ResponsesAgent` with UC function tools and MLflow tracing
- A system prompt in `model_config.yaml` (hand-tuned and/or DSPy-optimized)
- An evaluation set with LLM judges (correctness, groundedness, relevance) — the quality backbone from Stage 5
- Local test results showing agent quality

Now the agent needs to enter the Coliseum: log it as a versioned artifact, register it in Unity Catalog, and prove it deserves to compete.

> **First-time vs iterative:** In this stage you register the agent for the first time via the CLI. In the production workflow (after Stage 11), new candidates are registered from the Coliseum Playground — domain experts write custom prompts, optionally boost them with DSPy, and register directly from the app. The Automated Gate logic is the same either way.

---

## Instructions

---

### Step 1 — Explain the Coliseum Promotion Pipeline

Before writing any code, the learner needs to understand the three-gate architecture that governs how models move from experiment to production.

```
  CANDIDATE GATE              AUTOMATED GATE               HUMAN GATE
  (Stage 11 — Playground)     (Stage 7 — HERE)             (Stage 9 — Review App)
 ┌────────────────────┐      ┌────────────────────┐       ┌────────────────────┐
 │                    │      │                    │       │                    │
 │  Custom prompt     │      │  Judges from       │       │  Domain expert     │
 │  tested in UI      │      │  Stage 5 run on    │       │  reviews responses │
 │                    │      │  eval set           │       │                    │
 │  >=80% thumbs-up   │      │  Candidate must    │       │  Side-by-side      │
 │  from assessments  │      │  beat champion     │       │  comparison        │
 │                    │      │  AND challenger     │       │                    │
 │  Optional: DSPy    │      │  Result: promote   │       │  Result: promote   │
 │  job to boost      │      │  to @challenger    │       │  to @champion      │
 │  prompt score      │      │                    │       │                    │
 │                    │      │                    │       │                    │
 │  Result: register  │      │                    │       │                    │
 │  as @candidate     │      │                    │       │                    │
 └────────┬───────────┘      └────────┬───────────┘       └────────┬───────────┘
          │                           │                            │
          ▼                           ▼                            ▼
     @candidate ──────────────> @challenger ──────────────> @champion
     (just registered)          (beat metrics)              (serving traffic)
```

**Note:** On first registration (this stage), there is no Candidate Gate — you register directly from the CLI. The Candidate Gate activates after Stage 11 when the Playground is deployed. The Automated Gate uses the same judges built in Stage 5.

**Why three gates?** Progressive trust.

- **Candidate Gate** catches obviously bad prompts before they consume evaluation compute. If a human cannot get 80% good answers in 5 tries, the model is not worth evaluating programmatically.
- **Automated Gate** catches regressions. `mlflow.evaluate()` runs the full evaluation set with aligned judges — no human could manually test 50+ queries consistently. This gate is deterministic and reproducible.
- **Human Gate** catches nuance. Automated metrics miss tone, domain appropriateness, and edge cases that only a subject-matter expert would notice. No fully automated pipeline should promote to champion.

**Note:** The gates do not run in strict sequence. The Candidate Gate happens in the Playground UI (Stage 11) when someone crafts a custom prompt. The Automated Gate runs HERE during registration. The Human Gate runs in Stage 9 via the Review App. The typical first-time flow is: register with default prompt (Stage 7) -> deploy (Stage 8) -> human review (Stage 9). The Playground (Stage 11) adds the Candidate Gate for subsequent iterations.

Use `AskUserQuestion` to confirm the learner understands the three-gate architecture before proceeding.

---

### Step 2 — Log the Agent as an MLflow Model

Log the agent with `mlflow.pyfunc.log_model()`. This creates a versioned artifact in MLflow that can be registered, deployed, and compared.

**Critical: the model must be logged to Databricks (not local SQLite).** Set the tracking URI to `databricks` so the artifact lands in the workspace where the serving endpoint can find it.

**Critical: package the full agent code.** The agent imports from `risk_agent.config` and `risk_agent.tools.*`. Without `code_paths=["src"]`, the serving endpoint will fail with `ModuleNotFoundError` because it only gets `agent.py` but not its dependencies.

**Critical: pin pip_requirements carefully.**
- Do NOT use extras brackets like `mlflow[genai]` — the serving environment validator rejects them.
- Include `pyyaml` (used by config loader) and `openai` (used by the agent client).

```python
import mlflow
from mlflow.models import infer_signature

# MUST log to Databricks — serving endpoints can only find models in the workspace
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/risk-agent")

# Infer signature from input/output examples
input_example = {"messages": [{"role": "user", "content": "What is the risk tier for Acme Corp?"}]}
output_example = {"content": "Acme Corp has a HIGH risk tier with total exposure of $2.5M."}
signature = infer_signature(input_example, output_example)

with mlflow.start_run(run_name="risk-agent-candidate") as run:
    model_info = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model="src/risk_agent/agent.py",   # the entry point
        code_paths=["src"],                        # REQUIRED — packages risk_agent.config + risk_agent.tools.*
        model_config="model_config.yaml",          # externalized prompt + LLM config
        signature=signature,
        pip_requirements=[
            "mlflow>=2.18",          # no extras brackets — [genai] breaks the validator
            "databricks-sdk>=0.38",
            "openai>=1.0",           # agent uses OpenAI client for Foundation Models
            "pyyaml>=6.0",           # config.py loads model_config.yaml
        ],
    )
    print(f"Logged model: {model_info.model_uri}")
    print(f"Run ID: {run.info.run_id}")
```

**Key parameters explained:**

| Parameter | Purpose |
|-----------|---------|
| `artifact_path` | Directory name within the MLflow run — like a namespace for the artifact |
| `python_model` | Points to the `.py` file with the agent class. MLflow loads this at serving time |
| `code_paths` | **Packages the full `risk_agent` package** — tools, config, everything agent.py imports. Without this, serving fails with `ModuleNotFoundError` |
| `model_config` | External YAML with the system prompt and LLM settings. Decoupled from code so DSPy can update it without code changes |
| `signature` | Declares the input/output schema — serving uses this for request validation |
| `pip_requirements` | Pinned deps. **No extras brackets** (`mlflow[genai]` → `mlflow`) — the serving validator rejects them |

Run this code. Show the logged model URI. Guide the user to view the run in the MLflow UI (Experiments > risk-agent > latest run > Artifacts tab).

Use `AskUserQuestion` to confirm the model is logged before proceeding.

---

### Step 3 — Register in Unity Catalog

Registration creates a governed, versioned entry in Unity Catalog. Every call to `register_model()` creates a NEW version — the registry is append-only, never destructive.

```python
import mlflow

model_name = "main.financial_risk.risk_agent"

# Register the logged model — creates a new version each time
model_version = mlflow.register_model(
    model_uri=model_info.model_uri,
    name=model_name,
)

print(f"Registered: {model_name} version {model_version.version}")
```

**Why Unity Catalog and not the legacy Workspace Model Registry?**

| Aspect | Workspace Registry | Unity Catalog Registry |
|--------|-------------------|----------------------|
| Governance | Per-workspace | Cross-workspace, centralized ACLs |
| Lineage | Manual tags | Automatic (tracks which notebook/job created each version) |
| Discovery | Workspace-scoped search | Catalog-wide search, like finding a table |
| Naming | `models:/name` | `catalog.schema.model` — same namespace as tables |

Unity Catalog treats models like first-class data assets. The same permissions, lineage, and audit logs that govern your Gold tables also govern your agent.

Run the registration. Show the version number. Guide the user to the Unity Catalog UI: Catalog > `main` > `financial_risk` > Models > `risk_agent`.

Use `AskUserQuestion` to confirm the registration before proceeding.

---

### Step 4 — Set Candidate Alias

Aliases are human-readable pointers to specific model versions. They decouple deployment from version numbers — instead of deploying "version 7", you deploy "@champion".

```python
from mlflow import MlflowClient

client = MlflowClient()

# Set the candidate alias on the newly registered version
client.set_registered_model_alias(
    name=model_name,
    alias="candidate",
    version=model_version.version,
)

print(f"Set @candidate -> version {model_version.version}")
```

**The three aliases and their meaning:**

```
  @candidate                 @challenger                @champion
 ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
 │ Just          │          │ Passed the   │          │ Currently    │
 │ registered.   │          │ Automated    │          │ serving live │
 │ Needs to pass │──pass──> │ Gate. Waiting│──pass──> │ traffic via  │
 │ Automated     │          │ for Human    │          │ the serving  │
 │ Gate.         │          │ Gate.        │          │ endpoint.    │
 └──────────────┘          └──────────────┘          └──────────────┘
```

**Aliases are pointers, not copies.** Reassigning `@champion` from version 5 to version 8 is instant — no data is moved, no model is re-deployed. The serving endpoint picks up the new version automatically (if configured with alias-based routing).

**Safe rollbacks:** If version 8 causes problems in production, reassign `@champion` back to version 5. Instant rollback, zero downtime.

Run the alias assignment. Verify by listing aliases:

```python
# Show all aliases for the model
model_details = client.get_registered_model(model_name)
for alias in model_details.aliases:
    print(f"  @{alias.alias} -> version {alias.version}")
```

Use `AskUserQuestion` to confirm the alias is set.

---

### Step 5 — Run the Automated Gate

This is the core of Stage 7. The Automated Gate uses `mlflow.genai.evaluate()` with the same built-in scorers from Stage 5 to compare candidate vs champion traces. The `run_automated_gate()` function in `evaluate.py` encapsulates this logic.

```python
import mlflow
from mlflow import MlflowClient
from risk_agent.evaluate import get_scorers, run_automated_gate

client = MlflowClient()
model_name = "main.financial_risk.risk_agent"

# --- Load versions by alias ---
candidate_version = client.get_model_version_by_alias(model_name, "candidate")
print(f"Candidate: version {candidate_version.version}")

try:
    champion_version = client.get_model_version_by_alias(model_name, "champion")
    print(f"Champion:  version {champion_version.version}")
except mlflow.exceptions.MlflowException:
    champion_version = None
    print("Champion:  (none — first registration, candidate auto-promotes)")
```

**First registration shortcut:** If there is no champion yet, the candidate auto-promotes to champion. No gate needed — there is nothing to beat.

```python
if champion_version is None:
    # First registration — auto-promote to champion
    client.set_registered_model_alias(model_name, "champion", candidate_version.version)
    client.delete_registered_model_alias(model_name, "candidate")
    print(f"First registration — version {candidate_version.version} is now @champion")
else:
    # --- Generate traces for both versions ---
    mlflow.set_experiment("/Shared/risk-agent")

    # Evaluate candidate
    candidate_uri = f"models:/{model_name}/{candidate_version.version}"
    candidate_traces = mlflow.search_traces(model_id=candidate_uri)

    # Evaluate champion
    champion_uri = f"models:/{model_name}/{champion_version.version}"
    champion_traces = mlflow.search_traces(model_id=champion_uri)

    # --- Run Automated Gate with built-in scorers from Stage 5 ---
    gate_result = run_automated_gate(
        candidate_traces=candidate_traces,
        champion_traces=champion_traces,
        scorers=get_scorers(),  # Same scorers from evaluate.py
    )

    # --- Display comparison ---
    print("\n--- Automated Gate Results ---")
    print(f"  Candidate scores: {gate_result['candidate_scores']}")
    print(f"  Champion scores:  {gate_result['champion_scores']}")
    print(f"  Candidate avg:    {gate_result['candidate_avg']:.3f}")
    print(f"  Champion avg:     {gate_result['champion_avg']:.3f}")

    # --- Promotion decision ---
    if gate_result["passed"]:
        client.set_registered_model_alias(model_name, "challenger", candidate_version.version)
        client.delete_registered_model_alias(model_name, "candidate")
        print(f"\nPASS — version {candidate_version.version} promoted to @challenger")
        print("Next: Human Gate (Stage 9) to approve promotion to @champion")
    else:
        print(f"\nFAIL — version {candidate_version.version} stays as @candidate")
        print(f"Candidate avg ({gate_result['candidate_avg']:.3f}) <= "
              f"Champion avg ({gate_result['champion_avg']:.3f})")
        print("Action: go back to Stage 6 (DSPy) to improve the prompt, then re-register")
```

**What `run_automated_gate()` does internally:**
1. Calls `mlflow.genai.evaluate()` on candidate traces with the 5 built-in scorers
2. Calls `mlflow.genai.evaluate()` on champion traces with the same scorers
3. Compares average scores — candidate must beat champion to pass
4. All evaluation runs are visible in the MLflow Evaluation tab

Present the comparison as a table:

| Metric | Candidate (vN) | Champion (vM) | Challenger (vK) | Winner |
|--------|----------------|---------------|-----------------|--------|
| Correctness | X.XX | X.XX | X.XX | ... |
| Groundedness | X.XX | X.XX | X.XX | ... |
| Relevance | X.XX | X.XX | X.XX | ... |
| **Average** | **X.XX** | **X.XX** | **X.XX** | **...** |

Use `AskUserQuestion` to let the learner observe the results and confirm understanding. Ask:
- "The Automated Gate has run. Review the results above. Ready to proceed?"

---

### Step 6 — Show in Databricks UI

Guide the user to explore the registered model in the Databricks UI:

1. **Navigate to:** Catalog > `main` > `financial_risk` > Models > `risk_agent`
2. **Versions tab:** Show all registered versions, each with a creation timestamp and source run
3. **Aliases:** Show which versions have `@candidate`, `@challenger`, `@champion` aliases
4. **Lineage:** Click on a version to see the lineage graph — which experiment run produced it, which notebook or script triggered the registration

```
  Lineage Graph (Databricks UI)
 ┌────────────────────────────────────────────────────────────┐
 │                                                            │
 │  Experiment Run ──────> Logged Model ──────> Registered    │
 │  (run_id: abc123)       (artifact)          Model v3      │
 │       │                                       │            │
 │       ├── model_config.yaml                   ├── @champion│
 │       ├── evaluation metrics                  └── serving  │
 │       └── traces                                  endpoint │
 │                                                            │
 └────────────────────────────────────────────────────────────┘
```

**Safe rollbacks:** If a new champion underperforms, reassign `@champion` to the previous version:

```python
# Emergency rollback — instant, no re-deployment needed
client.set_registered_model_alias(model_name, "champion", previous_version_number)
```

Use `AskUserQuestion` to confirm the user has explored the UC Model Registry.

---

### Step 7 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| Agent logged | ✓ | MLflow run with artifact, signature, config |
| Registered in UC | ✓ | `main.financial_risk.risk_agent` version N |
| @candidate alias | Set (or cleared) | Points to latest version |
| Automated Gate | Ran | `mlflow.evaluate()` on candidate vs champion |
| @challenger alias | Set (if passed) | Candidate promoted to challenger |
| @champion alias | Set (if first reg) | First registration auto-promotes |

**What happened:**
- If this was the **first registration**: the agent is now `@champion` (nothing to beat)
- If the candidate **passed** the Automated Gate: it is now `@challenger`, waiting for the Human Gate (Stage 9)
- If the candidate **failed**: it stays as `@candidate` — go back to Stage 6 (DSPy) and iterate

**Next:** Run `/silver-databricks-agents:deploy-agent` to deploy the champion to a serving endpoint.

---

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
| 8 | deploy-agent | <- next |
| 9 | review-iterate | |
| 10 | align-judges | |
| 11 | deploy-app | |
| 12 | cleanup | |

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 8 — Deploy Agent" (Recommended)** — description: "Run `/silver-databricks-agents:deploy-agent` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:deploy-agent" })`.
