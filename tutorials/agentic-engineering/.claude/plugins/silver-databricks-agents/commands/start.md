[Stage 0] Show all available silver-databricks-agents commands and skills. Do NOT run any of them. Display ALL content below VERBATIM — do not summarize, condense, or reformat. Output every section exactly as written.

---

# SilverAIWolf's Databricks Agents Tutorial

### AI Agents with ResponsesAgent + Coliseum Promotion Pipeline

> **The Scenario:** Your data engineering team has built the financial risk medallion pipeline —
> Gold tables with financial ratios, risk exposure tiers, and portfolio summaries are ready.
> Now the risk department wants something more: an AI agent that can answer natural-language
> questions about the data. "What's our exposure to counterparty X?" "Which counterparties
> are critical risk?" "Summarize our FX concentration." Instead of building dashboards or
> writing SQL by hand, you'll build a Databricks agent that queries Gold tables through
> governed UC function tools, optimizes its own prompts with DSPy, evaluates quality with
> MemAlign-aligned judges, and deploys through a three-gate Coliseum promotion pipeline.

---

### Architecture

```
  Gold Tables (bootstrapped or from batch tutorial)
 ┌─────────────────────────────────┐
 │  gold_financial_ratios          │
 │  gold_risk_exposure             │───┐
 │  gold_portfolio_summary         │   │
 └─────────────────────────────────┘   │
                                       │
 ┌─────────────────────────────────┐   │    ┌──────────────────────────────────┐
 │  Unity Catalog Functions        │<──┼───>│  FinancialRiskAgent              │
 │  get_risk_exposure()            │   │    │  (ResponsesAgent)                │
 │  get_financial_ratios()         │   │    │    predict() / predict_stream()  │
 │  get_portfolio_summary()        │   │    │    + Foundation Model (LLM)      │
 └─────────────────────────────────┘   │    │    + @mlflow.trace               │
                                       │    └──────────────────────────────────┘
                                       │                   │
                                       │        ┌──────────┴──────────┐
                                       │        │                     │
                                       │  ┌─────┴──────┐    ┌───────┴────────┐
                                       │  │  Serving   │    │  Coliseum      │
                                       │  │  Endpoint  │    │  Playground    │
                                       │  │  (API)     │    │  (Databricks   │
                                       │  └────────────┘    │   App + UI)    │
                                       │                    └────────────────┘
                                       │
 ┌─────────────────────────────────────┴───────────────────────────────────────┐
 │                     OPTIMIZATION FLYWHEEL                                   │
 │                                                                             │
 │  Domain expert writes custom prompt in Playground                           │
 │         │                                                                   │
 │         ├── Tests & votes (Candidate Gate ≥80%)                             │
 │         │                                                                   │
 │         ├── Optionally triggers DSPy job ──> improved prompt returned       │
 │         │                                                                   │
 │         ├── Registers as @candidate ──> Automated Gate (judges on eval set) │
 │         │                                                                   │
 │         └── Human Gate ──> promote to @champion                             │
 │                                                                             │
 │  MemAlign (Stage 10) improves the judges using feedback from the Playground │
 │  ──> better judges ──> better Automated Gate ──> better DSPy optimization   │
 └─────────────────────────────────────────────────────────────────────────────┘
```

### Coliseum Promotion Pipeline (Three Gates)

```
  Domain expert writes custom prompt in Playground
       │
       ▼
  CANDIDATE GATE          AUTOMATED GATE           HUMAN GATE
  ≥80% thumbs-up         judges on eval set       domain expert
  in Playground           beats champion            review + approval
       │                      │                         │
       │   ┌─ DSPy job ─┐    │                         │
       │   │ (optional)  │    │                         │
       │   │ boost score │    │                         │
       │   └──────┬──────┘    │                         │
       │          │           │                         │
  ┌────┴──────────┴──┐  ┌────┴──────┐            ┌─────┴─────┐
  │ CUSTOM PROMPT    │─>│ CANDIDATE │───────────>│ CHALLENGER│──────────> CHAMPION
  │ (registered)     │  │ (new ver) │            │(competing)│           (serving)
  └──────────────────┘  └───────────┘            └───────────┘
```

---

### Prerequisites

Before running any stage, make sure you have:

