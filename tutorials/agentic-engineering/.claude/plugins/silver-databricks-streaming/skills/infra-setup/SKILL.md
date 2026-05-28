---
description: "[Stage 1] Scaffold project, install tools, run local tests, configure Databricks auth — zero AWS cost"
---

# Project Setup — Scaffold + Tools + Auth

Scaffold the streaming monorepo project, install all tools via mise, run local tests, and configure Databricks authentication. **No AWS resources are provisioned in this stage — zero cost.**

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

This is Stage 1 of the streaming tutorial. The learner should have:
- Completed the batch tutorial (`silver-databricks-batch`)
- An AWS account with CLI configured
- A Databricks workspace (same one from the batch tutorial)

---

## Instructions

---

### Step 1 — Check Prerequisites

Verify tools are installed (credentials are checked separately — AWS in this step, Databricks in Step 4 after `.env` exists):

```bash
# Check each tool — report status as a table
mise --version          # mise (tool manager)
uv --version            # uv (Python package manager)
```

Present results as a checklist table:

| Tool | Status | Action |
|------|--------|--------|
| mise | ✓ / ✗ | Required — install from https://mise.jdx.dev |
| uv | ✓ / ✗ | Required — `mise install` |

Terraform and AWS CLI are NOT needed yet — they will be installed via `mise install` and used in Stage 3.

#### AWS Credentials Check

AWS is only needed starting at Stage 3, but check now so the user isn't surprised later.

**Step A — Detect SSO profile and refresh token first.**
SSO tokens expire frequently. Always refresh before attempting identity checks to avoid false negatives:

1. Check for configured SSO profiles: `aws configure list-profiles`
2. If a `silveraiwolf` profile exists (or any SSO profile), **refresh the token first**:
   - `aws sso login --profile silveraiwolf` (opens a browser — no terminal input needed, just wait for it to complete; use a 120s timeout)
   - `export AWS_PROFILE=silveraiwolf`
3. Check if `~/.zshrc` already contains `export AWS_PROFILE=silveraiwolf` — if not, append it so it persists across sessions

**Step B — Verify identity.** Try these approaches **in order** until one succeeds:

1. Try with the profile: `AWS_PROFILE=silveraiwolf aws sts get-caller-identity`
2. Try the default: `aws sts get-caller-identity`

**If no SSO profile exists and both identity checks fail**, guide the user through SSO setup. Only `aws configure sso` requires the `!` prefix (it has interactive prompts). Everything else you run directly:

1. Tell the user to configure the SSO profile (one-time — has interactive prompts that require terminal input):
   ```
   ! aws configure sso
   # SSO session name: silveraiwolf
   # SSO start URL: <their SSO start URL>
   # SSO region: <their SSO region>
   # SSO registration scopes: sso:account:access
   # Then select the account and role when prompted
   # CLI default profile name: silveraiwolf
   ```
2. After the profile is configured, **you** run the rest automatically via Bash:
   - `aws sso login --profile silveraiwolf` (opens a browser — no terminal input needed, just wait for it to complete; use a 120s timeout)
   - `export AWS_PROFILE=silveraiwolf`
   - `aws sts get-caller-identity` to verify
3. Check if `~/.zshrc` already contains `export AWS_PROFILE=silveraiwolf` — if not, append it so it persists across sessions

**If credentials exist but `AWS_PROFILE` isn't set**, handle it automatically:
1. Run `export AWS_PROFILE=silveraiwolf` via Bash so the current session picks it up
2. Check if `~/.zshrc` already contains `export AWS_PROFILE=silveraiwolf` — if not, append it so it persists across sessions
3. Confirm to the user that both the session and shell config have been updated

**Do NOT check Databricks auth here** — the project `.env` file (which contains `DATABRICKS_HOST` and `DATABRICKS_TOKEN`) doesn't exist until after Step 2 (scaffold). Databricks auth is verified in Step 4.

Use `AskUserQuestion` to confirm prerequisites are met before continuing.

---

### Step 2 — Scaffold Project

Ask the user for a project directory (default: `<repo-root>/tutorials/agentic-engineering/workspaces/financial-risk-streaming`, where `<repo-root>` is the git repository root).

**If the directory already exists**, remove it first and re-scaffold from the template. This ensures a clean state — any previous Terraform state, `.databricks/` cache, `.env`, or modified files are cleared. The user's credentials will be re-configured in Step 4.

```bash
# Remove previous scaffold (if any)
rm -rf <project-dir>
```

1. Copy the entire `project-template/` directory from this plugin to the chosen location
2. Initialize a git repo — **required** for `databricks bundle deploy` to know which files to sync:
   ```bash
   cd <project-dir>
   git init
   git add -A
   git commit -m "Initial scaffold" --no-verify
   ```
