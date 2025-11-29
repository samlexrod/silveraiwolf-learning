"""
OPTION 3: Standalone Model Promotion Script
Promotes a model from experiments to production registry after validation

Usage:
    python scripts/promote_to_production.py --run-id <mlflow_run_id>
    python scripts/promote_to_production.py --run-id <mlflow_run_id> --force
    python scripts/promote_to_production.py --run-id <mlflow_run_id> --alias Champion
"""

import os
import sys
import argparse
from typing import Dict, Optional
import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.production_criteria import (
    evaluate_performance_criteria,
    evaluate_champion_criteria,
    ProductionCriteria,
    format_criteria_summary
)


def get_current_champion_metrics(
    catalog: str,
    schema: str,
    model_name: str,
    alias: str = "Champion"
) -> Optional[Dict[str, float]]:
    """
    Get metrics from current production model

    Args:
        catalog: Unity Catalog catalog name
        schema: Unity Catalog schema name
        model_name: Model name
        alias: Alias to check (default: Champion)

    Returns:
        Dictionary of metrics or None if no champion exists
    """
    client = MlflowClient()
    full_name = f"{catalog}.{schema}.{model_name}"

    try:
        # Get model version with alias
        model_version = client.get_model_version_by_alias(full_name, alias)

        # Get run metrics
        run = mlflow.get_run(model_version.run_id)
        return dict(run.data.metrics)

    except Exception as e:
        print(f"ℹ️  No current {alias} found: {e}")
        return None


def promote_model_to_production(
    run_id: str,
    force: bool = False,
    alias: str = "Champion",
    criteria: ProductionCriteria = None
):
    """
    Promote a model to production after validation

    Args:
        run_id: MLflow run ID to promote
        force: Force promotion without validation
        alias: Alias to set (default: Champion)
        criteria: Production criteria (uses defaults if None)
    """
    if criteria is None:
        criteria = ProductionCriteria()

    print("=" * 80)
    print("OPTION 3: STANDALONE MODEL PROMOTION")
    print("=" * 80)
    print(f"\nRun ID: {run_id}")
    print(f"Target Alias: {alias}")
    print(f"Force: {force}")

    # Set MLflow tracking URI
    load_dotenv()
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")

    client = MlflowClient()

    # Get run details
    print("\n[1/5] Loading run details...")
    try:
        run = mlflow.get_run(run_id)
    except Exception as e:
        print(f"❌ Failed to load run: {e}")
        sys.exit(1)

    print(f"✓ Run Name: {run.info.run_name}")
    print(f"✓ Experiment: {run.info.experiment_id}")

    # Extract metrics
    metrics = dict(run.data.metrics)
    params = dict(run.data.params)

    print(f"\n[2/5] Validating performance criteria...")
    print(format_criteria_summary(metrics, criteria))

    # Check if meets criteria
    passes_criteria, reason = evaluate_performance_criteria(metrics, criteria)

    if not passes_criteria and not force:
        print("\n❌ PROMOTION BLOCKED")
        print(f"   Reason: {reason}")
        print("\n💡 Use --force to override this check")
        sys.exit(1)

    if force and not passes_criteria:
        print("\n⚠️  WARNING: Forcing promotion despite failed criteria")
        print(f"   Reason: {reason}")

    # Get model info from run
    print("\n[3/5] Extracting model information...")
    track = params.get("track", "Unknown")
    provider = params.get("provider", "Unknown")
    model = params.get("model", "Unknown")

    # Determine model name based on track
    catalog = os.getenv("UC_CATALOG", "main")
    schema = os.getenv("UC_SCHEMA", "news_classifier")

    if "External" in track or track == "A - External Model":
        model_name = f"external_{provider}_classifier"
    else:
        model_base = model.replace('databricks-', '').replace('-instruct', '')
        model_name = f"internal_{model_base}_classifier"

    full_model_name = f"{catalog}.{schema}.{model_name}"
    print(f"✓ Model Name: {full_model_name}")

    # Check against current champion (if exists)
    print("\n[4/5] Checking against current champion...")
    champion_metrics = get_current_champion_metrics(catalog, schema, model_name, alias)

    if champion_metrics:
        current_accuracy = champion_metrics.get('category_accuracy', 0.0)
        new_accuracy = metrics.get('category_accuracy', 0.0)

        beats_champion, champion_reason = evaluate_champion_criteria(
            new_accuracy,
            current_accuracy,
            criteria
        )

        if not beats_champion and not force:
            print("\n❌ PROMOTION BLOCKED")
            print(f"   Reason: {champion_reason}")
            print(f"   Current {alias}: {current_accuracy:.2%}")
            print(f"   New Model: {new_accuracy:.2%}")
            print("\n💡 Use --force to override this check")
            sys.exit(1)

        if force and not beats_champion:
            print(f"\n⚠️  WARNING: New model does not beat current {alias}")
            print(f"   {champion_reason}")

        print(f"✓ New model beats current {alias} by {(new_accuracy - current_accuracy):.2%}")
    else:
        print(f"✓ No current {alias} - will be first production model")

    # Register and set alias
    print("\n[5/5] Promoting model to production...")

    try:
        # Check if model is already registered
        artifact_path = "model"  # Standard path from experiments
        model_uri = f"runs:/{run_id}/{artifact_path}"

        # Register model
        model_version = mlflow.register_model(
            model_uri=model_uri,
            name=full_model_name,
            tags={
                "promoted_by": "standalone_script",
                "promoted_from_run": run_id,
                "production_alias": alias,
                "passes_criteria": str(passes_criteria).lower(),
                "forced": str(force).lower()
            }
        )

        print(f"✓ Registered as version: {model_version.version}")

        # Set alias
        client.set_registered_model_alias(
            name=full_model_name,
            alias=alias,
            version=model_version.version
        )

        print(f"✓ Set alias '{alias}' to version {model_version.version}")

        # Update description
        description = f"✅ PRODUCTION {alias.upper()} - Promoted via standalone script"
        if force:
            description += " (FORCED)"

        client.update_model_version(
            name=full_model_name,
            version=model_version.version,
            description=description
        )

        print("\n" + "=" * 80)
        print("✅ PROMOTION SUCCESSFUL")
        print("=" * 80)
        print(f"Model: {full_model_name}")
        print(f"Version: {model_version.version}")
        print(f"Alias: {alias}")
        print(f"Accuracy: {metrics.get('category_accuracy', 0.0):.2%}")
        print(f"F1 Score: {metrics.get('category_f1_weighted', 0.0):.3f}")
        print("\nTo load in production:")
        print(f"  model = mlflow.pyfunc.load_model('models:/{full_model_name}@{alias}')")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ PROMOTION FAILED")
        print(f"   Error: {e}")
        sys.exit(1)


