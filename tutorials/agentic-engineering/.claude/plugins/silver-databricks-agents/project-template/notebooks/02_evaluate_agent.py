# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # 02 — Evaluate the Financial Risk Agent
# MAGIC
# MAGIC Run the evaluation set against the agent, compute quality metrics
# MAGIC using MLflow's evaluation framework, and compare candidate vs champion.

# COMMAND ----------

# MAGIC %pip install -q databricks-agents mlflow[genai] openai pandas
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import mlflow
import pandas as pd

# Set experiment
mlflow.set_experiment("/Shared/risk-agent".format(
    spark.sql("SELECT current_user()").first()[0]
))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load the evaluation dataset

# COMMAND ----------

# Load from the project's eval directory
eval_path = "../data/eval/evaluation_set.json"

with open(eval_path) as f:
    eval_data = json.load(f)

eval_df = pd.DataFrame(eval_data)
display(eval_df[["request", "expected_response"]])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate the agent

# COMMAND ----------

# Load the agent — from source for development, from registry for CI/CD
import sys
sys.path.insert(0, "../src")

from risk_agent.agent import FinancialRiskAgent

agent = FinancialRiskAgent()

# COMMAND ----------

# Run predictions on the eval set
predictions = []
for _, row in eval_df.iterrows():
    result = agent.predict(model_input={
        "messages": [{"role": "user", "content": row["request"]}]
    })
    predictions.append(result.get("content", ""))

eval_df["prediction"] = predictions
display(eval_df[["request", "expected_response", "prediction"]])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run MLflow evaluation

# COMMAND ----------

with mlflow.start_run(run_name="eval-candidate"):
    eval_result = mlflow.evaluate(
        data=eval_df,
        predictions="prediction",
        targets="expected_response",
        model_type="question-answering",
        extra_metrics=[],
    )

    print("--- Evaluation Metrics ---")
    for metric, value in eval_result.metrics.items():
        print(f"  {metric}: {value}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compare champion vs candidate (if both exist)

# COMMAND ----------

MODEL_NAME = "main.financial_risk.risk_agent"

try:
    client = mlflow.MlflowClient()

    champion_info = client.get_model_version_by_alias(MODEL_NAME, "champion")
    champion = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion")

    champion_predictions = []
    for _, row in eval_df.iterrows():
        result = champion.predict({
            "messages": [{"role": "user", "content": row["request"]}]
        })
        champion_predictions.append(result.get("content", ""))

    eval_df["champion_prediction"] = champion_predictions

    with mlflow.start_run(run_name="eval-champion"):
        champion_eval = mlflow.evaluate(
            data=eval_df,
            predictions="champion_prediction",
            targets="expected_response",
            model_type="question-answering",
        )

    print("--- Champion Metrics ---")
    for metric, value in champion_eval.metrics.items():
        print(f"  {metric}: {value}")

    print("\n--- Candidate Metrics (from above) ---")
    for metric, value in eval_result.metrics.items():
        print(f"  {metric}: {value}")

except Exception as e:
    print(f"Champion comparison skipped: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## View evaluation results in MLflow UI
# MAGIC
# MAGIC Navigate to the experiment page in the MLflow UI to see:
# MAGIC - Per-example scores in the artifact viewer
# MAGIC - Aggregate metrics on the run page
# MAGIC - Side-by-side comparison between champion and candidate runs
