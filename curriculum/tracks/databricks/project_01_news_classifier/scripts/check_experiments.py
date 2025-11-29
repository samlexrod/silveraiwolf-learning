"""
Quick script to verify experiments exist in Databricks
"""

import os
import sys
from dotenv import load_dotenv
import mlflow

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, "config", ".env")
load_dotenv(env_path)

# Configure MLflow
mlflow.set_tracking_uri("databricks")

# Get host
databricks_host = os.getenv("DATABRICKS_HOST", "").rstrip('/')

print("=" * 80)
print("CHECKING DATABRICKS EXPERIMENTS")
print("=" * 80)
print(f"\nDatabricks Host: {databricks_host}")
print(f"MLflow Tracking URI: databricks\n")

# Check experiments
experiments = [
    os.getenv("MLFLOW_EXPERIMENT_NAME_EXTERNAL", "/Users/samlexrod@gmail.com/news-classifier-external"),
    os.getenv("MLFLOW_EXPERIMENT_NAME_INTERNAL", "/Users/samlexrod@gmail.com/news-classifier-internal"),
]

for exp_name in experiments:
    print(f"\nChecking: {exp_name}")
    try:
        exp = mlflow.get_experiment_by_name(exp_name)
        if exp:
            print(f"  ✅ EXISTS")
            print(f"  Experiment ID: {exp.experiment_id}")
            print(f"  Direct URL: {databricks_host}/ml/experiments/{exp.experiment_id}")

            # Check for runs
            runs = mlflow.search_runs(experiment_ids=[exp.experiment_id], max_results=5)
            if len(runs) > 0:
                print(f"  Runs: {len(runs)} total")
                for idx, row in runs.iterrows():
                    print(f"    - {row['tags.mlflow.runName']} (Status: {row['status']})")
            else:
                print(f"  Runs: 0 (no runs yet)")
        else:
            print(f"  ❌ NOT FOUND")
            print(f"  Run this to create: mlflow run . -e track_a_external")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

print("\n" + "=" * 80)
print("HOW TO VIEW IN DATABRICKS UI")
print("=" * 80)
print("\n1. Open your Databricks workspace:")
print(f"   {databricks_host}")
print("\n2. In the left sidebar, click: Machine Learning")
print("\n3. Click: Experiments")
print("\n4. Look for:")
print(f"   - {experiments[0]}")
print(f"   - {experiments[1]}")
print("\nNote: Experiments appear in the /Users/<your-email>/ folder")
print("=" * 80)