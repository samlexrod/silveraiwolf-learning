"""
Daily Inference Pipeline - Production Model Serving
Demonstrates loading the champion model from Unity Catalog and running predictions

This is a production-ready pipeline that shows:
1. How to load the champion (production) model by alias from Unity Catalog
2. How to run predictions on production data
3. How to save prediction results to disk

This is NOT an experiment - it's a production inference pipeline that serves
the current champion model for daily predictions.

Usage:
    # Via Make (recommended)
    make daily-inference

    # Via MLflow (for Airflow/scheduled jobs)
    mlflow run . -e daily_inference

    # Direct Python
    python scripts/daily_inference.py
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_model_by_alias(
    catalog: str,
    schema: str,
    model_name: str,
    alias: str = "challenger"
) -> Optional[object]:
    """
    Load model from Unity Catalog by alias

    Args:
        catalog: Unity Catalog name
        schema: Schema name
        model_name: Model name
        alias: Alias to load (challenger or champion)

    Returns:
        Loaded MLflow model or None if not found
    """
    client = MlflowClient()
    full_model_name = f"{catalog}.{schema}.{model_name}"

    try:
        # Get model version by alias
        model_version = client.get_model_version_by_alias(full_model_name, alias)

        # Get model metadata
        tags = model_version.tags if hasattr(model_version, 'tags') else {}

        print(f"✓ Loading {alias} model:")
        print(f"  Version: {model_version.version}")
        print(f"  Provider: {tags.get('provider', 'unknown')}")
        print(f"  Model: {tags.get('model', 'unknown')}")
        print(f"  Accuracy: {float(tags.get('category_accuracy', 0.0)):.2%}")

        # Load the model
        model_uri = f"models:/{full_model_name}@{alias}"
        model = mlflow.pyfunc.load_model(model_uri)

        return model, model_version.version, tags

    except Exception as e:
        print(f"⚠️  Could not load {alias} model: {e}")
        return None, None, None


def run_daily_inference():
    """
    Run daily inference pipeline using the champion (production) model

    This is a production inference pipeline that loads the current champion model
    from Unity Catalog and runs predictions on production data.
    """
    print("=" * 80)
    print("DAILY INFERENCE PIPELINE - PRODUCTION MODEL SERVING")
    print("=" * 80)

    # Load environment and setup MLflow
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, "config", ".env")
    load_dotenv(env_path)

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
    mlflow.set_registry_uri(os.getenv("MLFLOW_REGISTRY_URI", "databricks-uc"))

    # Get Unity Catalog configuration
    catalog = os.getenv("UC_CATALOG", "main")
    schema = os.getenv("UC_SCHEMA", "news_classifier")
    model_name = "news_classifier"

    # Production always uses champion
    alias = "champion"

    print(f"\nProduction model: {alias}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Load the champion model
    print(f"\n[1/4] Loading {alias} model from Unity Catalog...")
    model, version, tags = load_model_by_alias(catalog, schema, model_name, alias)

    if model is None:
        print("\n❌ No champion model found. Please run experiments first.")
        print("   Run: make run-all")
        sys.exit(1)

    # Step 2: Load production data
    print(f"\n[2/4] Loading production data...")
    data_path = os.path.join(project_root, "data", "sample_news.json")

    with open(data_path, 'r') as f:
        articles = json.load(f)

    print(f"✓ Loaded {len(articles)} articles for inference")

    # Step 3: Run inference
    print(f"\n[3/4] Running inference with {alias} model...")

    # Prepare input DataFrame for the model
    # Convert articles to DataFrame format expected by model
    input_data = pd.DataFrame([
        {
            "title": article.get("title", ""),
            "content": article.get("content", ""),
            "category": "",  # Empty - model will predict
            "sentiment": ""  # Empty - model will predict
        }
        for article in articles
    ])

    # Call the model's predict method
    try:
        prediction_results = model.predict(input_data)
        print(f"✓ Generated {len(prediction_results)} predictions")

        # Convert predictions to output format
        predictions = []
        for i, (article, pred) in enumerate(zip(articles, prediction_results.to_dict('records')), 1):
            result = {
                "article_id": article.get("id", i),
                "title": article.get("title", ""),
                "predicted_category": pred.get("category", "Unknown"),
                "predicted_sentiment": pred.get("sentiment", "Unknown"),
                "expected_category": article.get("expected_category", "N/A"),
                "expected_sentiment": article.get("expected_sentiment", "N/A"),
                "timestamp": datetime.now().isoformat()
            }
            predictions.append(result)
    except Exception as e:
        print(f"   ⚠️  Prediction failed: {e}")
        print(f"   Note: The registered models are placeholder models for demonstration")
        sys.exit(1)

    # Step 4: Save predictions to file
    print(f"\n[4/4] Saving predictions...")

    # Create output directory if it doesn't exist
    output_dir = os.path.join(project_root, "output", "predictions")
    os.makedirs(output_dir, exist_ok=True)

    # Save predictions with timestamp
    predictions_file = f"predictions_{alias}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    predictions_path = os.path.join(output_dir, predictions_file)

    output_data = {
        "metadata": {
            "inference_date": datetime.now().isoformat(),
            "model_alias": alias,
            "model_version": version,
            "provider": tags.get("provider", "unknown"),
            "model_name": tags.get("model", "unknown"),
            "model_accuracy": float(tags.get("category_accuracy", 0.0)),
            "num_articles": len(articles),
            "num_predictions": len(predictions)
        },
        "predictions": predictions
    }

    with open(predictions_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✓ Saved predictions to: {predictions_path}")

    # Success summary
    print("\n" + "=" * 80)
    print("✅ DAILY INFERENCE COMPLETED")
    print("=" * 80)
    print(f"\nModel used: {alias} (v{version})")
    print(f"Provider: {tags.get('provider', 'unknown')}")
    print(f"Model: {tags.get('model', 'unknown')}")
    print(f"Articles processed: {len(articles)}")
    print(f"Predictions generated: {len(predictions)}")
    print(f"\nResults saved to:")
    print(f"  {predictions_path}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run daily inference pipeline with production champion model"
    )

    args = parser.parse_args()

    run_daily_inference()
