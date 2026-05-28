---
description: "[Stage 5] Build the evaluation backbone — MLflow 3.x built-in scorers, registered datasets, and labeling schemas that power the Automated Gate, DSPy optimization, and MemAlign alignment"
---

# Evaluate Agent — Build the Quality Backbone (MLflow 3.x Native)

Build the evaluation infrastructure using MLflow 3.x native features: built-in scorers, registered datasets, and labeling schemas. Everything you build here powers the Automated Gate (Stage 7), DSPy prompt optimization (Stage 6), MemAlign judge alignment (Stage 10), and the Coliseum Playground (Stage 11).

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 4 (add-tracing), the learner has:
- A working ResponsesAgent with tools and full tracing
- MLflow traces capturing every invocation with timing and tool data
- No systematic way to measure response quality — "it looks right" is not a metric

This stage replaces gut feeling with quantitative evaluation — and builds infrastructure that the rest of the tutorial depends on.

---

## Instructions

---

### Step 1 — Explain Agent Evaluation

**Why evaluate?**

The scorers, dataset, and labeling schemas you build here are not just for this stage — they are the **single evaluation backbone** used across the entire tutorial:

| Where Evaluation Is Used | Stage | How |
|-------------------------|-------|-----|
| **Baseline measurement** | 5 (here) | `mlflow.genai.evaluate()` with built-in scorers |
| **DSPy optimization** | 6 | DSPy metric wraps the same scorers |
| **Automated Gate** | 7 | `run_automated_gate()` compares candidate vs champion traces |
| **Human review** | 9 | Labeling sessions + label schemas in MLflow UI |
| **MemAlign alignment** | 10 | Human feedback from labeling sessions improves custom judges |
| **Playground** | 11 | A/B votes flow into labeling sessions |

LLMs are probabilistic. The same question can produce different quality answers across invocations. Without evaluation, you're flying blind:

| Without Evaluation | With Evaluation |
|-------------------|-----------------|
| "The response looks right to me" | Correctness: yes/no per response |
| "I think it used the tool data" | RetrievalGroundedness: grounded or not |
| "It kind of answered the question" | RelevanceToQuery: relevant or not |
| No way to compare prompt variants | A/B test with statistical confidence |

**MLflow 3.x Built-in Scorers**

MLflow 3.x provides production-ready scorers out of the box — no need to write custom LLM judge prompts for standard dimensions:

| Scorer | What It Measures | Key Question |
|--------|-----------------|--------------|
| **Correctness** | Is the answer factually right? | Does the response match the expected answer? |
| **RetrievalGroundedness** | Is it based on retrieved context? | Did the agent use tool data, or hallucinate? |
| **RelevanceToQuery** | Does it answer what was asked? | Did the agent stay on topic? |
| **Safety** | Is the response safe and appropriate? | No harmful content, no financial advice? |
| **Guidelines** (custom) | Domain-specific rules | Does it follow our risk reporting standards? |

**The evaluation pipeline:**
```
Registered Dataset (questions + expected answers)
    ↓
mlflow.genai.evaluate() runs each question
    ↓
Built-in Scorers score each response automatically
    ↓
Results visible in MLflow Evaluation UI
    ↓
  ┌─────────────────────────────────────────────────┐
  │  MLflow Experiment > Evaluation Tab              │
  │  ├── Evaluation Runs (scored results)            │
  │  ├── Datasets (registered eval sets)             │
  │  ├── Labeling Schemas (winner, rationale)        │
  │  └── Labeling Sessions (human review queues)     │
  └─────────────────────────────────────────────────┘
```

**Key insight about groundedness:** This is where tracing from Stage 4 pays off. The `RetrievalGroundedness` scorer inspects the trace to see what data the tools returned, then checks if the agent's response is consistent with that data. Without traces, you can't measure groundedness.

Use `AskUserQuestion` to confirm the learner understands the built-in scorers before proceeding.

---

### Step 2 — Walk Through evaluate.py

Read and display `src/risk_agent/evaluate.py`. Walk through the key components:

**Built-in Scorers:**

```python
from mlflow.genai.scorers import (
    Correctness,
    Guidelines,
    RelevanceToQuery,
    RetrievalGroundedness,
    Safety,
)

def get_scorers() -> list:
    return [
        Correctness(),                 # Factual accuracy vs expected answer
        RetrievalGroundedness(),       # Grounded in tool results (traces)
        RelevanceToQuery(),            # Stays on topic
        Safety(),                      # No harmful content
        Guidelines(
            name="risk_domain_guidelines",
            guidelines=(
                "The response must cite specific counterparty names, risk tiers, "
                "and numerical values from the tool results. It must not give "
                "financial advice. It must present data in tables when showing "
                "multiple counterparties. It must not explain its methodology."
            ),
        ),
    ]
```

