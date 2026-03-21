---
description: "[Stage 6] Run CI/CD locally with act, then deploy to production"
---

# CI/CD with `act` — Local-First Deployment

Validate your CI/CD pipelines locally in Docker containers before pushing to GitHub. Faster feedback loops, fewer broken builds.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

This stage only requires **Stage 1 (scaffold-setup)** — the pipeline code, workflow files, and Databricks credentials must exist. Gold tables are **not** a prerequisite because CI/CD validates and deploys your code and bundle configuration — it doesn't depend on data already existing in tables. The CD pipeline itself creates/refreshes tables when it runs.

The learner needs:
- `databricks.yml` configured with all three layers
- `.github/workflows/ci.yml` and `cd.yml` present
- Local tests passing, lint clean
- `.env` with Databricks credentials

This stage teaches **local-first CI/CD**: run the same GitHub Actions workflows locally with `act` before pushing. The CD pipeline owns production deployment — not `mise run deploy:prod` directly.

---

## Instructions

---

### Step 1 — Verify Prerequisites

Check that the required tools are installed:

```bash
cd <target-directory>
```

Run these checks:

```bash
# Check act
act --version 2>/dev/null || echo "MISSING: act"

# Check Docker
docker --version 2>/dev/null || echo "MISSING: Docker"

# Check .env credentials
test -f .env && grep -q 'DATABRICKS_HOST=.' .env && echo "✓ DATABRICKS_HOST set" || echo "MISSING: DATABRICKS_HOST in .env"
test -f .env && grep -q 'DATABRICKS_TOKEN=.' .env && echo "✓ DATABRICKS_TOKEN set" || echo "MISSING: DATABRICKS_TOKEN in .env"

# Check pipeline code and workflows exist (scaffolding complete)
test -d src/financial_risk && echo "✓ Pipeline code exists" || echo "MISSING: src/financial_risk/"
test -f .github/workflows/ci.yml && echo "✓ CI workflow exists" || echo "MISSING: .github/workflows/ci.yml"
test -f .github/workflows/cd.yml && echo "✓ CD workflow exists" || echo "MISSING: .github/workflows/cd.yml"
test -f databricks.yml && echo "✓ Bundle config exists" || echo "MISSING: databricks.yml"
```

Present the results as a checklist:

```
┌──────────────────────────────────────────────────────┐
│  Stage 6 Prerequisites                               │
├──────────────────────────────────────────────────────┤
│  [ ] act              — brew install act             │
│  [ ] Docker           — Docker Desktop running       │
│  [ ] .env             — Databricks credentials set   │
│  [ ] Pipeline code    — src/financial_risk/ exists    │
│  [ ] CI/CD workflows  — .github/workflows/*.yml      │
│  [ ] Bundle config    — databricks.yml               │
└──────────────────────────────────────────────────────┘
```

Mark each as ✓ or ✗ based on the checks.

If `act` is missing, tell the user:

> Install act with: `brew install act`
> On first run, act will prompt you to choose a Docker image size. Choose **Medium** (~500MB) — it has everything you need.

If Docker is missing or not running, tell the user to install/start Docker Desktop.

If pipeline code or workflows are missing, tell the user to run `/silver-databricks:scaffold-setup` first.

**PAUSE** — use `AskUserQuestion` to confirm all prerequisites are met. Offer "All good — continue" and "I need to install something first".

---

### Step 2 — Explain CI/CD: Why Local-First

Tell the user:

> ### Why Local-First CI/CD?
>
> Most teams write CI/CD workflows, push to GitHub, wait for runners, discover failures, fix, push again. Each round trip takes 2-5 minutes — and you're debugging blind.
>
> **Local-first CI/CD** flips this: run the exact same GitHub Actions workflows in Docker containers on your machine. Same YAML, same steps, same environment. When it passes locally, it passes on GitHub.
>
> ```
>  Traditional CI/CD                     Local-First CI/CD
>  ─────────────────                     ──────────────────
>
>  edit code                             edit code
>     ↓                                     ↓
>  git push                              act pull_request    ← runs CI locally
>     ↓                                     ↓
>  wait 2-5 min...                       see results in ~30s
>     ↓                                     ↓
>  GitHub Actions runs                   fix if needed
>     ↓                                     ↓
>  check results (maybe fail)            act push --secret-file .secrets  ← runs CD locally
>     ↓                                     ↓
>  fix → push → wait → check...         git push             ← confident it works
> ```
>
> **`act`** is the tool that makes this work. It:
> 1. Reads your `.github/workflows/*.yml` files
> 2. Pulls a Docker image that mimics GitHub's `ubuntu-latest` runner
> 3. Executes each job and step in isolated containers
> 4. Reports pass/fail with the same output format as GitHub Actions
>
> Your project already has two workflows:
> - **`ci.yml`** — runs on pull requests: lint, test, validate bundle
> - **`cd.yml`** — runs on push to main: deploy bundle + run pipeline in prod

