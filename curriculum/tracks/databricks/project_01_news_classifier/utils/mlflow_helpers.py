"""
MLflow utilities for experiment tracking and model registration
"""

import os
import json
from typing import Dict, List, Any, Optional
import mlflow
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix


def setup_mlflow(experiment_name: str) -> str:
    """
    Configure MLflow tracking and experiment

    Args:
        experiment_name: Name of the MLflow experiment

    Returns:
        str: Experiment ID
    """
    # Set tracking and registry URIs
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
    mlflow.set_registry_uri(os.getenv("MLFLOW_REGISTRY_URI", "databricks-uc"))

    # FIX for mlflow run compatibility (GitHub issue #2735):
    # If MLFLOW_RUN_ID is set, mlflow run already created a run - use that experiment
    # Do NOT call set_experiment() as it will cause a mismatch
    if os.getenv("MLFLOW_RUN_ID"):
        active_run = mlflow.active_run()
        if active_run:
            experiment_id = active_run.info.experiment_id
            experiment = mlflow.get_experiment(experiment_id)
            print(f"✓ Using existing experiment: {experiment.name} (ID: {experiment_id})")
            return experiment_id
        else:
            # Run exists but not active yet - get its experiment ID
            run_id = os.getenv("MLFLOW_RUN_ID")
            client = mlflow.tracking.MlflowClient()
            run = client.get_run(run_id)
            experiment_id = run.info.experiment_id
            experiment = mlflow.get_experiment(experiment_id)
            print(f"✓ Using existing experiment: {experiment.name} (ID: {experiment_id})")
            return experiment_id

    # No mlflow run context - create or get experiment normally (for direct Python execution)
    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(experiment_name)
            print(f"✓ Created new experiment: {experiment_name} (ID: {experiment_id})")
        else:
            experiment_id = experiment.experiment_id
            print(f"✓ Using existing experiment: {experiment_name} (ID: {experiment_id})")

        mlflow.set_experiment(experiment_name)
        return experiment_id

    except Exception as e:
        raise Exception(f"Failed to setup MLflow experiment: {e}")


def log_predictions(
    predictions: List[Dict[str, Any]],
    artifact_path: str = "predictions"
) -> None:
    """
    Log predictions as MLflow artifact

    Args:
        predictions: List of prediction dictionaries
        artifact_path: Path to store artifact
    """
    df = pd.DataFrame(predictions)

    # Log as CSV
    csv_path = f"{artifact_path}.csv"
    df.to_csv(csv_path, index=False)
    mlflow.log_artifact(csv_path, artifact_path="predictions")

    # Log as JSON for easy parsing
    json_path = f"{artifact_path}.json"
    with open(json_path, 'w') as f:
        json.dump(predictions, f, indent=2)
    mlflow.log_artifact(json_path, artifact_path="predictions")

    # Clean up local files
    os.remove(csv_path)
    os.remove(json_path)

    print(f"✓ Logged {len(predictions)} predictions to MLflow")


def calculate_metrics(
    y_true: List[str],
    y_pred: List[str],
    labels: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Calculate classification metrics

    Args:
        y_true: True labels
        y_pred: Predicted labels
        labels: List of label names (optional)

    Returns:
        Dict[str, float]: Metrics dictionary
    """
    # Calculate basic accuracy
    accuracy = accuracy_score(y_true, y_pred)

    # Calculate precision, recall, f1
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average='weighted', zero_division=0
    )

    # Calculate per-class metrics
    precision_per_class, recall_per_class, f1_per_class, _ = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=labels, zero_division=0
    )

    metrics = {
        "accuracy": float(accuracy),
        "precision_weighted": float(precision),
        "recall_weighted": float(recall),
        "f1_weighted": float(f1),
    }

    # Add per-class metrics
    if labels:
        for i, label in enumerate(labels):
            if i < len(precision_per_class):
                metrics[f"precision_{label}"] = float(precision_per_class[i])
                metrics[f"recall_{label}"] = float(recall_per_class[i])
                metrics[f"f1_{label}"] = float(f1_per_class[i])

    return metrics


def log_confusion_matrix(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str]
) -> None:
    """
    Log confusion matrix as artifact

    Args:
        y_true: True labels
        y_pred: Predicted labels
        labels: List of label names
    """
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # Create confusion matrix DataFrame
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)

    # Save and log
    cm_path = "confusion_matrix.csv"
    cm_df.to_csv(cm_path)
    mlflow.log_artifact(cm_path, artifact_path="metrics")
    os.remove(cm_path)

    print("✓ Logged confusion matrix to MLflow")


def register_model_to_uc(
    model_name: str,
    run_id: str,
    catalog: str,
    schema: str,
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    alias: Optional[str] = None
) -> str:
    """
    Register model to Unity Catalog

    Args:
        model_name: Name of the model
        run_id: MLflow run ID
        catalog: Unity Catalog catalog name
        schema: Unity Catalog schema name
        description: Model description
        tags: Model tags
        alias: Model alias (e.g., "Champion", "Challenger", "Candidate")

    Returns:
        str: Registered model version
    """
    # Construct full model name with UC path
    full_model_name = f"{catalog}.{schema}.{model_name}"

    try:
        # Register model
        model_uri = f"runs:/{run_id}/model"
        model_version = mlflow.register_model(
            model_uri=model_uri,
            name=full_model_name,
            tags=tags
        )

        client = mlflow.tracking.MlflowClient()

        # Update model description if provided
        if description:
            client.update_registered_model(
                name=full_model_name,
                description=description
            )

        # Set alias if provided
        if alias:
            client.set_registered_model_alias(
                name=full_model_name,
                alias=alias,
                version=model_version.version
            )
            print(f"✓ Registered model: {full_model_name} (version {model_version.version}, alias: {alias})")
        else:
            print(f"✓ Registered model: {full_model_name} (version {model_version.version})")

        return model_version.version

    except Exception as e:
        print(f"✗ Failed to register model to Unity Catalog: {e}")
        raise


def log_model_parameters(params: Dict[str, Any]) -> None:
    """
    Log model parameters to MLflow

    Args:
        params: Dictionary of parameters
    """
    for key, value in params.items():
        # MLflow params must be strings
        mlflow.log_param(key, str(value))

    print(f"✓ Logged {len(params)} parameters to MLflow")


def log_model_metrics(metrics: Dict[str, float]) -> None:
    """
    Log metrics to MLflow

    Args:
        metrics: Dictionary of metrics
    """
    for key, value in metrics.items():
        mlflow.log_metric(key, value)

    print(f"✓ Logged {len(metrics)} metrics to MLflow")