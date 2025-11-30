"""
Run all experiments sequentially to determine Champion model

This script orchestrates running experiments from both Track A (External Models)
and Track B (Internal Databricks Models) to compare all providers and determine
which should receive the Champion alias in Unity Catalog.

All experiments register to the same model: main.news_classifier.news_classifier
"""

import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/.env')


def print_header(message: str, char: str = "="):
    """Print formatted header"""
    width = 80
    print("\n" + char * width)
    print(message.center(width))
    print(char * width + "\n")


def run_experiment(track: str, provider: str = None, model: str = None) -> bool:
    """
    Run a single experiment by calling Python scripts directly

    Args:
        track: 'external' or 'internal'
        provider: Provider name for external models (openai, anthropic)
        model: Model name for internal models

    Returns:
        bool: True if experiment succeeded, False otherwise
    """
    try:
        # Construct command
        if track == "external":
            script_path = "track_a_external/experiment_external.py"
            param_flag = f"--provider={provider}"
            display_name = f"External: {provider.upper()}"
        else:  # internal
            script_path = "track_b_internal/experiment_internal.py"
            param_flag = f"--model={model}"
            display_name = f"Internal: {model}"

        print(f"Running {display_name}...")
        print(f"  Script: {script_path}")
        print(f"  Parameter: {param_flag}")
        print()

        # Run directly via Python (avoids nested MLflow run issues)
        cmd = ["python", script_path, param_flag]

        # Execute and stream output
        # Clear MLflow run context to ensure each experiment starts its own run
        env = os.environ.copy()
        env.pop('MLFLOW_RUN_ID', None)  # Remove active run ID
        env.pop('MLFLOW_EXPERIMENT_ID', None)  # Remove experiment ID conflict

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=False,  # Stream output to console
            text=True
        )

        if result.returncode == 0:
            print(f"\n✅ {display_name} completed successfully\n")
            return True
        else:
            print(f"\n❌ {display_name} failed with exit code {result.returncode}\n")
            return False

    except Exception as e:
        print(f"\n❌ {display_name} failed with error: {e}\n")
        return False


def main():
    """Run all experiments sequentially"""

    print_header("RUNNING ALL EXPERIMENTS - CHAMPION COMPARISON")

    print("This will run experiments with all available models to determine the Champion:")
    print("  - Track A: OpenAI GPT-4o-mini, Anthropic Claude Sonnet 4.5")
    print("  - Track B: Databricks GPT-OSS-20B, Meta Llama 3.3 70B")
    print()
    print("All models will compete for the Champion alias in: main.news_classifier.news_classifier")
    print()
    print("⚠️  Note: Each experiment will run sequentially. This may take 20-30 minutes total.")
    print()

    print_header("Starting Experiments", "-")

    # Track results
    results = {}

    # Run all experiments
    experiments = [
        ("external", "openai", None, "1/4"),
        ("external", "anthropic", None, "2/4"),
        ("internal", None, "databricks-gpt-oss-20b", "3/4"),
        ("internal", None, "databricks-meta-llama-3-3-70b-instruct", "4/4"),
    ]

    for idx, (track, provider, model, progress) in enumerate(experiments, 1):
        name = provider if provider else model
        print(f"\n[{progress}] Running {name}...")
        print("-" * 80)

        success = run_experiment(track, provider, model)
        results[name] = success

        # Stop if experiment failed and user wants to abort
        if not success:
            print(f"\n⚠️  Experiment {name} failed. Continuing with remaining experiments...")

    # Print summary
    print_header("EXPERIMENT SUMMARY")

    print("Results:")
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name:40s} {status}")

    print()
    print_header("NEXT STEPS")

    successful_count = sum(1 for s in results.values() if s)
    total_count = len(results)

    if successful_count == total_count:
        print("✅ ALL EXPERIMENTS COMPLETE!")
        print()
        print("Check Unity Catalog to see the Champion:")
        print("  Model: main.news_classifier.news_classifier")
        print("  - Champion alias = Current best model")
        print("  - Challenger alias = Model that beat the champion")
        print("  - Candidate alias = Good models that didn't beat champion")
        print()
        print("To view results in Databricks UI:")
        print("  1. Go to Machine Learning → Experiments")
        print("  2. Check both experiment pages:")
        print(f"     - {os.getenv('MLFLOW_EXPERIMENT_NAME_EXTERNAL', 'External Experiment')}")
        print(f"     - {os.getenv('MLFLOW_EXPERIMENT_NAME_INTERNAL', 'Internal Experiment')}")
        print("  3. Go to Catalog → main → news_classifier → news_classifier")
        print("  4. Check the 'Aliases' tab to see Champion/Challenger/Candidate")
        return 0
    else:
        print(f"⚠️  {successful_count}/{total_count} experiments completed successfully")
        print()
        print("Review the errors above and:")
        print("  1. Check your credentials in config/.env")
        print("  2. Verify model endpoint availability")
        print("  3. Check the experiment logs in Databricks UI")
        return 1


if __name__ == "__main__":
    sys.exit(main())
