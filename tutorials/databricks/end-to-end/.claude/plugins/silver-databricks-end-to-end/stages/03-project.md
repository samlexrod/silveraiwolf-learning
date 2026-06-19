<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Project — local tooling (mise · uv · dbt)

Wire the local repo so every track can run dbt + scripts against your Free Edition workspace. The shared
scaffold lives at the **umbrella root** (`tutorials/databricks/end-to-end/`): `mise.toml`,
`pyproject.toml` (uv), and a `dbt/` project whose profile targets the **Starter Warehouse** + the
**`silverline`** catalog.

**Cost:** Free — installing local deps + a `dbt debug` / one-row query (auto-stops). No quota concern.

**Precondition:** `connect` (CLI authed, workspace URL + warehouse id captured) and `landing-zone`
(`silverline` + schemas) done.

This is an **interactive walkthrough** — pause after each section.

---

## Section 1 — Point the project at your workspace (non-secret env)

The scaffold reads `DATABRICKS_HOST` + `DATABRICKS_WAREHOUSE_ID` from a gitignored `.env`. **Claude** creates
it from `.env.sample` using the two values captured in `connect` (these are **not secret** — and `.env` is
gitignored anyway):

```bash
cd tutorials/databricks/end-to-end
cp .env.sample .env
# fill .env with the connect-stage values:
#   DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
#   DATABRICKS_WAREHOUSE_ID=<starter-warehouse-id>
```

**Pause.** Confirm `.env` has the host + warehouse id (render as `AskUserQuestion`).

---

## Section 2 — Auth: OAuth (default) — no token to manage

dbt + the scripts authenticate with **OAuth U2M**, reusing the cached token from `databricks auth login`
(the `free` profile created in `connect`). **No PAT needed** — `profiles.yml` sets `auth_type: oauth`, and
`run_sql.py` reuses the `free` profile's OAuth via the SDK. This is more secure (no long-lived token) and
lets Claude run the smoke-tests without holding a secret.

> 🔐 **PAT fallback** (only if OAuth is unavailable on a given host): export `DATABRICKS_TOKEN="dapi…"` in
> your shell (from **Settings → Developer → Access tokens**) — both dbt and `run_sql.py` use it when set.
> Keep it out of files; `.env` holds only the non-secret host + warehouse id.

**Pause.** Confirm the `free` OAuth profile is in place from `connect` (render as `AskUserQuestion`).

---

## Section 3 — Install deps + smoke-test the connection

**Claude** runs these (local tooling):

```bash
mise run setup        # uv sync (dbt-databricks, databricks-sdk, databricks-sql-connector)
mise run dbt:debug    # dbt debug — proves the profile reaches the warehouse + silverline catalog (OAuth)
```

Expect `dbt debug` → **All checks passed!** (connection ok, catalog `silverline` reachable). Then a
one-row query smoke:

```bash
mise run sql 'SELECT current_catalog(), current_user()'   # → silverline | <you>
```

> If `dbt debug` fails on auth, re-run `databricks auth login --profile free` (the cached OAuth token may
> have expired); if it fails on `http_path`, re-check the warehouse id. If the warehouse is asleep the first
> query wakes it (a few seconds; $0 at rest).

**Pause.** Confirm `dbt debug` passes and the SELECT returns `silverline` + your user (render as `AskUserQuestion`).

---

## Recap

- ✓ Shared **mise + uv + dbt** scaffold at the umbrella root, configured for your workspace
- ✓ dbt profile `databricks_free` → the **Starter Warehouse** + **`silverline`** catalog, via **OAuth** (no PAT)
- ✓ `dbt debug` green + a live SELECT — the project can reach Databricks
- ✓ No secret to manage — OAuth reuses the `free` profile's cached token; `.env` = non-secret host + warehouse id

**Cost now:** $0. **Phase A (Setup) complete** — stages 1–3 of 12 done; every later stage can now run.