3. Trust and install mise tools:
   ```bash
   mise trust
   mise install      # Installs terraform, awscli, python
   uv sync --extra dev
   ```
4. Verify tools: `terraform --version && aws --version`

Present the project structure:

```
workspaces/financial-risk-streaming/
├── mise.toml                          # Tool versions + task runner
├── pyproject.toml                     # Python deps (databricks-sdk, opensearch-py)
├── databricks.yml                     # Asset Bundle — 3 pipelines + 4 jobs
├── infra/
│   ├── mise.toml                      # Terraform + AWS CLI tasks
│   ├── docker-compose.yml             # Postgres + Debezium + Redpanda
│   ├── debezium-connector.json        # CDC connector config
│   └── terraform/
│       ├── main.tf                    # EC2, OpenSearch (conditional), security groups
│       ├── variables.tf               # Region, instance type, enable_opensearch
│       ├── outputs.tf                 # Public IP, endpoints
│       ├── user-data.sh               # Cloud-init: Docker Compose up on boot
│       └── terraform.tfvars.sample
├── src/
│   ├── pipelines/
│   │   ├── app_streams/               # Pipeline 1: CDC from Kafka (continuous)
│   │   │   ├── financial/             #   transactions, market_prices
│   │   │   ├── counterparty/          #   counterparties, credit_ratings
│   │   │   └── operations/            #   offices, desks, assignments
│   │   ├── data_fabric/               # Pipeline 2: API via Auto Loader (continuous)
│   │   │   ├── compliance/            #   sanctions, KYC
│   │   │   ├── market_reference/      #   exchange rates, benchmarks
│   │   │   └── regulatory/            #   reporting requirements
│   │   └── analytics/                 # Pipeline 3: cross-domain Gold (triggered)
│   │       └── gold/
│   └── jobs/                          # Python batch jobs
│       ├── compliance/                #   fetch_sanctions, fetch_kyc
│       ├── market_reference/          #   fetch_exchange_rates, fetch_benchmark_rates
│       ├── regulatory/                #   fetch_reporting_requirements
│       └── opensearch/                #   backfill_opensearch
├── tests/
├── data/
│   └── seed.sql                       # PostgreSQL seed data (7 tables)
└── explorations/
```

Use `AskUserQuestion` to confirm the scaffold looks correct.

---

### Step 3 — Run Local Tests

```bash
mise run test       # pytest — CDC parsing, Gold ratio calculations
mise run lint       # ruff — code quality
```

Explain: these tests run locally with PySpark (no Databricks needed). They validate the transformation logic before deploying.

---

### Step 4 — Configure Databricks Credentials

**Check if `.env` already exists** with credentials set:

```bash
# Check for existing .env with both vars set (values redacted)
grep -E '^DATABRICKS_(HOST|TOKEN)=' .env 2>/dev/null | sed 's/=.*/=<set>/'
```

**If `.env` exists and both vars are set**, verify connectivity:
```bash
source .env
DATABRICKS_HOST=$DATABRICKS_HOST DATABRICKS_TOKEN=$DATABRICKS_TOKEN databricks workspace list /
```

Note: pass `DATABRICKS_HOST` and `DATABRICKS_TOKEN` explicitly as env vars — this project uses token auth via `.env`, not `~/.databrickscfg` profiles. The `databricks` CLI picks up these env vars automatically.

**If `.env` doesn't exist or vars are missing**:
1. Create `.env` from `.env.sample`: `cp .env.sample .env`
2. Tell the user to open `.env` in their editor and paste their `DATABRICKS_HOST` (workspace URL) and `DATABRICKS_TOKEN` (personal access token). Show them the exact lines to fill in:
   ```
   DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
   DATABRICKS_TOKEN=dapi...
   ```
3. Use `AskUserQuestion` to confirm they've saved the `.env` file — options: "Done, credentials saved" / "I need help getting a token"
4. Verify connectivity as above

**If `databricks workspace list /` fails with a bundle config error** (e.g., "cannot resolve bundle auth configuration"), this means `databricks.yml` is interfering. Run the check from outside the project dir or pass the env vars explicitly:
```bash
DATABRICKS_HOST=$DATABRICKS_HOST DATABRICKS_TOKEN=$DATABRICKS_TOKEN databricks workspace list /
```

Use `AskUserQuestion` to confirm Databricks auth works.

---

### Step 5 — Summary

| Component | Status | Cost |
|-----------|--------|------|
| Project scaffolded | ✓ | $0 |
| Tools installed (mise) | ✓ | $0 |
| Local tests passing | ✓ | $0 |
| Databricks auth configured | ✓ | $0 |
| AWS resources | Not provisioned | $0 |
| **Total cost so far** | | **$0** |

**Next:** Run `/silver-databricks-streaming:deploy-dev` to create the Unity Catalog schema and landing zone volumes on Databricks (still $0).
