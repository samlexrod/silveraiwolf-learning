# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 8 · Build 4 — notebooks run as a **Job** (Workflows)
# MAGIC
# MAGIC The notebook/Workflows orchestration: the DDL build notebooks live in **`notebook_project/`**
# MAGIC (`build_silver` → `build_gold`) and a **Job runs them as tasks** (a 2-task DAG, gold depends on
# MAGIC silver). This notebook **builds that Job — pointing at `notebook_project/` — and runs it.** Same
# MAGIC pattern as `08.2_build_dbt`→`dbt_project/` and `08.3_build_sdp`→`sdp_project/`. → `*_nb`. Run on **serverless**.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.61.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ## Build the Job (create if absent) — tasks point at notebook_project/

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, NotebookTask, TaskDependency

NAME = "silverline-notebook-job"
NP = "/Workspace/Users/samlexrod@gmail.com/SilverAIWolf/08-medallion/notebook_project"
w = WorkspaceClient()

jobs = list(w.jobs.list(name=NAME))
if jobs:
    job_id = jobs[0].job_id
    print("reusing job", job_id)
else:
    created = w.jobs.create(
        name=NAME,
        tasks=[
            Task(task_key="silver", notebook_task=NotebookTask(notebook_path=f"{NP}/load_silver")),
            Task(task_key="gold", depends_on=[TaskDependency(task_key="silver")],
                 notebook_task=NotebookTask(notebook_path=f"{NP}/load_gold")),
        ],
    )
    job_id = created.job_id
    print("created job", job_id)

# COMMAND ----------

# MAGIC %md ## Run it + wait

# COMMAND ----------

run = w.jobs.run_now(job_id=job_id).result()
print(NAME, "->", run.state.result_state, "|", run.state.life_cycle_state)
for t in run.tasks:
    print(f"  {t.task_key:8} {t.state.life_cycle_state}/{t.state.result_state}")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT segment, contract_count, active_contracts, total_principal, avg_apr, total_residual
# MAGIC FROM silverline.gold.gold_segment_portfolio_nb
# MAGIC ORDER BY total_principal DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ The Job ran the `notebook_project/` notebooks (silver→gold) → `*_nb`. Open **Jobs & Pipelines →
# MAGIC silverline-notebook-job** to see the DAG + jump into each task notebook. ➡️ `08.5_parity`.