**PAUSE** — use `AskUserQuestion`. Offer "Continue — walk me through the workflows" and "I have questions about act".

---

### Step 3 — Walk Through `ci.yml`

Read `.github/workflows/ci.yml` and present:

> ### CI Pipeline (`ci.yml`)
>
> **Trigger:** `pull_request` to `main`
>
> | Job | Depends On | Steps |
> |---|---|---|
> | `lint` | — | checkout → setup-uv → install deps → ruff check → ruff format check |
> | `test` | `lint` | checkout → setup-uv → install deps → generate seed data → unit tests → integration tests |
> | `validate-bundle` | — | checkout → setup-cli → `databricks bundle validate` |
>
> **Dependency graph:**
>
> ```
>                ┌──────────┐
>  ┌─────────>   │  test    │
>  │             └──────────┘
>  │
>  ┌──────────┐
>  │   lint   │
>  └──────────┘
>
>  ┌──────────────────┐
>  │ validate-bundle  │   (runs in parallel with lint)
>  └──────────────────┘
> ```
>
> **Key points:**
> - `lint` must pass before `test` runs (`needs: lint`)
> - `validate-bundle` runs independently — checks that `databricks.yml` is valid without deploying
> - `astral-sh/setup-uv@v4` installs uv in the container — same tool you use locally
> - `databricks/setup-cli@main` installs the Databricks CLI

**PAUSE** — use `AskUserQuestion`. Offer "Continue — walk me through cd.yml" and "I have questions about CI".

---

### Step 4 — Walk Through `cd.yml`

Read `.github/workflows/cd.yml` and present:

> ### CD Pipeline (`cd.yml`)
>
> **Trigger:** `push` to `main`
>
> | Step | What It Does |
> |---|---|
> | `checkout` | Clone the repo |
> | `setup-cli` | Install Databricks CLI |
> | `deploy` | `databricks bundle deploy --target prod` |
> | `run` | `databricks bundle run financial_risk_pipeline --target prod` |
>
> **Secrets required:**
>
> | Secret | Maps To | Where It Comes From |
> |---|---|---|
> | `DATABRICKS_HOST` | Workspace URL | Your `.env` → `DATABRICKS_HOST` |
> | `DATABRICKS_TOKEN` | Personal Access Token | Your `.env` → `DATABRICKS_TOKEN` |
>
> **Key points:**
> - `environment: production` adds a protection rule on GitHub (manual approval before deploy). **Note:** `act` may skip jobs with `environment:` set — we'll handle this in the local run.
> - The CD pipeline deploys to `--target prod` — this is the production target in `databricks.yml`
> - After deploying, it runs the pipeline immediately — full Bronze → Silver → Gold refresh
>
> **Tutorial vs production:** The `run` step is included here so you can see the full end-to-end flow. In production, deployment and execution are separate concerns — pipeline runs are typically managed by a scheduler (Databricks Jobs, Airflow), not triggered directly from the CD step.

**PAUSE** — use `AskUserQuestion`. Offer "Continue — set up act" and "I have questions about CD".

---

### Step 5 — Configure `act`: Create `.secrets`

Tell the user:

> `act` needs your Databricks credentials to run the CD pipeline. GitHub Actions uses repository secrets — locally, `act` reads from a `.secrets` file. Let's create it from your `.env`.

Create the `.secrets` file:

```bash
# Extract credentials from .env and write to .secrets format
echo "DATABRICKS_HOST=$(grep DATABRICKS_HOST .env | cut -d= -f2-)" > .secrets
echo "DATABRICKS_TOKEN=$(grep DATABRICKS_TOKEN .env | cut -d= -f2-)" >> .secrets
```

