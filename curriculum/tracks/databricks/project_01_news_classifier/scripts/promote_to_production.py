"""
OPTION 3: Standalone Champion Promotion Script
Promotes challenger to champion after manual approval

This script is designed to run as an MLflow entry point for orchestration with Airflow.

Workflow:
1. Check if a challenger exists (waiting for review)
2. If no challenger → exit gracefully
3. If challenger exists → show comparison with champion
4. Prompt for approval
5. If approved:
   - Current champion → defeated
   - Challenger → champion

Usage:
    # Via MLflow (recommended for Airflow orchestration)
    mlflow run . -e promote_challenger

    # Direct Python (for testing)
    python scripts/promote_to_production.py

    # Skip approval prompt (auto-approve for automated workflows)
    python scripts/promote_to_production.py --auto-approve
"""

import os
import sys
import argparse
from typing import Dict, Optional, Tuple
import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_model_by_alias(
    client: MlflowClient,
    catalog: str,
    schema: str,
    model_name: str,
    alias: str
) -> Optional[Tuple[object, Dict[str, float]]]:
    """
    Get model version and metrics by alias

    Args:
        client: MLflow client
        catalog: Unity Catalog name
        schema: Schema name
        model_name: Model name
        alias: Alias to look up (champion, challenger, candidate, defeated)

    Returns:
        Tuple of (model_version, metrics) or None if not found
    """
    full_model_name = f"{catalog}.{schema}.{model_name}"

    try:
        # Get model version by alias
        model_version = client.get_model_version_by_alias(full_model_name, alias)

        # Get metrics from tags (stored during registration)
        tags = model_version.tags if hasattr(model_version, 'tags') else {}

        metrics = {
            'category_accuracy': float(tags.get('category_accuracy', 0.0)),
            'category_f1': float(tags.get('category_f1', 0.0)),
            'provider': tags.get('provider', 'unknown'),
            'model': tags.get('model', 'unknown'),
            'version': model_version.version
        }

        return model_version, metrics

    except Exception as e:
        print(f"ℹ️  No {alias} found: {e}")
        return None


