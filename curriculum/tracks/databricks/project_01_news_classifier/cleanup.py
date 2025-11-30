#!/usr/bin/env python
"""
Cleanup script to delete registered models and experiments

WARNING: This will permanently delete:
- All versions of the registered model in Unity Catalog
- All MLflow experiments and their runs
"""

import os
import sys
import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

# Load environment
load_dotenv('config/.env')

# Setup
mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'databricks'))
mlflow.set_registry_uri(os.getenv('MLFLOW_REGISTRY_URI', 'databricks-uc'))
client = MlflowClient()

# Configuration
UC_CATALOG = os.getenv('UC_CATALOG', 'main')
UC_SCHEMA = os.getenv('UC_SCHEMA', 'news_classifier')
MODEL_NAME = f"{UC_CATALOG}.{UC_SCHEMA}.news_classifier"
EXPERIMENT_EXTERNAL = os.getenv('MLFLOW_EXPERIMENT_NAME_EXTERNAL', '/Users/samlexrod@gmail.com/news-classifier-external')
EXPERIMENT_INTERNAL = os.getenv('MLFLOW_EXPERIMENT_NAME_INTERNAL', '/Users/samlexrod@gmail.com/news-classifier-internal')


def delete_model_versions():
    """Delete all versions of the Unity Catalog model"""
    print("=" * 80)
    print("DELETING REGISTERED MODEL")
    print("=" * 80)
    print(f"Model: {MODEL_NAME}\n")

    try:
        # Get all versions
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")

        if not versions:
            print(f"⚠️  No versions found for model '{MODEL_NAME}'")
            return

        print(f"Found {len(versions)} version(s) to delete:\n")

        # Delete each version
        for v in sorted(versions, key=lambda x: int(x.version), reverse=True):
            version_num = v.version
            print(f"  Deleting version {version_num}...")
            try:
                client.delete_model_version(MODEL_NAME, version_num)
                print(f"  ✓ Deleted version {version_num}")
            except Exception as e:
                print(f"  ❌ Failed to delete version {version_num}: {e}")

        print(f"\n✓ All versions deleted\n")

        # Delete the model itself
        print(f"Deleting model '{MODEL_NAME}'...")
        try:
            client.delete_registered_model(MODEL_NAME)
            print(f"✓ Model '{MODEL_NAME}' deleted\n")
        except Exception as e:
            print(f"⚠️  Could not delete model (may have already been deleted): {e}\n")

    except Exception as e:
        print(f"❌ Error deleting model: {e}\n")


def delete_experiment(experiment_name):
    """Delete an MLflow experiment and all its runs"""
    print(f"Deleting experiment: {experiment_name}")

    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)

        if experiment is None:
            print(f"  ⚠️  Experiment '{experiment_name}' not found\n")
            return

        experiment_id = experiment.experiment_id

        # Get all runs in the experiment
        runs = client.search_runs(experiment_ids=[experiment_id])
        print(f"  Found {len(runs)} run(s) to delete")

        # Delete all runs
        for run in runs:
            try:
                client.delete_run(run.info.run_id)
                print(f"    ✓ Deleted run {run.info.run_id}")
            except Exception as e:
                print(f"    ❌ Failed to delete run {run.info.run_id}: {e}")

        # Delete the experiment
        print(f"  Deleting experiment {experiment_id}...")
        try:
            client.delete_experiment(experiment_id)
            print(f"  ✓ Experiment '{experiment_name}' deleted\n")
        except Exception as e:
            print(f"  ❌ Failed to delete experiment: {e}\n")

    except Exception as e:
        print(f"  ❌ Error: {e}\n")


def main():
    print("\n" + "=" * 80)
    print("CLEANUP SCRIPT - DELETE MODELS AND EXPERIMENTS")
    print("=" * 80)
    print("\nWARNING: This will permanently delete:")
    print(f"  - Model: {MODEL_NAME} (all versions)")
    print(f"  - Experiment: {EXPERIMENT_EXTERNAL}")
    print(f"  - Experiment: {EXPERIMENT_INTERNAL}")
    print("\n" + "=" * 80)

    # Ask for confirmation
    response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Cleanup cancelled\n")
        sys.exit(0)

    print("\n" + "=" * 80)
    print("STARTING CLEANUP")
    print("=" * 80 + "\n")

    # Delete model versions
    delete_model_versions()

    # Delete experiments
    print("=" * 80)
    print("DELETING EXPERIMENTS")
    print("=" * 80)
    print()

    delete_experiment(EXPERIMENT_EXTERNAL)
    delete_experiment(EXPERIMENT_INTERNAL)

    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print("\n✓ All models and experiments have been deleted")
    print("\nYou can now run experiments fresh with:")
    print("  make run-all\n")


if __name__ == "__main__":
    main()
