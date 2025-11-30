"""
MLflow Experiment for Internal Databricks Foundation Model Agent
Logs predictions, metrics, and registers model to Unity Catalog using ResponsesAgent
"""

import os
import json
import sys
from datetime import datetime
from typing import List, Dict, Any
import mlflow
import mlflow.pyfunc
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from track_b_internal.internal_agent import InternalNewsClassifierAgent
from config.news_categories import NEWS_CATEGORIES, SENTIMENT_CATEGORIES
from utils.mlflow_helpers import (
    setup_mlflow,
    log_predictions,
    calculate_metrics,
    log_confusion_matrix,
    log_model_parameters,
    log_model_metrics,
    register_model_to_uc
)
from utils.databricks_auth import verify_databricks_connection
from utils.production_criteria import (
    evaluate_performance_criteria,
    get_registration_tags,
    format_criteria_summary,
    ProductionCriteria
)


def load_sample_data(data_path: str) -> List[Dict[str, Any]]:
    """Load sample news data"""
    with open(data_path, 'r') as f:
        return json.load(f)


def run_experiment(
    model: str = "databricks-gpt-oss-20b",
    register_to_uc: bool = True,
    require_approval: bool = False,
    auto_gate: bool = True
):
    """
    Run Track B experiment with Databricks Foundation Model

    Args:
        model: Foundation model endpoint name
        register_to_uc: Register model to Unity Catalog
        require_approval: Require manual approval before registration (Option 1)
        auto_gate: Use automated gating with tags (Option 2)
    """
    print("=" * 80)
    print("TRACK B: DATABRICKS FOUNDATION MODEL EXPERIMENT")
    print("=" * 80)

    # Load environment variables (use absolute path to project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, "config", ".env")
    load_dotenv(env_path)

    if not os.path.exists(env_path):
        print(f"⚠️  Warning: .env file not found at {env_path}")
        print("   Run: make setup")

    # Verify Databricks connection
    print("\n[1/7] Verifying Databricks connection...")
    if not verify_databricks_connection():
        raise Exception("Failed to connect to Databricks")

    # Setup MLflow
    print("\n[2/7] Setting up MLflow experiment...")
    experiment_name = os.getenv(
        "MLFLOW_EXPERIMENT_NAME_INTERNAL",
        "/Users/default/news-classifier-internal"
    )
    experiment_id = setup_mlflow(experiment_name)

    # Initialize agent
    print(f"\n[3/7] Initializing internal agent (model={model})...")
    agent = InternalNewsClassifierAgent(model=model)
    print(f"✓ Using Databricks Foundation Model: {agent.model}")

    # Load data
    print("\n[4/7] Loading sample news data...")
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    data_path = os.path.join(data_dir, "sample_news.json")
    news_articles = load_sample_data(data_path)
    print(f"✓ Loaded {len(news_articles)} articles")

    # Start MLflow run (or use existing run from `mlflow run`)
    print("\n[5/7] Running classification and logging to MLflow...")

    # BEST PRACTICE: Check if mlflow run already created a run (GitHub issue #2735)
    # When MLFLOW_RUN_ID is set, mlflow run already created the run - don't call start_run()
    if os.getenv("MLFLOW_RUN_ID"):
        # mlflow run already created a run - just use it
        created_run = False
        if not mlflow.active_run():
            # Activate the run that mlflow run created
            mlflow.start_run(run_id=os.getenv("MLFLOW_RUN_ID"))
        print(f"Using existing MLflow run: {mlflow.active_run().info.run_id}")
    else:
        # Direct Python execution - create our own run
        mlflow.start_run(run_name=f"internal_{model.replace('databricks-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        created_run = True
        print(f"Started MLflow run: {mlflow.active_run().info.run_id}")

    try:

        # Log parameters
        params = {
            **agent.get_model_info(),
            "track": "B - Internal Foundation Model",
            "num_articles": len(news_articles),
            "timestamp": datetime.now().isoformat()
        }
        log_model_parameters(params)

        # Run predictions
        predictions = []
        y_true_category = []
        y_pred_category = []
        y_true_sentiment = []
        y_pred_sentiment = []

        print(f"\nClassifying {len(news_articles)} articles...")
        for i, article in enumerate(news_articles, 1):
            print(f"  [{i}/{len(news_articles)}] {article['title'][:50]}...")

            result = agent.classify(article['title'], article['content'])

            prediction = {
                "id": article["id"],
                "title": article["title"],
                "predicted_category": result["category"],
                "expected_category": article.get("expected_category", "Unknown"),
                "predicted_sentiment": result["sentiment"],
                "expected_sentiment": article.get("expected_sentiment", "Unknown"),
                "raw_response": result["raw_response"]
            }
            predictions.append(prediction)

            # Track for metrics
            if article.get("expected_category"):
                y_true_category.append(article["expected_category"])
                y_pred_category.append(result["category"])

            if article.get("expected_sentiment"):
                y_true_sentiment.append(article["expected_sentiment"])
                y_pred_sentiment.append(result["sentiment"])

        # Log predictions
        log_predictions(predictions)

        # Calculate and log metrics
        print("\n[6/7] Calculating metrics...")
        category_metrics = calculate_metrics(
            y_true_category,
            y_pred_category,
            labels=NEWS_CATEGORIES
        )
        sentiment_metrics = calculate_metrics(
            y_true_sentiment,
            y_pred_sentiment,
            labels=SENTIMENT_CATEGORIES
        )

        # Prefix metrics
        all_metrics = {
            f"category_{k}": v for k, v in category_metrics.items()
        }
        all_metrics.update({
            f"sentiment_{k}": v for k, v in sentiment_metrics.items()
        })

        log_model_metrics(all_metrics)

        # Log confusion matrices
        log_confusion_matrix(y_true_category, y_pred_category, NEWS_CATEGORIES)

        # Print summary
        print("\n" + "=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print(f"Category Accuracy:  {category_metrics['accuracy']:.2%}")
        print(f"Category F1 Score:  {category_metrics['f1_weighted']:.3f}")
        print(f"Sentiment Accuracy: {sentiment_metrics['accuracy']:.2%}")
        print(f"Sentiment F1 Score: {sentiment_metrics['f1_weighted']:.3f}")
        print("=" * 80)

        # OPTION 2: Automated gating with champion comparison
        passes_criteria = True
        criteria_reason = "Production criteria not evaluated"
        model_alias = None  # Which alias to assign (Champion, Challenger, Candidate)

        if auto_gate:
            print("\n" + format_criteria_summary(all_metrics))
            passes_criteria, criteria_reason = evaluate_performance_criteria(all_metrics)

            if not passes_criteria:
                print("\n⚠️  Model does NOT meet production criteria")
                print(f"   Reason: {criteria_reason}")
                print("   ❌ Will NOT register to Unity Catalog")
                register_to_uc = False
            else:
                print("\n✅ Model PASSES production criteria")

                # Check if it beats the current champion
                from utils.production_criteria import (
                    get_champion_metrics,
                    evaluate_champion_criteria,
                    check_duplicate_performance
                )
                catalog = os.getenv("UC_CATALOG", "main")
                schema = os.getenv("UC_SCHEMA", "news_classifier")
                # All experiments register to the same model for comparison
                model_name = "news_classifier"

                # First, check if identical performance already exists
                duplicate = check_duplicate_performance(catalog, schema, model_name, all_metrics)

                if duplicate:
                    print(f"\n⚠️  Model with identical performance already exists:")
                    print(f"   Version {duplicate['version']}: {duplicate['provider']}/{duplicate['model']}")
                    print(f"   Accuracy: {duplicate['accuracy']:.2%}")
                    print(f"   Alias: {duplicate['alias']}")
                    print("   ❌ Will NOT register duplicate model to Unity Catalog")
                    register_to_uc = False
                    model_alias = None
                else:
                    # No duplicate, proceed with champion comparison
                    champion_metrics = get_champion_metrics(catalog, schema, model_name)

                    if champion_metrics is None:
                        print("   ℹ️  No current champion - this will be the first registered model")
                        print("   ✅ Will register to Unity Catalog as 'champion'")
                        model_alias = "champion"
                    else:
                        champion_accuracy = champion_metrics.get('category_accuracy', 0.0)
                        new_accuracy = all_metrics.get('category_accuracy', 0.0)

                        beats_champion, champion_reason = evaluate_champion_criteria(
                            new_accuracy, champion_accuracy
                        )

                        print(f"   Current champion: {champion_accuracy:.2%} accuracy")
                        print(f"   New Model:        {new_accuracy:.2%} accuracy")

                        if beats_champion:
                            print(f"   ✅ {champion_reason}")
                            print("   ✅ Will register to Unity Catalog as 'challenger'")
                            print("      (Ready for A/B testing against champion)")
                            model_alias = "challenger"
                        else:
                            print(f"   ⚠️  {champion_reason}")
                            print("   ✅ Will register to Unity Catalog as 'candidate'")
                            print("      (Meets criteria but doesn't beat champion)")
                            model_alias = "candidate"

        # Log model using PythonModel
        print("\n[7/7] Logging model artifact...")

        # Create a simple wrapper class
        class NewsClassifierModel(mlflow.pyfunc.PythonModel):
            def predict(self, context, model_input):
                """Predict method for MLflow model"""
                # model_input is a pandas DataFrame or dict
                import pandas as pd

                if isinstance(model_input, pd.DataFrame):
                    results = []
                    for _, row in model_input.iterrows():
                        result = {
                            "category": row.get("category", "Unknown"),
                            "sentiment": row.get("sentiment", "Unknown")
                        }
                        results.append(result)
                    return pd.DataFrame(results)
                else:
                    return model_input

        # Create input example and signature for Unity Catalog
        import pandas as pd
        from mlflow.models.signature import infer_signature

        # Input example (what the model expects)
        input_example = pd.DataFrame({
            "title": ["Sample news headline"],
            "content": ["Sample news article content"],
            "category": ["politics"],
            "sentiment": ["positive"]
        })

        # Output example (what the model returns)
        output_example = pd.DataFrame({
            "category": ["politics"],
            "sentiment": ["positive"]
        })

        # Infer signature from examples
        signature = infer_signature(input_example, output_example)

        # Log the model with signature
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=NewsClassifierModel(),
            signature=signature,
            input_example=input_example,
            pip_requirements=[
                "mlflow",
                "databricks-sdk>=0.18.0",
                "python-dotenv>=1.0.0",
                "pandas"
            ]
        )

        run_id = mlflow.active_run().info.run_id
        print(f"✓ MLflow Run ID: {run_id}")

        # Register to Unity Catalog
        if register_to_uc:
            # OPTION 1: Manual approval gate
            if require_approval:
                print("\n" + "=" * 80)
                print("MANUAL APPROVAL REQUIRED")
                print("=" * 80)
                if passes_criteria:
                    print("✅ Model meets production criteria")
                else:
                    print("⚠️  Model does NOT meet production criteria")
                    print(f"   Reason: {criteria_reason}")

                response = input("\n🤔 Register to Unity Catalog? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("❌ Registration cancelled by user")
                    register_to_uc = False

        if register_to_uc:
            print("\nRegistering model to Unity Catalog...")
            catalog = os.getenv("UC_CATALOG", "main")
            schema = os.getenv("UC_SCHEMA", "news_classifier")
            # All experiments register to the same model for comparison
            model_name = "news_classifier"

            # Generate tags with production readiness
            tags = get_registration_tags(
                metrics=all_metrics,
                track="B",
                provider="databricks",
                model=model,
                passes_criteria=passes_criteria,
                reason=criteria_reason
            )

            # Update description based on criteria
            if passes_criteria:
                description = f"✅ PRODUCTION READY - {model} - {criteria_reason}"
            else:
                description = f"⚠️  EXPERIMENT ONLY - {model} - {criteria_reason}"

            try:
                version = register_model_to_uc(
                    model_name=model_name,
                    run_id=run_id,
                    catalog=catalog,
                    schema=schema,
                    description=description,
                    tags=tags,
                    alias=model_alias  # Set Champion, Challenger, or Candidate alias
                )
                print(f"✓ Registered as: {catalog}.{schema}.{model_name} (v{version})")
                if model_alias:
                    print(f"   Alias: {model_alias}")
                if passes_criteria:
                    print(f"   Status: ✅ PRODUCTION READY")
                else:
                    print(f"   Status: ⚠️  EXPERIMENT ONLY")
                print(f"   Tags: {tags}")
            except Exception as e:
                print(f"⚠ Could not register to UC (may need permissions): {e}")

    finally:
        # Only end the run if we created it (not if mlflow run created it)
        if created_run:
            mlflow.end_run()

    print("\n✓ Experiment complete!")
    print(f"View results: {os.getenv('DATABRICKS_HOST')}/ml/experiments/{experiment_id}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Track B Internal Foundation Model Experiment")
    parser.add_argument(
        "--model",
        type=str,
        default="databricks-gpt-oss-20b",
        choices=[
            # OpenAI models via Databricks
            "databricks-gpt-5-1",
            "databricks-gpt-5",
            "databricks-gpt-5-mini",
            "databricks-gpt-5-nano",
            "databricks-gpt-oss-120b",
            "databricks-gpt-oss-20b",
            # Google models
            "databricks-gemini-3-pro",
            "databricks-gemini-2.5-pro",
            "databricks-gemini-2.5-flash",
            "databricks-gemma-3-12b",
            # Meta Llama models
            "databricks-llama-4-maverick",
            "databricks-meta-llama-3-3-70b-instruct",
            "databricks-meta-llama-3-1-405b-instruct",
            "databricks-meta-llama-3-1-8b-instruct",
            "databricks-meta-llama-3-70b-instruct",
            # Anthropic Claude models
            "databricks-claude-sonnet-4-5",
            "databricks-claude-sonnet-4",
            "databricks-claude-opus-4-1",
            "databricks-claude-3.7-sonnet",
            # Databricks proprietary
            "databricks-dbrx-instruct",
            # Other open models
            "databricks-qwen3-next-80b-a3b-instruct"
        ],
        help="Databricks Foundation Model endpoint"
    )
    parser.add_argument(
        "--no-register",
        action="store_true",
        help="Skip Unity Catalog registration"
    )
    parser.add_argument(
        "--require-approval",
        action="store_true",
        help="Require manual approval before registration (Option 1: Manual Gate)"
    )
    parser.add_argument(
        "--no-auto-gate",
        action="store_true",
        help="Disable automated production criteria gating (Option 2: Auto Gate)"
    )

    args = parser.parse_args()

    run_experiment(
        model=args.model,
        register_to_uc=not args.no_register,
        require_approval=args.require_approval,
        auto_gate=not args.no_auto_gate
    )