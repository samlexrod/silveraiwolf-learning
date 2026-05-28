---
description: "[Stage 3] Register Unity Catalog functions as governed agent tools, wire them into the agent, and test tool-augmented responses"
---

# Add Tools — Unity Catalog Functions as Governed Agent Tools

Register SQL functions in Unity Catalog, wire them into the ResponsesAgent as governed tools, and test the agent with real data from Gold tables. This is the stage where the agent goes from "chatbot" to "data-backed analyst."

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 2 (author-agent), the learner has:
- A working ResponsesAgent with predict() and predict_stream()
- model_config.yaml with externalized settings
- Local testing confirmed — but the agent has NO tools and CANNOT query data

This stage adds the tools that bridge the gap between the LLM and the Gold tables.

---

## Instructions

---

### Step 1 — Explain UC Functions as Tools

**Why Unity Catalog functions instead of raw SQL in the agent?**

This is a governance question, not a technical one. Present the comparison:

| Approach | Governed | Discoverable | Versioned | Auditable | Reusable |
|----------|----------|--------------|-----------|-----------|----------|
| **UC Functions** | ✓ RBAC controls who can call them | ✓ Other agents/users find them in catalog | ✓ Schema evolution tracked | ✓ Every call logged in audit trail | ✓ Any agent can use them |
| **Raw SQL in agent code** | ✗ Agent has full table access | ✗ Hidden inside Python files | ✗ Git history only | ✗ No call-level audit | ✗ Copy-paste to reuse |

**The governance chain:**
```
User asks question
    → LLM decides which tool to call (tool selection)
    → Agent calls UC function (governed by RBAC)
    → UC function queries Gold table (governed by table ACLs)
    → Results flow back to LLM (audited end-to-end)
    → LLM summarizes for the user
```

Every step in this chain is governed and auditable. If you embed raw SQL in the agent, you lose the middle three governance layers.

**Discoverability matters too:** When you register `get_risk_exposure` as a UC function, any team member can find it in the Unity Catalog explorer, understand its signature, and use it in their own agents or notebooks. Raw SQL buried in `agent.py` is invisible to everyone else.

Use `AskUserQuestion` to confirm the learner understands why UC functions are the right tool pattern before proceeding.

---

### Step 2 — Check SQL Warehouse

UC functions are created and executed via SQL warehouses. Verify one is running:

```bash
source .env
export DATABRICKS_HOST DATABRICKS_TOKEN
databricks warehouses list
```

If no warehouse is running, guide the user:
- Go to Databricks UI > SQL > SQL Warehouses
- Start a warehouse (or create a new Serverless one)
- Note the warehouse ID for subsequent commands

Use `AskUserQuestion` to confirm a SQL warehouse is available. Capture the warehouse ID for use in later steps.

---

### Step 3 — Create UC Functions

Read and display the `sql/create_uc_functions.sql` file from the project. Walk through each function:

**Function 1: `get_risk_exposure`**
- Input: counterparty name (string)
- Queries: `gold_risk_exposure`
- Returns: risk tier, total exposure, VaR, stress test results
- Use case: "What is the risk tier for Acme Corp?"

**Function 2: `get_financial_ratios`**
- Input: counterparty name (string)
- Queries: `gold_financial_ratios`
- Returns: debt-to-equity, current ratio, interest coverage, credit score
- Use case: "What are the financial ratios for Global Trading Inc?"

**Function 3: `get_portfolio_summary`**
- Input: none (aggregates across all counterparties)
- Queries: `gold_portfolio_summary`
- Returns: total exposure, average risk score, concentration metrics
- Use case: "Give me an overview of the portfolio risk."

Execute the SQL to create the functions:

```bash
# Run the SQL file to create UC functions
databricks api post /api/2.0/sql/statements \
  --json "{\"warehouse_id\": \"<WAREHOUSE_ID>\", \"statement\": \"$(cat sql/create_uc_functions.sql | tr '\n' ' ')\", \"wait_timeout\": \"50s\"}"
```

If the SQL file contains multiple statements, run them individually. Verify the functions exist:

```bash
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "<WAREHOUSE_ID>", "statement": "SHOW FUNCTIONS IN main.<SCHEMA> LIKE '\''get_*'\''", "wait_timeout": "50s"}'
```

Present the registered functions:

| UC Function | Input | Queries | Returns |
|------------|-------|---------|---------|
| `get_risk_exposure` | counterparty (STRING) | gold_risk_exposure | Risk tier, VaR, exposure |
| `get_financial_ratios` | counterparty (STRING) | gold_financial_ratios | Debt ratios, credit score |
| `get_portfolio_summary` | (none) | gold_portfolio_summary | Aggregate risk metrics |

Use `AskUserQuestion` to confirm all three functions are registered.

---

### Step 4 — Wire Tools into Agent

Read and display the tool definitions in `src/risk_agent/agent.py` (or `tools.py` if tools are in a separate file). Explain how tools are wired:

**Tool Definition Schema:**
Each tool is defined with a name, description, and parameter schema. The LLM uses the description to decide WHEN to call the tool, and the parameter schema to know WHAT to pass.

