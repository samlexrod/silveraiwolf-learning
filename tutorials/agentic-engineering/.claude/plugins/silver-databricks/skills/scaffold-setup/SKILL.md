---
description: "[Stage 1] Scaffold the financial risk pipeline project, configure Databricks credentials, authenticate via OAuth, and verify connectivity"
---

# Scaffold & Setup

Scaffold a production-ready Databricks pipeline project using the medallion architecture (Bronze → Silver → Gold) with synthetic financial risk data, then configure Databricks credentials and authenticate.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on. If the user already has something set up (e.g., they already have a Databricks account), skip that section.

## Instructions

---

### Step 1 — Check Prerequisites

Run these checks silently and report results:

```bash
python3 --version
uv --version
mise --version 2>/dev/null
databricks --version 2>/dev/null
act --version 2>/dev/null
```

For **Java**, check both the system path AND the Homebrew prefix — Java may be installed via brew but not symlinked:

```bash
java -version 2>&1 || $(brew --prefix openjdk@17 2>/dev/null)/libexec/openjdk.jdk/Contents/Home/bin/java -version 2>&1
```

If the second path works but the first doesn't, Java is installed but not linked. Count it as installed (with a note about linking).

Display the results as a visual checklist table. Use `✅` for pass and `❌` for fail, and include the detected version:

```
┌─────────────────────────────────────────────────────┐
│  Prerequisites                                      │
├──────────────────────┬──────┬────────────────────────┤
│  Tool                │      │  Version               │
├──────────────────────┼──────┼────────────────────────┤
│  Python 3.10+        │  ✅  │  3.13.9                │
│  Java 17+ (JDK)      │  ❌  │  not found             │
│  uv                  │  ✅  │  0.7.x                 │
│  mise                │  ✅  │  2025.x.x              │
│  Databricks CLI      │  ❌  │  not found             │
│  act (local CI/CD)   │  ❌  │  not found             │
├──────────────────────┴──────┴────────────────────────┤
│  3/6 passed                                         │
└─────────────────────────────────────────────────────┘
```

Adapt the table to the actual results — show real versions, real pass/fail status, and update the pass count in the footer.

If **Python** or **uv** are missing, stop and tell the user to install them first — the tutorial can't proceed without them.

If **Java**, **mise**, **Databricks CLI**, or **act** are missing, **install them automatically** — do not ask the user which ones to install. Tell the user what you're installing and run all installs in parallel:

- `brew install openjdk@17`  — for Java (required by PySpark for local tests)
- `brew install mise`        — for task runner
- `brew tap databricks/tap && brew install databricks` — for Databricks CLI
- `brew install act`         — for local CI/CD (runs GitHub Actions in Docker, used in Stage 6)

After installing Java (or if Java was already installed via brew but not linked), set `JAVA_HOME` for the current session using the brew prefix — this works regardless of whether the system symlink exists:

```bash
export JAVA_HOME=$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home
```

Do NOT attempt `sudo ln -sfn` — it requires a password prompt that blocks non-interactive sessions. The `JAVA_HOME` export is sufficient; mise and the project's `.env` will handle it from here.

After installing all tools, re-run the checks and display the updated table. If `brew` itself is missing, stop and tell the user to install it from https://brew.sh first.

---

### Step 2 — Scaffold the Project

Ask the user:

> Where should I create the project? (default: `./financial-risk-pipeline`)

Use their answer or the default.

If the target directory already exists, remove it first so the scaffold starts clean (no stale files from a previous run):

```bash
rm -rf <target-directory>
```

Then copy the entire project template:

```bash
cp -r .claude/plugins/silver-databricks/project-template/ <target-directory>/
```

Initialize the project:

```bash
cd <target-directory>
mise trust
mise install
uv sync --extra dev
```

Do NOT run `git init` — the project lives inside the parent repository and should not have its own `.git`.

---

### Step 3 — Generate Seed Data

```bash
cd <target-directory>
uv run python data/generate_seed_data.py
```

This creates `data/seed/` with:
- `counterparties.csv` — 20 counterparties with balance sheet data
- `transactions.csv` — ~900 transactions over 90 business days
- `market_data.csv` — Daily prices for 50 instruments

