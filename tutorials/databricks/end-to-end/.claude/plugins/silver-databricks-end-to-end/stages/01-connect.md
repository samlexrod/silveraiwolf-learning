<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Connect — authenticate the CLI to Free Edition

Get a working **Databricks CLI** pointed at your Free Edition workspace, and capture the two values every
other track needs: the **workspace URL** and the **Starter Warehouse id**.

**Cost:** Free — signing in + reading metadata; no quota impact.

This is an **interactive walkthrough** — pause after each section. **Claude runs the CLI/local commands
itself** (the learner's machine has the CLI) and reports results; the learner only does the browser
steps — Free Edition signup and the OAuth approval.

---

## Section 1 — Sign up (or sign in) to Free Edition

1. Go to the Databricks **Free Edition** signup (`https://www.databricks.com/learn/free-edition` → *Get
   started*). Sign in with **email-OTP / Google / Microsoft** (Free Edition supports only these).
2. You land in a workspace at a URL like `https://<id>.cloud.databricks.com` (or `…databricks.com`).
   **Copy that workspace URL** — you'll use it for auth.

> 💡 Free Edition gives you **one workspace + one metastore**, and you're the **admin/owner** — there's no
> account console, so most things run as *you*. (Service principals **are** available, though — the
> `data-api` stage uses one as a non-owner API identity.)

**Pause.** Confirm you're in your Free Edition workspace and have copied the workspace URL (render as `AskUserQuestion`).

---

## Section 2 — Install / verify the Databricks CLI

**Claude:** run `databricks version` yourself first — don't ask the learner to check it.

```bash
databricks version    # expect the Go CLI v0.2xx+ (not the legacy Python 0.1x databricks-cli)
```

- If it prints **v0.2xx+**, you're set — say so and move on.
- If it's **missing or the legacy 0.1x**, tell the learner and offer to install/update:
  ```bash
  # macOS (Homebrew):
  brew tap databricks/tap && brew install databricks
  # or the universal installer (any platform):
  # curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
  ```

**Pause.** Report the version you found (render as `AskUserQuestion`); only ask the learner to act if an
install/update is needed.

---

## Section 3 — Authenticate (OAuth first, PAT fallback)

**Claude:** first run `databricks auth profiles` to see what already exists (a valid profile for the
learner's Free Edition host may already be there — reuse it). Ask the learner for their **workspace URL**
if you don't have it, then **run the OAuth login yourself**; the learner only completes the browser
approval.

**OAuth U2M** (preferred — no token to manage):
```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile free
# opens a browser; the learner approves. Then verify:
databricks auth profiles
```

> ⚠️ **OAuth can be flaky on some Free Edition hosts.** If `auth login` errors or hangs, use a **PAT**:
> in the workspace UI → **Settings → Developer → Access tokens → Generate new token**, copy it, then:
> ```bash
> databricks configure --profile free --host https://<your-workspace>.cloud.databricks.com
> #   (paste the PAT when prompted for "Personal Access Token")
> ```
> The token is stored in `~/.databrickscfg` (your machine) — **never commit it**.

**Pause.** After the learner approves in the browser, **you run `databricks auth profiles`** and confirm a
`free` profile (or reused profile) exists (render as `AskUserQuestion`).

---

## Section 4 — Verify + capture the two values

**Claude:** run both commands yourself with the `free` profile and report the values — don't ask the
learner to run them.

```bash
# 1) Identity — proves auth works:
databricks --profile free current-user me | jq '{userName, active}'

# 2) The Starter Warehouse — Free Edition auto-creates ONE serverless 2X-Small warehouse (you can't make another):
databricks --profile free warehouses list -o json \
  | jq -r '.[] | "\(.id)  \(.name)  \(.warehouse_type)  \(.state)"'
```

Note the **warehouse id** of the Starter Warehouse (often named *"Starter Warehouse"* / *"Serverless
Starter Warehouse"*). Save both values for the next stages — they're **not secret**, so a local note is fine:

```bash
# e.g. jot them down; project wires them into mise + dbt:
#   DATABRICKS_HOST = https://<your-workspace>.cloud.databricks.com
#   WAREHOUSE_ID    = <starter-warehouse-id>
```

> If `warehouses list` is empty, open **SQL Warehouses** in the UI once — Free Edition provisions the
> Starter Warehouse on first visit. It auto-stops when idle ($0 / no quota burn at rest).

**Pause.** Report that `current-user me` returned the learner's user and that you've captured the workspace
URL + Starter Warehouse id (render as `AskUserQuestion`).

---

## Recap

- ✓ A **Free Edition** workspace (you're the owner; one workspace + metastore)
- ✓ The **Databricks CLI** authenticated as a `free` profile (OAuth or PAT)
- ✓ Verified with `current-user me`
- ✓ Captured the **workspace URL** + the **Starter Warehouse id** (the one serverless SQL warehouse)

**Cost now:** $0 — auth + metadata only.