Explain each scorer:
- **Correctness** — compares response against expected answer (if provided in dataset)
- **RetrievalGroundedness** — checks response is supported by retrieved context from traces
- **RelevanceToQuery** — verifies response addresses the original question
- **Safety** — catches harmful, biased, or inappropriate content
- **Guidelines** — custom domain rules specific to financial risk reporting

**Why `Guidelines` is powerful:** The first four scorers are generic. `Guidelines` lets you encode domain-specific rules — like "must cite counterparty names" and "must not give financial advice." This is the scorer that domain experts can customize.

Use `AskUserQuestion` to confirm the learner understands the scorer architecture.

---

### Step 3 — Register the Evaluation Dataset

Register the eval set as a named dataset in MLflow. This makes it visible in the Evaluation UI and reusable across stages:

```bash
cd <project-dir>
uv run python -c "
import mlflow
from risk_agent.evaluate import create_eval_dataset

mlflow.set_experiment('/Shared/risk-agent')

# Register the dataset — visible in MLflow UI > Evaluation > Datasets
dataset = create_eval_dataset(name='risk-agent-eval-v1')
print(f'Dataset registered: {dataset}')
"
```

Then read and display the `data/eval/evaluation_set.json` file. Walk through the structure:

```json
[
  {
    "request": "What is the risk tier for Acme Corp?",
    "expected_response": "Acme Corp has a HIGH risk tier with total exposure of $2,500,000...",
    "context": {
      "counterparty_name": "Acme Corp",
      "risk_tier": "HIGH",
      "total_exposure_usd": 2500000
    }
  }
]
```

Each entry has: `request` (the question as a plain string), `expected_response` (the ideal answer for Correctness scoring), and `context` (ground truth data for reference). Note: the evaluation code transforms `request` → `inputs.query` and `expected_response` → `expectations.expected_response` to match the `mlflow.genai.evaluate()` format.

Present the eval set as a table:

| # | Question | Expected Key Facts | Tool Required |
|---|----------|-------------------|---------------|
| 1 | Risk tier for Acme Corp | risk_tier=Medium, exposure=$X | get_risk_exposure |
| 2 | Financial ratios for Global Trading | debt_to_equity=X, credit_score=Y | get_financial_ratios |
| 3 | Portfolio risk overview | total_exposure=$X, avg_risk=Y | get_portfolio_summary |
| ... | ... | ... | ... |

**Why registered datasets?** The dataset appears in the MLflow Evaluation tab. Every evaluation run references it by name, creating an audit trail: "eval run #7 used dataset `risk-agent-eval-v1`". When you add more eval pairs later, register a new version (`v2`) so results are always traceable.

Use `AskUserQuestion` to confirm the dataset looks correct.

---

### Step 4 — Run Evaluation with Built-in Scorers

**Important: MLflow tracking URI.** If `.env` contains `MLFLOW_TRACKING_URI=databricks`, **remove that line**. Local evaluation must use the local tracking store (MLflow defaults to `./mlflow.db`). Databricks serving endpoints set this automatically — you never need it in `.env`.

**Important: `mlflow.genai.evaluate()` data format.** MLflow 3.x requires:
- `inputs` column: a **dict** of field names → values (e.g., `{"query": "What is..."}`)
- `expectations` column: a **dict** of expectation names → values (e.g., `{"expected_response": "..."}`)
- `predict_fn` signature: parameters must **match the `inputs` dict keys** (e.g., `def predict_fn(query: str)`)

MLflow unpacks `inputs` as kwargs and calls `predict_fn(**inputs)`. If the keys don't match the function's parameter names, you get `unexpected keyword argument` errors.

Execute evaluation using the correct format:

```python
import mlflow, json, pandas as pd
from risk_agent.agent import FinancialRiskAgent
from risk_agent.evaluate import get_scorers

mlflow.set_experiment('/Shared/risk-agent')

with open('data/eval/evaluation_set.json') as f:
    eval_data = json.load(f)

agent = FinancialRiskAgent()

# predict_fn parameter name MUST match the inputs dict key ("query")
def predict_fn(query: str) -> str:
    messages = [{"role": "user", "content": query}]
    result = agent.predict(model_input={"messages": messages})
    return result.get("content", str(result))

# Format data: inputs as dict, expectations as dict
rows = []
for item in eval_data:
    rows.append({
        "inputs": {"query": item["request"]},                          # dict, not str
        "expectations": {"expected_response": item["expected_response"]},  # dict, not str
    })

result = mlflow.genai.evaluate(
    data=pd.DataFrame(rows),
    predict_fn=predict_fn,
    scorers=get_scorers(),
)
```

**What happens during evaluation:**
1. `mlflow.genai.evaluate()` calls `predict_fn(query="What is the risk tier...")` for each row
2. The agent runs predict() with tracing (generates a trace per question)
3. Five built-in scorers score each response automatically
4. Results are logged to the MLflow experiment and visible in the **Evaluation tab**