---

### Step 4 — Run Tests & Lint

Before moving on, tell the user what's about to happen and why:

> Now let's verify the scaffolded project is healthy. I'll run two things:
>
> 1. **Unit & integration tests** (`pytest`) — these use PySpark locally to validate the seed data and transformation logic. This is why we installed Java earlier — PySpark needs a JVM to run even in local mode.
> 2. **Linter** (`ruff`) — checks code style, unused imports, and formatting rules.
>
> Both should pass cleanly on a freshly scaffolded project. If anything fails, we'll fix it before continuing.

Then run the commands:

```bash
cd <target-directory>
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

Report results clearly — show the pass count for tests and confirm lint is clean. If anything fails, investigate and help the user fix it before proceeding.

---

### Step 5 — Databricks Free Edition Account

Ask the user:

> Do you already have a Databricks account? (yes/no)

**If no**, walk them through it:

> 1. Go to **https://www.databricks.com/learn/free-edition** and sign up
> 2. Choose your cloud provider (any works — AWS, Azure, or GCP)
> 3. Complete the signup flow and wait for your workspace to provision
> 4. Once you can see the Databricks workspace landing page, you're ready
>
> Let me know when your workspace is ready.

**If yes**, move to the next step.

---

### Step 6 — Configure Databricks Credentials

Create the `.env` file from the sample:

```bash
cd <target-directory>
cp .env.sample .env
```

Tell the user what they need to fill in:

> I've created your `.env` file from the template. You need to add two values:
>
> **1. Workspace URL (`DATABRICKS_HOST`)**
> - Go to **https://accounts.cloud.databricks.com/login**
> - Log in and look at your browser's address bar
> - Copy the URL up to `.cloud.databricks.com` — it looks like: `https://dbc-abc12345-6789.cloud.databricks.com`
>
> **2. Personal Access Token (`DATABRICKS_TOKEN`)**
> - In your Databricks workspace, go to **User Settings → Developer → Access Tokens**
> - Click **Generate New Token**, give it a name (e.g., `local-dev`), and copy the token
>
> Open `<target-directory>/.env` in your editor and fill in both values, then let me know.

Use `AskUserQuestion` to ask:

> Have you filled in `DATABRICKS_HOST` and `DATABRICKS_TOKEN` in the `.env` file?

Options:
- "Yes, both are set" — proceed to verification
- "I need help" — offer more detailed guidance

---

### Step 7 — Authenticate & Verify Connection

Read the `.env` file to extract the host and token:

```bash
cd <target-directory>
grep '^DATABRICKS_HOST=' .env | cut -d= -f2-
grep '^DATABRICKS_TOKEN=' .env | cut -d= -f2-
```

If `DATABRICKS_HOST` is empty, tell the user it's missing and loop back to Step 6.

If `DATABRICKS_TOKEN` is empty (check the same way), tell the user it's missing and loop back to Step 6.

Once both values are present, tell the user:

> Both values found. Now I'll authenticate the Databricks CLI using OAuth so the CLI session is fully configured. This will open your browser for a one-time login — just approve the prompt and come back here.

Run the OAuth login using the host from `.env`:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
databricks auth login --host "$DATABRICKS_HOST"
```

This opens the browser for OAuth consent. The CLI stores the OAuth token in `~/.databrickscfg` automatically.

After the login completes, verify it worked:

```bash
databricks auth describe --host "$DATABRICKS_HOST"
```

You should see `Authenticated with: databricks-cli` and a valid username.

Then validate the connection:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
databricks workspace list / --host "$DATABRICKS_HOST"
```

If the command succeeds (returns a list of directories), tell the user:

> ✓ Authenticated and connected to Databricks successfully!

If it fails, troubleshoot:
- **Browser didn't open?** Try copying the URL from the terminal output manually
- **401 Unauthorized?** The token or OAuth may have failed — re-check the workspace URL and try `databricks auth login --host <URL>` again
- **Wrong URL?** Ask them to re-check their workspace URL
- **Network issue?** Check if they're behind a VPN or proxy