Verify `.secrets` is gitignored:

```bash
grep -q '.secrets' .gitignore && echo "✓ .secrets is gitignored" || echo "✗ .secrets NOT in .gitignore — adding it"
```

If not gitignored, add it. Then confirm:

> ✓ `.secrets` created with Databricks credentials
> ✓ `.secrets` is in `.gitignore` — will never be committed
>
> **This file stays local.** On GitHub, you'd set these as repository secrets in Settings → Secrets → Actions.

**PAUSE** — use `AskUserQuestion`. Offer "Continue — run CI locally" and "I want to check the .secrets file first".

---

### Step 6 — Run CI Locally

Tell the user:

> Let's run the CI pipeline locally. This simulates what happens when you open a pull request.
>
> **First run warning:** `act` will download a Docker image (~500MB–1.5GB depending on the image size you chose). This is a one-time download.

Run:

```bash
act pull_request
```

**Troubleshooting:**

- **`databricks/setup-cli@main` fails**: This action may not work in act's Docker containers. If it fails, it's expected — the `validate-bundle` job needs the Databricks CLI installed differently in Docker. The lint and test jobs should still pass. Tell the user:
  > The `validate-bundle` job may fail in act because `databricks/setup-cli@main` expects GitHub's hosted runner environment. This is fine — lint and test are the critical gates. On GitHub, all three jobs will pass.

- **Java not found** (for PySpark tests): If integration tests need Spark, they may fail without Java in the container. Unit tests should pass. Tell the user which jobs passed and which failed, and explain why.

- **Docker not running**: Tell the user to start Docker Desktop.

Present results:

```
┌─────────────────────────────────────────────────┐
│  CI Results (act pull_request)                   │
├─────────────────────────────────────────────────┤
│  lint              ✓ / ✗                         │
│  test              ✓ / ✗                         │
│  validate-bundle   ✓ / ✗ (may fail locally)     │
└─────────────────────────────────────────────────┘
```

After presenting the results table, explain what just happened inside Docker:

> ### What just ran inside Docker
>
> Each job spun up a fresh `ubuntu-latest` container — no state carried over from your local machine. Here's what each one validated:
>
> | Job | What it did | Why it matters |
> |---|---|---|
> | **lint** | Installed uv + deps from scratch, ran `ruff check` (code quality) and `ruff format --check` (style) | Catches unused imports, style violations, and formatting drift — regardless of your local editor settings |
> | **test** | Installed Java 17 (Temurin) + Python 3.11 + deps, generated fresh seed data, ran 10 unit tests + 5 integration tests with PySpark | Proves the pipeline logic works in a clean environment — not just on your machine with your cached state |
> | **validate-bundle** | Installed the Databricks CLI, ran `databricks bundle validate` against `databricks.yml` | Confirms the Asset Bundle config is valid and deployable — catches schema errors, missing references, and typos |
>
> **The key point:** Everything ran in isolated containers with no access to your local Python, Java, `.env`, or `.venv`. If it passes here, it will pass on GitHub's hosted runners — which is the whole point of local-first CI/CD.

**PAUSE** — use `AskUserQuestion`. Offer "Continue — dry-run CD" and "I need to fix a failure first".

---

### Step 7 — Dry-Run CD

Tell the user:

> Before deploying to production, let's do a dry run. This validates the CD workflow without actually deploying anything.

Run:

```bash
act push --secret-file .secrets --dryrun
```

> A dry run parses the workflow, resolves secrets, and shows what *would* execute — without running any steps. This catches YAML syntax errors, missing secrets, and job configuration issues before you commit to a real deploy.

**Troubleshooting:**

- **`environment: production` causes job to be skipped**: `act` doesn't support GitHub's environment protection rules. If the deploy job is skipped, tell the user:
  > The `environment: production` line in `cd.yml` causes `act` to skip the job. For local runs, you can temporarily comment it out:
  > ```yaml
  > # environment: production  # uncomment for GitHub, comment for act
  > ```
  > This doesn't affect the GitHub Actions behavior — the protection rule only applies on GitHub.

Present dry-run output and confirm it looks correct.

**PAUSE** — use `AskUserQuestion`. Offer "Continue — deploy for real" and "I need to fix something first".