**Where to see results in the MLflow UI:**

Guide the user to the Experiment page > **Evaluation** tab. This is the native evaluation UI:
- **Evaluation Runs** — each `mlflow.genai.evaluate()` call creates a run with all scores
- **Per-row results** — click into a run to see scores per question
- **Datasets** — the registered dataset used for this evaluation
- **Compare runs** — select multiple runs to compare side-by-side (useful after prompt iteration)

Use `AskUserQuestion` to confirm the evaluation completed and the user can see results in the MLflow UI.

---

### Step 5 — Create Labeling Schemas

Set up label schemas for human review. These schemas appear in the MLflow Evaluation UI and will be used in Stage 9 (Review App) and Stage 11 (Playground):

```bash
cd <project-dir>
uv run python -c "
from risk_agent.evaluate import create_review_schemas

schemas = create_review_schemas()
print(f'Created schemas: {schemas}')
"
```

This creates two schemas:

| Schema | Type | Purpose |
|--------|------|---------|
| **risk_winner** | Categorical (Champion/Custom/Neither) | Who produced the better response? |
| **risk_rationale** | Free text | Why did you choose this winner? |

**Why labeling schemas matter:** When domain experts review responses in the Playground (Stage 11) or Review App (Stage 9), their votes are captured as structured labels — not loose comments. This structured feedback feeds MemAlign alignment (Stage 10) and makes A/B testing statistically rigorous.

Guide the user to the MLflow Evaluation tab > **Labeling Schemas** to see the created schemas.

Use `AskUserQuestion` to confirm the schemas are visible.

---

### Step 6 — Analyze Results and Iterate

Display results as a detailed table:

| Question | Correctness | Groundedness | Relevance | Safety | Guidelines | Notes |
|----------|------------|-------------|-----------|--------|-----------|-------|
| Risk tier for Acme Corp | ✓ | ✓ | ✓ | ✓ | ✓ | Fully grounded |
| Financial ratios for Global Trading | ✓ | ✓ | ✗ | ✓ | ✗ | Missing table format |
| Portfolio overview | ✓ | ✗ | ✓ | ✓ | ✗ | Added unrequested detail |

**Identify weak spots by scorer:**

| Problem | System Prompt Fix |
|---------|------------------|
| Low Groundedness | Add: "Only include information from tool results. Do not add facts from your training data." |
| Low Relevance | Add: "Answer only the specific question asked. Do not volunteer additional analysis." |
| Low Guidelines | Add: "Present data in tables when comparing multiple counterparties. Lead with the answer." |

After updating the system prompt in `model_config.yaml`, re-run evaluation using the same pattern from Step 4 (the `predict_fn(query: str)` + dict-format data). Compare the two evaluation runs in MLflow to see which metrics improved.

Guide the user to the MLflow Evaluation tab to **compare the two runs** — select both, click Compare. The UI shows which metrics improved.

**Teaching moment:** Manual prompt iteration works but is slow and subjective. DSPy (Stage 6) automates this — it tries hundreds of prompt variants and picks the winner based on these same scorers.

Use `AskUserQuestion` to confirm the learner sees the improvement.

---

### Step 7 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| Built-in scorers | ✓ Configured | Correctness, Groundedness, Relevance, Safety, Guidelines |
| Evaluation dataset | ✓ Registered | `risk-agent-eval-v1` in MLflow |
| Labeling schemas | ✓ Created | risk_winner (categorical), risk_rationale (text) |
| Baseline evaluation | ✓ Ran | Scores visible in MLflow Evaluation tab |
| Manual iteration | ✓ Demonstrated | One round with before/after comparison |

**What we built — and where it's used next:**

| Component | Used In | How |
|-----------|---------|-----|
| **Built-in scorers** | Stage 6 (DSPy), Stage 7 (Gate) | `get_scorers()` wraps them for reuse |
| **Registered dataset** | Stage 7 (Gate), Stage 11 (Playground) | Named reference for reproducible evaluation |
| **Labeling schemas** | Stage 9 (Review), Stage 11 (Playground) | Structured feedback for human review |
| **Baseline scores** | All subsequent stages | The "before" in every comparison |

**MLflow Evaluation UI — your new dashboard:**
- **Evaluation Runs**: See all scored results, compare across prompt variants
- **Datasets**: Track which eval set was used for each run
- **Labeling Schemas**: Structure human feedback for MemAlign
- **Labeling Sessions** (created in Stage 9): Organize human review queues

**Next:** Run `/silver-databricks-agents:optimize-prompts` to learn how DSPy uses these scorers to automatically optimize prompts.

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 6 — Optimize Prompts" (Recommended)** — description: "Run `/silver-databricks-agents:optimize-prompts` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:optimize-prompts" })`.