def list_candidate_models(
    catalog: str = None,
    schema: str = None,
    min_accuracy: float = 0.85
):
    """
    List all experiment runs that could be promoted

    Args:
        catalog: Unity Catalog catalog name
        schema: Unity Catalog schema name
        min_accuracy: Minimum accuracy threshold
    """
    load_dotenv()
    mlflow.set_tracking_uri("databricks")

    if catalog is None:
        catalog = os.getenv("UC_CATALOG", "main")
    if schema is None:
        schema = os.getenv("UC_SCHEMA", "news_classifier")

    print("=" * 80)
    print("CANDIDATE MODELS FOR PROMOTION")
    print("=" * 80)

    # Search for runs in both experiments
    experiments = [
        os.getenv("MLFLOW_EXPERIMENT_NAME_EXTERNAL", "/Users/default/news-classifier-external"),
        os.getenv("MLFLOW_EXPERIMENT_NAME_INTERNAL", "/Users/default/news-classifier-internal")
    ]

    candidates = []

    for exp_name in experiments:
        try:
            experiment = mlflow.get_experiment_by_name(exp_name)
            if experiment:
                runs = mlflow.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    filter_string=f"metrics.category_accuracy >= {min_accuracy}",
                    order_by=["metrics.category_accuracy DESC"],
                    max_results=10
                )

                for _, run in runs.iterrows():
                    candidates.append({
                        "run_id": run["run_id"],
                        "run_name": run["tags.mlflow.runName"],
                        "accuracy": run["metrics.category_accuracy"],
                        "f1": run["metrics.category_f1_weighted"],
                        "experiment": exp_name
                    })
        except Exception as e:
            print(f"⚠️  Could not search experiment {exp_name}: {e}")

    if not candidates:
        print(f"\n⚠️  No candidates found with accuracy >= {min_accuracy:.0%}")
        return

    print(f"\nFound {len(candidates)} candidate(s):\n")
    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. Run ID: {candidate['run_id']}")
        print(f"   Name: {candidate['run_name']}")
        print(f"   Accuracy: {candidate['accuracy']:.2%}")
        print(f"   F1 Score: {candidate['f1']:.3f}")
        print(f"   Experiment: {candidate['experiment']}")
        print()

    print("To promote a model:")
    print(f"  python scripts/promote_to_production.py --run-id <run_id>")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Promote MLflow model to production with validation gates"
    )

    parser.add_argument(
        "--run-id",
        type=str,
        help="MLflow run ID to promote"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force promotion even if criteria not met"
    )
    parser.add_argument(
        "--alias",
        type=str,
        default="Champion",
        help="Alias to set (default: Champion). Options: Champion, Candidate, Staging"
    )
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="List all models eligible for promotion"
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=0.85,
        help="Minimum accuracy for candidate listing (default: 0.85)"
    )

    args = parser.parse_args()

    if args.list_candidates:
        list_candidate_models(min_accuracy=args.min_accuracy)
    elif args.run_id:
        promote_model_to_production(
            run_id=args.run_id,
            force=args.force,
            alias=args.alias
        )
    else:
        parser.print_help()
        print("\nExamples:")
        print("  # List candidate models")
        print("  python scripts/promote_to_production.py --list-candidates")
        print()
        print("  # Promote a specific run")
        print("  python scripts/promote_to_production.py --run-id abc123def456")
        print()
        print("  # Force promotion despite criteria")
        print("  python scripts/promote_to_production.py --run-id abc123def456 --force")
        print()
        print("  # Promote to Staging instead of Champion")
        print("  python scripts/promote_to_production.py --run-id abc123def456 --alias Staging")