---

### Step 8 — Run CD for Real

Tell the user:

> This is the real deployment. `act` will run the CD pipeline in Docker — deploying your Asset Bundle to the production target and running the full pipeline.
>
> ```
>  What happens next:
>  ─────────────────
>  1. Docker container starts (ubuntu-latest image)
>  2. Databricks CLI installs inside the container
>  3. databricks bundle deploy --target prod
>  4. databricks bundle run financial_risk_pipeline --target prod
>  5. Full pipeline executes: Bronze → Silver → Gold
> ```
>
> This is exactly what GitHub Actions would do on push to main.

Run:

```bash
act push --secret-file .secrets
```

**Troubleshooting:**

- **`databricks/setup-cli@main` fails in Docker**: If the Databricks CLI setup action doesn't work in act's containers, offer a fallback:
  > The `databricks/setup-cli@main` action may not work in act's Docker environment. You can deploy to prod directly with:
  > ```bash
  > mise run deploy:prod
  > ```
  > This achieves the same result — the value of `act` is validating the workflow structure and catching issues before GitHub runs it.

- **`environment: production` skips the job**: Same fix as Step 7 — comment it out for local runs.

- **Authentication failure**: Check `.secrets` has the correct values. Run `cat .secrets` to verify (but don't display the token to the user — just confirm the format looks right).

If deployment succeeds:

> ✓ CD pipeline completed — production deployment via act!

If deployment fails but the workflow structure was validated:

> The workflow structure is valid. The deployment step may fail due to Docker/act limitations with the Databricks CLI action. You can deploy to prod directly with `mise run deploy:prod` — the key learning here is that the CI/CD workflow is validated and ready for GitHub.

**PAUSE** — use `AskUserQuestion`. Offer "Continue — verify production" and "I need to troubleshoot".

---

### Step 9 — Verify Production

Tell the user:

> Let's verify the production deployment by querying the Gold tables.

Run:

```bash
export $(grep -v '^#' .env | xargs)
WAREHOUSE_ID=$(databricks warehouses list -o json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
databricks api post /api/2.0/sql/statements --json "{\"statement\": \"SELECT 'gold_financial_ratios' as tbl, COUNT(*) as cnt FROM main.financial_risk.gold_financial_ratios UNION ALL SELECT 'gold_risk_exposure', COUNT(*) FROM main.financial_risk.gold_risk_exposure UNION ALL SELECT 'gold_portfolio_summary', COUNT(*) FROM main.financial_risk.gold_portfolio_summary\", \"warehouse_id\": \"$WAREHOUSE_ID\", \"wait_timeout\": \"50s\"}"
```

Present the results:

```
┌────────────────────────────┬───────┬───────────────────────┐
│  Table                     │ Rows  │  Status               │
├────────────────────────────┼───────┼───────────────────────┤
│  gold_financial_ratios     │  ~20  │  ✓ Production data    │
│  gold_risk_exposure        │  ~20  │  ✓ Production data    │
│  gold_portfolio_summary    │  var  │  ✓ Production data    │
└────────────────────────────┴───────┴───────────────────────┘
```

Adapt to actual counts.

> **Note:** On Databricks Free Edition, dev and prod targets may share the same catalog and schema — so you may see the same data as Stage 5. In a full Databricks deployment, prod would use a separate catalog or schema with stricter access controls.

**PAUSE** — use `AskUserQuestion`. Offer "Continue — see the full picture" and "I have questions about the prod tables".

---

### Step 10 — What Just Happened

Tell the user:

> Here's the full picture — from development to production:
>
> ```
>  Development (Stages 1–5)                    CI/CD (Stage 6)
>  ──────────────────────────                  ─────────────────────────────
>
>  ┌─────────────┐                             ┌──────────────────────┐
>  │ Scaffold &  │                             │  CI (pull_request)   │
>  │ Setup       │                             │  ┌────────────────┐  │
>  └──────┬──────┘                             │  │ lint           │  │
>         ↓                                    │  │ test           │  │
>  ┌─────────────┐                             │  │ validate-bundle│  │
>  │ Landing     │                             │  └────────────────┘  │
>  │ Zone        │                             └──────────┬───────────┘
>  └──────┬──────┘                                        ↓
>         ↓                                    ┌──────────────────────┐
>  ┌─────────────┐                             │  CD (push to main)   │
>  │ Bronze →    │                             │  ┌────────────────┐  │
>  │ Silver →    │  ──── git push ────────>    │  │ deploy --prod  │  │
>  │ Gold        │                             │  │ run pipeline   │  │
>  └─────────────┘                             │  └────────────────┘  │
>                                              └──────────────────────┘
>         ↑                                               ↑
>    mise run test                                  act pull_request
>    mise run deploy:dev                            act push --secret-file .secrets
>    (your local dev loop)                          (local CI/CD validation)
> ```
>
> **The workflow in practice:**
>
> | Step | Command | What Happens |
> |---|---|---|
> | 1. Develop | `mise run test` / `mise run deploy:dev` | Edit, test, deploy to dev target |
> | 2. Validate CI | `mise run act:ci` | Run lint + test + validate in Docker |
> | 3. Validate CD | `mise run act:cd:dry` | Dry-run the deploy workflow |
> | 4. Deploy prod | `mise run act:cd` | Full CD pipeline in Docker → prod |
> | 5. Push | `git push` | GitHub Actions runs the same workflows |
>
> **The key insight:** By the time you push to GitHub, you've already validated everything locally. No surprises, no waiting, no broken builds.

---

### Step 11 — Summary

Display a summary:

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 6 — CI/CD with act (Local-First Deployment) Complete!  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  CI Pipeline:   ✓ Lint + Test + Validate Bundle              │
│  CD Pipeline:   ✓ Deploy + Run Pipeline (prod target)        │
│  Local Runs:    ✓ Validated with act before pushing           │
│                                                               │
│  Workflows:                                                   │
│    .github/workflows/ci.yml   runs on pull_request            │
│    .github/workflows/cd.yml   runs on push to main            │
│                                                               │
│  New mise tasks:                                              │
│    mise run act:ci        Run CI locally (lint + test)        │
│    mise run act:cd:dry    Dry-run CD (validate without deploy)│
│    mise run act:cd        Deploy to prod via CD pipeline      │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  Complete Tutorial Pipeline                                   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Stage 1: Scaffold & Setup        /silver-databricks:scaffold-setup  │
│  Stage 2: Landing Zone            /silver-databricks:deploy-dev      │
│  Stage 3: Bronze (Staging)        /silver-databricks:run-bronze      │
│  Stage 4: Silver (ODS / DWH)     /silver-databricks:run-silver      │
│  Stage 5: Gold (Data Marts)       /silver-databricks:run-gold        │
│  Stage 6: CI/CD with act          /silver-databricks:run-cicd        │
│                                                               │
│  10 Delta tables · 13 expectations · 2 workflows · 1 tool    │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  What's next?                                                 │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Your pipeline is now production-ready with CI/CD:            │
│  - Push a PR → CI validates automatically                    │
│  - Merge to main → CD deploys to production                  │
│  - Before pushing, validate locally with act                 │
│                                                               │
│  From here, you could:                                        │
│  - Add GitHub branch protection rules requiring CI to pass   │
│  - Set up environment protection for production deploys      │
│  - Add Slack notifications on pipeline failures              │
│  - Schedule the pipeline for daily runs with Databricks Jobs │
│  - Connect BI tools to Gold tables for dashboards            │
│  - Build REST APIs wrapping Gold queries                     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Important

- **`act` requires Docker** — Docker Desktop must be running. First run downloads a ~500MB–1.5GB image depending on the chosen size.
- **`databricks/setup-cli@main` may not work in act** — this GitHub Action expects the hosted runner environment. If it fails, the lint/test jobs are the critical CI gates. Deploy to prod directly with `mise run deploy:prod` as a fallback.
- **`environment: production` in cd.yml** — `act` doesn't support GitHub's environment protection rules. Comment out this line for local runs if the deploy job is skipped. This doesn't affect GitHub behavior.
- **`.secrets` must never be committed** — it contains your Databricks credentials. It's in `.gitignore`.
- **Free Edition limitations** — dev and prod targets may share the same catalog/schema. In a full deployment, prod would use a separate catalog with access controls.
- If the SQL Statements API doesn't work on Free Edition, always fall back to the UI — Catalog browser and pipeline graph are reliable alternatives.
