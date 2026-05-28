---
description: "[Stage 1] Scaffold the financial risk agent project, configure Databricks credentials, authenticate, and bootstrap Gold tables"
---

# Scaffold Setup — Project + Auth + Gold Tables

Scaffold the financial risk agent project, install dependencies, configure Databricks authentication, and bootstrap Gold tables with synthetic data. This stage prepares everything the agent needs to query real data.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

This is Stage 1 of the agents tutorial. The learner may be coming from:
- The batch tutorial (`silver-databricks-batch`) — Gold tables already exist
- A fresh start — Gold tables need to be bootstrapped with synthetic data

Either path works. The bootstrap step detects which scenario applies.

---

## Instructions

---

### Step 1 — Check Prerequisites

Verify tools are installed. Run version checks and present as a checklist table:

```bash
python3 --version        # Python 3.11+
uv --version             # uv (Python package manager)
mise --version            # mise (tool manager)
databricks --version      # Databricks CLI
```

Present results as a checklist table:

| Tool | Required Version | Status | Action |
|------|-----------------|--------|--------|
| Python | 3.11+ | ✓ / ✗ | Install via `brew install python@3.11` |
| uv | any | ✓ / ✗ | Install via `brew install uv` |
| mise | any | ✓ / ✗ | Install from https://mise.jdx.dev |
| Databricks CLI | any | ✓ / ✗ | Install via `brew install databricks` |

**Do NOT check for Java or act** — they are not needed for the agents tutorial.

If any tools are missing, offer to install them via `brew`:

```bash
brew install <missing-tool>
```

Use `AskUserQuestion` to confirm all prerequisites are met before continuing.

---

### Step 2 — Scaffold the Project

Ask the user where to create the project. Default: `<repo-root>/tutorials/agentic-engineering/workspaces/financial-risk-agent` (where `<repo-root>` is the git repository root). This follows the same convention as the other tutorials: `financial-risk-pipeline`, `financial-risk-streaming`.

**Resolve `<repo-root>`** by running `git rev-parse --show-toplevel`. All paths below use this absolute root.

Use `AskUserQuestion` with options:
- Use default location (`<repo-root>/tutorials/agentic-engineering/workspaces/financial-risk-agent`) (Recommended)
- Choose a custom location

**If the directory already exists**, remove it first and re-scaffold from the template. This ensures a clean state — any previous `.env`, modified files, or cached state are cleared. The user's credentials will be re-configured in Step 3.

```bash
# Resolve repo root
REPO_ROOT=$(git rev-parse --show-toplevel)
TARGET="$REPO_ROOT/tutorials/agentic-engineering/workspaces/financial-risk-agent"

# Remove previous scaffold (if any)
rm -rf "$TARGET"
```

Copy the project from the plugin's `project-template/` directory:

```bash
PLUGIN_DIR="$REPO_ROOT/tutorials/agentic-engineering/.claude/plugins/silver-databricks-agents"
cp -r "$PLUGIN_DIR/project-template/" "$TARGET"
```

**Fallback:** If the relative path doesn't work, locate `project-template/` relative to this skill file's location (navigate up from `skills/scaffold-setup/` to the plugin root).

After copying, install dependencies:

```bash
cd <target>
uv sync --extra dev
```

Present the project structure:

```
<target>/
├── pyproject.toml              # Python deps (mlflow, databricks-sdk, dspy)
├── model_config.yaml           # Agent config (LLM model, temperature, system prompt)
├── .env.sample                 # Credential template
├── src/
│   └── risk_agent/
│       ├── agent.py            # ResponsesAgent — predict() + predict_stream()
│       ├── tools.py            # UC function tool definitions
│       └── __init__.py
├── sql/
│   └── create_uc_functions.sql # Unity Catalog function DDL
├── data/
│   └── bootstrap/
│       └── create_gold_tables.py  # Synthetic Gold table generator
├── evaluation/
│   └── evaluation_set.json     # Synthetic Q&A pairs for mlflow.evaluate()
├── optimize/
│   └── optimize.py             # DSPy prompt optimization
└── tests/
```

Use `AskUserQuestion` to confirm the scaffold looks correct.

---

### Step 3 — Configure Credentials

**Check if `.env` already exists** with credentials set:

```bash
grep -E '^DATABRICKS_(HOST|TOKEN)=' .env 2>/dev/null | sed 's/=.*/=<set>/'
```

**If `.env` exists and both vars are set**, skip to Step 4.

**If `.env` doesn't exist or vars are missing**:

1. Create `.env` from `.env.sample`:
   ```bash
   cp .env.sample .env
   ```

2. Tell the user to open `.env` and set these two values:
   - `DATABRICKS_HOST` — workspace URL (e.g., `https://dbc-abc123.cloud.databricks.com`)
   - `DATABRICKS_TOKEN` — personal access token (generate from User Settings > Developer > Access Tokens)

3. Use `AskUserQuestion` to ask:
   - **"Done — I've configured .env" (Recommended)** — description: "Continue to authentication"
   - **"I need help finding my credentials"** — description: "Show me where to get them in the Databricks UI"

   If the user needs help, explain: Go to your Databricks workspace → User Settings (top-right avatar) → Developer → Access Tokens → Generate new token. Then ask again.

---

### Step 4 — Authenticate

Verify the Databricks CLI can reach the workspace:

```bash
source .env
export DATABRICKS_HOST DATABRICKS_TOKEN
databricks auth login --host $DATABRICKS_HOST
```

Then confirm identity:

```bash
databricks current-user me
```

Display the authenticated user info: username, workspace URL. If authentication fails, guide the user to regenerate their token.

Use `AskUserQuestion` to confirm authentication works.

---

### Step 5 — Bootstrap Gold Tables

The agent queries Gold tables for financial risk data. These tables may already exist (from the batch tutorial) or need to be created with synthetic data.

**Check if Gold tables exist:**

```bash
source .env
export DATABRICKS_HOST DATABRICKS_TOKEN

# Check for existing Gold tables
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "<WAREHOUSE_ID>", "statement": "SHOW TABLES IN main.<SCHEMA> LIKE '\''gold_*'\''", "wait_timeout": "50s"}'
```

**If tables exist** — show row counts and skip bootstrap:

```bash
# Show row counts for each Gold table
for table in gold_financial_ratios gold_risk_exposure gold_portfolio_summary; do
  databricks api post /api/2.0/sql/statements \
    --json "{\"warehouse_id\": \"<WAREHOUSE_ID>\", \"statement\": \"SELECT COUNT(*) as row_count FROM main.<SCHEMA>.$table\", \"wait_timeout\": \"50s\"}"
done
```

Present as a table:

| Gold Table | Row Count | Source |
|-----------|-----------|--------|
| gold_financial_ratios | N | Batch pipeline / Bootstrap |
| gold_risk_exposure | N | Batch pipeline / Bootstrap |
| gold_portfolio_summary | N | Batch pipeline / Bootstrap |

**If tables are missing** — run the bootstrap script:

```bash
cd <target>
uv run python data/bootstrap/create_gold_tables.py
```

This creates all three Gold tables with realistic synthetic data: counterparties, risk tiers, financial ratios, exposure amounts, and portfolio summaries.

Use `AskUserQuestion` to ask the user which path they're on:
- I completed the batch tutorial (tables already exist)
- Fresh start (tables were just bootstrapped)
- I'm not sure (we'll verify in the next step)

---

### Step 6 — Verify & Summary

Run a final connectivity and data check:

```bash
# Verify Gold tables are queryable
databricks api post /api/2.0/sql/statements \
  --json '{"warehouse_id": "<WAREHOUSE_ID>", "statement": "SELECT * FROM main.<SCHEMA>.gold_risk_exposure LIMIT 3", "wait_timeout": "50s"}'
```

Display the sample data so the user can see what the agent will be querying.

Present the final summary:

| Component | Status | Details |
|-----------|--------|---------|
| Project scaffolded | ✓ | `<target>` |
| Dependencies installed | ✓ | mlflow, databricks-sdk, dspy |
| Databricks auth | ✓ | Connected as `<username>` |
| Gold tables | ✓ | 3 tables with data |
| Agent code | ✓ | Ready to test in Stage 2 |

Show the project structure tree one more time for reference.

**Next:** Run `/silver-databricks-agents:author-agent` to understand the ResponsesAgent architecture and test it locally with `mlflow.models.predict()`.

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 2 — Author Agent" (Recommended)** — description: "Run `/silver-databricks-agents:author-agent` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:author-agent" })`.