1. **Databricks account** — Free Edition works for the entire tutorial. Sign up at [https://www.databricks.com/learn/free-edition](https://www.databricks.com/learn/free-edition)
2. **Personal Access Token (PAT)** — Generate one from your Databricks workspace: User Settings → Developer → Access Tokens
3. **Python 3.11+** and **uv** — for local development and testing
4. **Foundation Model endpoint** — available in your workspace (e.g., `databricks-meta-llama-3-3-70b-instruct`)

**Optional**: If you completed the `silver-databricks-batch` tutorial, Gold tables already exist. Otherwise, Stage 1 will bootstrap them with synthetic data.

Store your PAT and workspace URL in a `.env` file (gitignored) — the scaffold creates the template for you.

---

### Tutorial Stages

```
  Stage 1        Stage 2        Stage 3        Stage 4        Stage 5        Stage 6
  SCAFFOLD  -->  AUTHOR    -->  ADD       -->  ADD       -->  EVALUATE  -->  OPTIMIZE
  & SETUP        AGENT         TOOLS          TRACING        AGENT          PROMPTS
                                                                            (DSPy)

  Stage 7        Stage 8        Stage 9        Stage 10       Stage 11       Stage 12
  REGISTER  -->  DEPLOY    -->  REVIEW &  -->  ALIGN     -->  COLISEUM  -->  CLEANUP
  AGENT          AGENT         ITERATE        JUDGES         PLAYGROUND
  (Coliseum)     (Serving)     (Human Gate)   (MemAlign)     (App)
```

| Stage | Command | Description |
|---|---|---|
| 0 | `/silver-databricks-agents:start` | Show this help |
| 1 | `/silver-databricks-agents:scaffold-setup` | Scaffold project, Databricks auth, bootstrap Gold tables |
| 2 | `/silver-databricks-agents:author-agent` | Create ResponsesAgent, test locally |
| 3 | `/silver-databricks-agents:add-tools` | Register UC function tools, wire into agent |
| 4 | `/silver-databricks-agents:add-tracing` | Add MLflow tracing for observability |
| 5 | `/silver-databricks-agents:evaluate-agent` | Build judges + eval set — the quality backbone for all gates |
| 6 | `/silver-databricks-agents:optimize-prompts` | DSPy prompt optimization — runs as a job from the Playground |
| 7 | `/silver-databricks-agents:register-agent` | Register in UC + Coliseum Automated Gate (uses same judges) |
| 8 | `/silver-databricks-agents:deploy-agent` | Deploy champion to serving endpoint |
| 9 | `/silver-databricks-agents:review-iterate` | Review App + Human Gate (approve/reject) |
| 10 | `/silver-databricks-agents:align-judges` | MemAlign judge alignment (semantic + episodic) |
| 11 | `/silver-databricks-agents:deploy-app` | Coliseum Playground — compare, vote, promote |
| 12 | `/silver-databricks-agents:cleanup` | Delete all Databricks resources |

---

### Tech Stack

`ResponsesAgent (MLflow)` · `Unity Catalog Functions` · `MLflow Tracing` · `DSPy` · `MemAlign` · `databricks.agents.deploy()` · `Databricks Apps (Gradio)` · `pytest` · `ruff` · `uv + mise`

---

### First-Time vs Iterative Workflow

The 12 stages are taught linearly, but the production workflow is a loop through the Playground:

```
FIRST TIME (tutorial order)              ITERATIVE (production loop)
─────────────────────────                ──────────────────────────
Stages 1-4: Build the agent              Playground: write custom prompt
Stage 5: Build judges + eval set         ├── Test & vote (Candidate Gate)
Stage 6: Learn DSPy optimization         ├── Optionally run DSPy job (boost)
Stage 7: Register + Automated Gate       ├── Register → Automated Gate
Stage 8: Deploy serving endpoint         ├── Human Gate → promote
Stage 9: Human Gate                      └── Repeat
Stage 10: Align judges (MemAlign)
Stage 11: Deploy Playground (the hub)    MemAlign runs periodically to
Stage 12: Cleanup                        improve judges from Playground feedback
```

The Playground (Stage 11) is the **hub** for all subsequent iterations. Domain experts write custom prompts, vote on quality, optionally trigger DSPy to boost their prompt, then push through the Automated and Human gates — all from one UI.

---

### Quick Start

1. Run `/silver-databricks-agents:scaffold-setup` to scaffold your project and configure Databricks credentials
2. Run `/silver-databricks-agents:author-agent` to create and test your first agent
3. Build up the agent: Tools → Tracing → Evaluation → DSPy
4. Deploy and govern: Register → Deploy → Human Review → Align Judges → Playground

---

After displaying everything above, use `AskUserQuestion` to offer the first stage:

- **"Start Stage 1 — Scaffold & Setup" (Recommended)** — description: "Run `/silver-databricks-agents:scaffold-setup` now"
- **"Not now"** — description: "I'll start later"

If the user chooses to start, invoke the skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:scaffold-setup" })`.