---

### Step 8 — Verify & Present

Run a final validation:

```bash
cd <target-directory>
export $(grep -v '^#' .env | xargs)
databricks workspace list /
databricks clusters list 2>/dev/null || echo "(no clusters — expected on Free Edition)"
```

Display the project structure:

```
<target-directory>/
├── .env.sample                 # Template — copy to .env and fill in
├── .env                        # Your workspace URL (gitignored)
├── mise.toml                   # Task runner + Python version management
├── databricks.yml              # Asset Bundles — deploy pipeline to Databricks
├── pyproject.toml              # Python project config (uv)
├── .actrc                      # Local CI with act
│
├── explorations/               # Databricks notebooks for prototyping
│   ├── 01_data_exploration.py  # Explore raw seed data
│   └── 02_ratio_prototyping.py # Prototype ratio calculations
│
├── src/financial_risk/
│   ├── bronze/                 # Raw ingestion (cloudFiles / CSV)
│   │   ├── counterparties.py   # Counterparty master data
│   │   ├── transactions.py     # Financial transactions (streaming)
│   │   └── market_data.py      # Market prices (streaming)
│   ├── silver/                 # Cleaned + conformed + enriched
│   │   ├── counterparties.py   # Standardized names, validated financials
│   │   ├── transactions.py     # Deduplicated, typed, direction-validated
│   │   ├── market_data.py      # Gap-filled prices, validated
│   │   └── positions.py        # Net positions with market values
│   ├── gold/                   # Business metrics
│   │   ├── financial_ratios.py # Liquidity, leverage, profitability ratios
│   │   ├── risk_exposure.py    # Concentration risk, risk tiers
│   │   └── portfolio_summary.py # Aggregations by sector/instrument/currency
│
├── tests/
│   ├── unit/                   # Fast, isolated tests
│   │   ├── test_ratios.py      # Financial ratio calculation logic
│   │   └── test_transformations.py # Silver-layer transformation logic
│   └── integration/
│       └── test_pipeline.py    # End-to-end flow with seed data
│
├── data/
│   ├── generate_seed_data.py   # Synthetic data generator
│   └── seed/                   # Generated CSVs (gitignored)
│
└── .github/workflows/
    ├── ci.yml                  # Lint + test on PR (act-compatible)
    └── cd.yml                  # Deploy on merge to main
```

Display a summary:

```
Setup Complete!

  Project:    <target-directory>
  Workspace:  <WORKSPACE_URL>
  Python:     ✓ Managed by mise
  CLI:        ✓ Configured
  Auth:       ✓ PAT in .env + OAuth CLI session
  Tests:      ✓ Passing
  Connection: ✓ Verified

Available mise tasks:
  mise run install      # Install dependencies
  mise run test         # Run unit tests
  mise run test:cov     # Run tests with coverage
  mise run lint         # Lint source and tests
  mise run format       # Format source and tests
  mise run ci           # Full local CI (lint + test)
  mise run seed         # Regenerate seed data
  mise run deploy:dev   # Deploy to Databricks (dev)
  mise run deploy:prod  # Deploy to Databricks (prod)

What's next:
  Stage 2 — Deploy to Dev
  Run /silver-databricks:deploy-dev to deploy the bundle and upload seed data
```

---

## Important

- **`.env` contains `DATABRICKS_HOST` and `DATABRICKS_TOKEN`** — both are required for local dev and CI/CD. The file is gitignored; the `.env.sample` template (without secrets) is committed.
- **OAuth is also configured** — after the user fills in `.env`, the skill automatically runs `databricks auth login` to establish an OAuth CLI session stored in `~/.databrickscfg`. This gives the CLI a browser-authenticated session in addition to the PAT.
- **CI/CD uses the same env vars** — configured as `secrets.DATABRICKS_HOST` and `secrets.DATABRICKS_TOKEN` in GitHub Actions (see `.github/workflows/cd.yml`). The user sets this up later when enabling CI/CD.
- If the user hits any issue, help them troubleshoot patiently — this is their first interaction with the platform.
