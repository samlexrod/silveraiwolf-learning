# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # 01 — Explore the Financial Risk Agent
# MAGIC
# MAGIC Interactive notebook for developing and testing the financial risk agent.
# MAGIC Load the agent, call it with sample questions, and inspect responses + tool calls.

# COMMAND ----------

# MAGIC %pip install -q databricks-agents mlflow[genai] openai
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import mlflow

# Set the experiment for tracing
mlflow.set_experiment("/Shared/risk-agent".format(
    spark.sql("SELECT current_user()").first()[0]
))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load the agent

# COMMAND ----------

# Option 1: Load from source (development)
import sys
sys.path.insert(0, "../src")

from risk_agent.agent import FinancialRiskAgent

agent = FinancialRiskAgent()

# COMMAND ----------

# Option 2: Load from MLflow registry (after registration)
# agent = mlflow.pyfunc.load_model("models:/main.financial_risk.risk_agent@champion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test basic questions

# COMMAND ----------

# Simple counterparty lookup
response = agent.predict(model_input={
    "messages": [{"role": "user", "content": "What is the risk tier for Acme Corp?"}]
})
print(response["content"])

# COMMAND ----------

# Multi-step question requiring multiple tools
response = agent.predict(model_input={
    "messages": [{"role": "user", "content": "Which counterparties have CRITICAL risk and what are their financial ratios?"}]
})
print(response["content"])

# COMMAND ----------

# Portfolio-level question
response = agent.predict(model_input={
    "messages": [{"role": "user", "content": "Show me the full portfolio summary by sector."}]
})
print(response["content"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test streaming responses

# COMMAND ----------

for chunk in agent.predict_stream(model_input={
    "messages": [{"role": "user", "content": "Compare the risk profiles of Meridian Bank and Vertex Capital."}]
}):
    print(chunk, end="", flush=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inspect MLflow traces
# MAGIC
# MAGIC After running the cells above, check the MLflow experiment UI for detailed
# MAGIC traces showing tool calls, LLM inputs/outputs, and latency.

# COMMAND ----------

# View recent traces programmatically
experiment = mlflow.get_experiment_by_name("/Shared/risk-agent".format(
    spark.sql("SELECT current_user()").first()[0]
))

if experiment:
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        max_results=5,
        order_by=["start_time DESC"],
    )
    display(runs[["run_id", "start_time", "status"]])