def promote_challenger_to_champion(auto_approve: bool = False):
    """
    Promote challenger to champion after approval

    Workflow:
    1. Check if challenger exists
    2. Show comparison with current champion
    3. Request approval (unless auto_approve=True)
    4. Demote champion → defeated
    5. Promote challenger → champion

    Args:
        auto_approve: Skip approval prompt (for automated workflows)
    """
    print("=" * 80)
    print("OPTION 3: CHAMPION PROMOTION WORKFLOW")
    print("=" * 80)

    # Load environment and setup MLflow
    # Find project root and load .env file
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, "config", ".env")
    load_dotenv(env_path)

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
    mlflow.set_registry_uri(os.getenv("MLFLOW_REGISTRY_URI", "databricks-uc"))

    client = MlflowClient()

    # Get Unity Catalog configuration
    catalog = os.getenv("UC_CATALOG", "main")
    schema = os.getenv("UC_SCHEMA", "news_classifier")
    model_name = "news_classifier"

    full_model_name = f"{catalog}.{schema}.{model_name}"

    print(f"\nModel: {full_model_name}")
    print(f"Auto-approve: {auto_approve}")

    # Step 1: Check if Challenger exists
    print("\n[1/5] Checking for challenger waiting for review...")
    challenger_info = get_model_by_alias(client, catalog, schema, model_name, "challenger")

    if challenger_info is None:
        print("\n⚠️  NO CHALLENGER FOUND")
        print("   No model is waiting for promotion to champion.")
        print("   Run experiments to create a new challenger.")
        print("=" * 80)
        return

    challenger_version, challenger_metrics = challenger_info

    print(f"✓ Challenger found: Version {challenger_metrics['version']}")
    print(f"  Provider: {challenger_metrics['provider']}")
    print(f"  Model: {challenger_metrics['model']}")
    print(f"  Accuracy: {challenger_metrics['category_accuracy']:.2%}")
    print(f"  F1 Score: {challenger_metrics['category_f1']:.3f}")

    # Step 2: Check current Champion
    print("\n[2/5] Checking current champion...")
    champion_info = get_model_by_alias(client, catalog, schema, model_name, "champion")

    if champion_info is None:
        print("ℹ️  No current champion found")
        print("   Challenger will become the first champion")
        has_champion = False
        champion_version = None
        champion_metrics = None
    else:
        has_champion = True
        champion_version, champion_metrics = champion_info

        print(f"✓ Champion found: Version {champion_metrics['version']}")
        print(f"  Provider: {champion_metrics['provider']}")
        print(f"  Model: {champion_metrics['model']}")
        print(f"  Accuracy: {champion_metrics['category_accuracy']:.2%}")
        print(f"  F1 Score: {champion_metrics['category_f1']:.3f}")

    # Step 3: Show comparison
    print("\n[3/5] Performance Comparison...")
    print("=" * 80)

    if has_champion:
        improvement = challenger_metrics['category_accuracy'] - champion_metrics['category_accuracy']

        print(f"{'Metric':<20} {'Current Champion':>20} {'Challenger':>20} {'Improvement':>15}")
        print("-" * 80)
        print(f"{'Accuracy':<20} {champion_metrics['category_accuracy']:>19.2%} {challenger_metrics['category_accuracy']:>19.2%} {improvement:>14.2%}")
        print(f"{'F1 Score':<20} {champion_metrics['category_f1']:>20.3f} {challenger_metrics['category_f1']:>20.3f}")
        print(f"{'Provider/Model':<20} {champion_metrics['provider']:>20} {challenger_metrics['provider']:>20}")
        print(f"{'Version':<20} {champion_metrics['version']:>20} {challenger_metrics['version']:>20}")
    else:
        print(f"{'Metric':<20} {'Challenger':>20}")
        print("-" * 80)
        print(f"{'Accuracy':<20} {challenger_metrics['category_accuracy']:>19.2%}")
        print(f"{'F1 Score':<20} {challenger_metrics['category_f1']:>20.3f}")
        print(f"{'Provider/Model':<20} {challenger_metrics['provider']:>20}")
        print(f"{'Version':<20} {challenger_metrics['version']:>20}")

    print("=" * 80)

    # Step 4: Request approval (unless auto-approve)
    print("\n[4/5] Approval Gate...")

    if auto_approve:
        print("✓ Auto-approve enabled - proceeding with promotion")
        approved = True
    else:
        print("\n🤔 Promote challenger to champion?")

        if has_champion:
            print(f"   • Current champion (v{champion_metrics['version']}) will be demoted to 'defeated'")
            print(f"   • Challenger (v{challenger_metrics['version']}) will become new champion")
        else:
            print(f"   • Challenger (v{challenger_metrics['version']}) will become first champion")

        response = input("\nProceed? (yes/no): ").strip().lower()
        approved = response in ['yes', 'y']

        if not approved:
            print("\n❌ PROMOTION CANCELLED")
            print("   Challenger remains in 'challenger' alias")
            print("=" * 80)
            return

    # Step 5: Execute promotion
    print("\n[5/5] Executing promotion...")

    try:
        # 5a. Demote current champion to defeated (if exists)
        if has_champion:
            print(f"   • Demoting champion v{champion_metrics['version']} → defeated...")
            client.set_registered_model_alias(
                name=full_model_name,
                alias="defeated",
                version=champion_metrics['version']
            )
            print(f"   ✓ Version {champion_metrics['version']} is now defeated")

        # 5b. Promote challenger to champion
        print(f"   • Promoting challenger v{challenger_metrics['version']} → champion...")
        client.set_registered_model_alias(
            name=full_model_name,
            alias="champion",
            version=challenger_metrics['version']
        )
        print(f"   ✓ Version {challenger_metrics['version']} is now champion")

        # 5c. Remove challenger alias (no longer needed)
        print(f"   • Removing 'challenger' alias from v{challenger_metrics['version']}...")
        client.delete_registered_model_alias(
            name=full_model_name,
            alias="challenger"
        )
        print(f"   ✓ Removed 'challenger' alias")

        # 5d. Update model version description
        new_description = f"🏆 CHAMPION - Promoted from Challenger"
        if has_champion:
            new_description += f" (replaced v{champion_metrics['version']})"

        client.update_model_version(
            name=full_model_name,
            version=challenger_metrics['version'],
            description=new_description
        )

        if has_champion:
            defeated_description = f"⚔️ DEFEATED - Replaced by v{challenger_metrics['version']}"
            client.update_model_version(
                name=full_model_name,
                version=champion_metrics['version'],
                description=defeated_description
            )

        # Success summary
        print("\n" + "=" * 80)
        print("✅ PROMOTION SUCCESSFUL")
        print("=" * 80)
        print(f"\n🏆 New Champion: Version {challenger_metrics['version']}")
        print(f"   Provider: {challenger_metrics['provider']}")
        print(f"   Model: {challenger_metrics['model']}")
        print(f"   Accuracy: {challenger_metrics['category_accuracy']:.2%}")
        print(f"   F1 Score: {challenger_metrics['category_f1']:.3f}")

        if has_champion:
            print(f"\n⚔️  Defeated: Version {champion_metrics['version']}")
            print(f"   Provider: {champion_metrics['provider']}")
            print(f"   Model: {champion_metrics['model']}")
            print(f"   Accuracy: {champion_metrics['category_accuracy']:.2%}")

        print(f"\nTo load new champion in production:")
        print(f"  model = mlflow.pyfunc.load_model('models:/{full_model_name}@champion')")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ PROMOTION FAILED")
        print(f"   Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Promote challenger to champion with approval gate"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip approval prompt and auto-approve promotion (for automated workflows)"
    )

    args = parser.parse_args()

    promote_challenger_to_champion(auto_approve=args.auto_approve)
