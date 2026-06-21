# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 8 · Build 3 of 3 — **SDP / Lakeflow**, create + run the pipeline
# MAGIC
# MAGIC The *declarative* way: describe tables + data-quality **expectations** and Lakeflow manages the
# MAGIC materialized views. This notebook owns the pipeline lifecycle — **creates it if absent, then runs it**
# MAGIC — pointing at the source notebook `08-medallion/medallion_sdp` (`@dlt.table` + `@dlt.expect_or_drop`).
# MAGIC It builds the `*_sdp` tables. Run on **serverless**.
# MAGIC
# MAGIC > ⚠️ Free Edition allows **one active pipeline**. If create fails on that limit, delete any other
# MAGIC > pipeline first (or reuse the existing `silverline-medallion-sdp`).

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ## Create the pipeline if it doesn't exist

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import PipelineLibrary, NotebookLibrary

NAME = "silverline-medallion-sdp"
SRC = "/Workspace/Users/samlexrod@gmail.com/SilverAIWolf/08-medallion/sdp_project/medallion_sdp"
w = WorkspaceClient()

existing = list(w.pipelines.list_pipelines(filter=f"name LIKE '{NAME}'"))
if existing:
    pid = existing[0].pipeline_id
    print("reusing pipeline", pid)
else:
    created = w.pipelines.create(
        name=NAME, serverless=True, catalog="silverline", schema="gold",
        libraries=[PipelineLibrary(notebook=NotebookLibrary(path=SRC))],
    )
    pid = created.pipeline_id
    print("created pipeline", pid)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run it + wait
# MAGIC > ⏳ **First run is slow — be patient.** A serverless DLT pipeline **cold-starts**: the update can sit in
# MAGIC > **`CREATED`** for **10+ minutes with no visible progress** before it moves to `SETTING_UP_TABLES` →
# MAGIC > `RUNNING` → `COMPLETED` (verified live on Free Edition: ~12 min to first progress). **Don't assume it
# MAGIC > failed** if `CREATED` lingers — it's provisioning compute. The loop below waits up to ~25 min; you can
# MAGIC > also watch it live in **Jobs & Pipelines → silverline-medallion-sdp**. Re-runs are faster (compute warm).

# COMMAND ----------

upd = w.pipelines.start_update(pipeline_id=pid).update_id
print(f"update {upd} — first run cold-starts; 'CREATED' can persist 10+ min before progress (not a failure)")
for _ in range(100):   # ~25 min: cold start can sit in CREATED for 10+ min before SETTING_UP_TABLES
    st = w.pipelines.get_update(pipeline_id=pid, update_id=upd).update.state.value
    print("  ", st)
    if st in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(15)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT segment, contract_count, active_contracts, total_principal, avg_apr, total_residual
# MAGIC FROM silverline.gold.segment_portfolio_sdp
# MAGIC ORDER BY total_principal DESC;

# COMMAND ----------

# MAGIC %md ✅ SDP build done (`_sdp`). Now `08.4_parity` proves SQL == dbt == SDP.

# COMMAND ----------

# MAGIC %md
# MAGIC 🐺 *SilverAIWolf Learning — `silver-databricks-end-to-end`*