```python
tools = [
    {
        "type": "function",
        "name": "get_risk_exposure",
        "description": "Get risk exposure data for a specific counterparty...",
        "parameters": {
            "type": "object",
            "properties": {
                "counterparty": {"type": "string", "description": "Name of the counterparty"}
            },
            "required": ["counterparty"]
        }
    },
    ...
]
```

**The Execution Flow:**
```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  User    │────>│   LLM        │────>│  UC Function │────>│  Gold    │
│  Question│     │  (selects    │     │  (governed   │     │  Table   │
│          │     │   tool)      │     │   execution) │     │  (data)  │
└──────────┘     └──────┬───────┘     └──────┬───────┘     └──────────┘
                        │                     │
                        │<────────────────────┘
                        │  results returned
                        │
                  ┌──────▼───────┐
                  │  LLM         │
                  │  (summarizes │────> Final answer to user
                  │   results)   │
                  └──────────────┘
```

**Key insight:** The LLM makes TWO calls — once to select the tool and once to summarize the results. The Databricks framework manages this loop automatically for `ResponsesAgent`. You don't write it.

Use `AskUserQuestion` to confirm the learner understands the tool execution flow.

---

### Step 5 — Test with Tools

Now test the agent with the same questions from Stage 2 — but this time, the agent has tools:

```bash
cd <project-dir>
uv run python -c "
import mlflow
result = mlflow.models.predict(
    'src/risk_agent',
    model_input={
        'messages': [
            {'role': 'user', 'content': 'What is the risk tier for Acme Corp?'}
        ]
    }
)
print(result)
"
```

**Compare with Stage 2:** The same question that got a hallucinated or "I don't know" response now returns REAL DATA from the Gold tables.

| Question | Stage 2 (No Tools) | Stage 3 (With Tools) |
|----------|-------------------|---------------------|
| "What is the risk tier for Acme Corp?" | Hallucinated / "I don't know" | "Acme Corp is classified as Medium risk with $X exposure..." |
| "What are the financial ratios for Global Trading?" | Generic LLM knowledge | "Debt-to-equity: X, Current ratio: Y, Credit score: Z" |
| "Give me a portfolio overview" | Vague generalities | "Total exposure: $X across N counterparties, average risk: Y" |

Test all three tool-backed questions to demonstrate full coverage. **Show the full agent response** for each test in a quoted block so the learner can see the real data.

After showing all three results, present the "what just happened" explanation:

```
What just happened (e.g., "What is the risk tier for Pinnacle Industries?")

 agent.py (local)          Foundation Model (cloud)    SQL Warehouse (cloud)
      │                           │                           │
 1.   │ ── messages ────────────→ │                           │
      │                           │                           │
 2.   │                           │ LLM decides: call         │
      │                           │ get_risk_exposure         │
      │                           │ with "Pinnacle"           │
      │                           │                           │
 3.   │ ←── tool_call ────────── │                           │
      │                           │                           │
 4.   │ ── SELECT * FROM get_risk_exposure(...) ────────────→ │
      │                           │                           │
 5.   │ ←── {CRITICAL, $5.1M, B+, 9.8%} ────────────────── │
      │                           │                           │
 6.   │ ── messages + results ──→ │                           │
      │                           │                           │
 7.   │                           │ LLM summarizes            │
      │                           │ the data                  │
      │                           │                           │
 8.   │ ←── final response ───── │                           │
      │    "Pinnacle Industries   │                           │
      │     is CRITICAL tier..."  │                           │
```

  - Steps 1-3: LLM reads the tool definitions and decides to call `get_risk_exposure`
  - Step 4-5: The Python tool wrapper queries the UC function via SQL Statements API → hits the Gold table
  - Steps 6-8: Tool results are sent back to the LLM, which summarizes them into a natural language answer
  - **Two LLM calls** (step 1 and step 6), **one SQL query** (step 4), all orchestrated by the agentic loop in `predict()`

Use `AskUserQuestion` to confirm the learner sees the difference tools make and understands the execution flow.

---

### Step 6 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| UC Functions | ✓ Created | 3 governed functions in Unity Catalog |
| Tool wiring | ✓ Complete | Agent can select and call all 3 tools |
| Data-backed responses | ✓ Verified | Real data from Gold tables |
| Governance chain | ✓ Active | RBAC + audit trail on every tool call |

**What the agent can do now:**
- Query risk exposure by counterparty (get_risk_exposure)
- Look up financial ratios by counterparty (get_financial_ratios)
- Aggregate portfolio-level risk metrics (get_portfolio_summary)
- All queries are governed, auditable, and discoverable via Unity Catalog

**What the agent still lacks:**
- Observability — no tracing, no visibility into what tools were called or how long they took
- Evaluation — no way to measure if responses are correct, grounded, and relevant
- Optimization — system prompt is hand-written, not data-driven

**Next:** Run `/silver-databricks-agents:add-tracing` to add MLflow tracing with `@mlflow.trace` and `start_span()` for full observability of every agent invocation.

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 4 — Add Tracing" (Recommended)** — description: "Run `/silver-databricks-agents:add-tracing` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:add-tracing" })`.
