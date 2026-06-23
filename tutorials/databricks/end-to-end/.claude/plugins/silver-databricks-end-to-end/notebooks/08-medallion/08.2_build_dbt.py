# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 8 · Build 2 of 3 — **dbt**, run as a Databricks **Job** (dbt task)
# MAGIC
# MAGIC The production way to run dbt on Databricks: a **Job with a native `dbt task`**. The dbt project is
# MAGIC staged as **workspace files** at `08-medallion/dbt_project/`; the Job runs `dbt build` on serverless,
# MAGIC executing the SQL against the Starter Warehouse (Databricks auto-generates the dbt profile from the
# MAGIC task's `warehouse_id` / `catalog` / `schema` — no token in the project). It builds the canonical
# MAGIC `silver_*` / `gold_*` tables (the same models as the repo's `dbt/models/`).
# MAGIC
# MAGIC The Job `silverline-dbt-job` is created via CLI in provisioning; this notebook **triggers it and waits**.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ## Trigger the dbt Job + wait

# COMMAND ----------

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

jobs = list(w.jobs.list(name="silverline-dbt-job"))
assert jobs, "Job 'silverline-dbt-job' not found — create it via CLI (provisioning)."
job_id = jobs[0].job_id
run = w.jobs.run_now(job_id=job_id).result()
print("silverline-dbt-job:", run.state.result_state, "|", run.state.life_cycle_state)

# Clickable links to the Job + this run (derived from the workspace URL — no hardcoded id).
host = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
displayHTML(
    f'🔗 <a href="{host}/jobs/{job_id}" target="_blank">Open <b>silverline-dbt-job</b></a> &nbsp;·&nbsp; '
    f'<a href="{host}/jobs/{job_id}/runs/{run.run_id}" target="_blank">this run</a> '
    f'(dbt logs, task graph, lineage)'
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## What the Job runs
# MAGIC A `dbt_task`: `commands=["dbt build --select tag:medallion"]`, `source=WORKSPACE`,
# MAGIC `project_directory=.../dbt_project`, `warehouse_id=<Starter Warehouse>`, `catalog=silverline`,
# MAGIC `schema=silver`. Open **Jobs & Pipelines → silverline-dbt-job** to see the dbt run logs + lineage.
# MAGIC
# MAGIC > 🔎 **Seeing the SQL dbt runs.** dbt models are **Jinja templates** (`{{ ref('silver_contracts') }}`,
# MAGIC > `{{ config(...) }}`) at the project path (`dbt_project/models/`) — not the final SQL. To see the **exact
# MAGIC > compiled SQL** dbt executed, open **SQL → Query History** and filter the Starter Warehouse: each
# MAGIC > statement carries a `/* {"app":"dbt", "node_id":"model.silverline.…"} */` comment and shows the resolved
# MAGIC > `create or replace table … as …` (the `{{ ref() }}` already rewritten to the real table). So on
# MAGIC > Databricks you **don't** need dbt Cloud or a local `dbt compile` to read what ran — it's in Query
# MAGIC > History. *(For completeness: `dbt compile` also writes the compiled SQL to `target/compiled/`, and dbt
# MAGIC > Cloud shows it in its IDE.)*
# MAGIC
# MAGIC Verify the gold it built:

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT segment, contract_count, active_contracts, total_principal, avg_apr, total_residual
# MAGIC FROM silverline.gold.gold_segment_portfolio
# MAGIC ORDER BY total_principal DESC;

# COMMAND ----------

# MAGIC %md ✅ dbt build done via a Job (canonical `gold_*`). Next: `08.3_build_sdp`, then `08.4_parity`.

# COMMAND ----------

# MAGIC %md
# MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
