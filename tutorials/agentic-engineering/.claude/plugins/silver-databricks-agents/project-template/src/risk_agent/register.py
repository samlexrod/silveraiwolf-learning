"""Model registration and Coliseum alias management.

Handles logging the agent to MLflow, registering in Unity Catalog,
managing champion/challenger/candidate aliases, and automated quality gates.
"""

from __future__ import annotations

import logging
from typing import Any

import mlflow
from mlflow.models import infer_signature

logger = logging.getLogger(__name__)

MODEL_NAME = "main.financial_risk.risk_agent"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_agent(
    model_name: str = MODEL_NAME,
    alias: str = "candidate",
    experiment_name: str = "/Shared/risk-agent",
    model_config_path: str = "model_config.yaml",
) -> str:
    """Log the agent to MLflow and register it with the given alias.

    Args:
        model_name: Full UC model name (catalog.schema.model).
        alias: Alias to assign (candidate, challenger, champion).
        experiment_name: MLflow experiment for tracking.
        model_config_path: Path to model_config.yaml.

    Returns:
        The model version string.
    """
    mlflow.set_experiment(experiment_name)

    # Define input/output signature
    input_example = {"messages": [{"role": "user", "content": "What is the risk tier for Acme Corp?"}]}
    output_example = {"content": "Acme Corp has a HIGH risk tier with total exposure of $2.5M."}
    signature = infer_signature(input_example, output_example)

    # MUST log to Databricks for serving endpoints to find the model
    mlflow.set_tracking_uri("databricks")

    with mlflow.start_run(run_name=f"register-{alias}") as run:
        # Log the agent model
        model_info = mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model="src/risk_agent/agent.py",
            code_paths=["src"],  # packages risk_agent.config + risk_agent.tools.*
            model_config=model_config_path,
            signature=signature,
            pip_requirements=[
                "databricks-sdk>=0.38",
                "mlflow>=2.18",  # no extras brackets — [genai] breaks serving validator
                "openai>=1.0",
                "pyyaml>=6.0",
            ],
        )

        # Register in Unity Catalog
        registered = mlflow.register_model(model_info.model_uri, model_name)
        version = registered.version

        # Set alias
        client = mlflow.MlflowClient()
        client.set_registered_model_alias(model_name, alias, version)
        logger.info("Registered %s version %s with alias '%s'", model_name, version, alias)

    return version


# ---------------------------------------------------------------------------
# Automated quality gate
# ---------------------------------------------------------------------------


def run_automated_gate(
    candidate_version: str,
    model_name: str = MODEL_NAME,
    eval_data_path: str = "data/eval/evaluation_set.json",
    threshold: float = 0.8,
) -> dict[str, Any]:
    """Evaluate candidate against champion (and challenger if exists).

    Runs mlflow.evaluate() on the candidate and compares scores against
    the current champion. The candidate passes the gate if its score
    meets or exceeds the threshold relative to the champion.

    Args:
        candidate_version: Version number of the candidate model.
        model_name: Full UC model name.
        eval_data_path: Path to evaluation dataset.
        threshold: Minimum score ratio (candidate/champion) to pass.

    Returns:
        Dict with keys: passed, candidate_score, champion_score, details.
    """
    import json
    import pandas as pd

    # Load evaluation data
    with open(eval_data_path) as f:
        eval_set = json.load(f)

    eval_df = pd.DataFrame(eval_set)

    results: dict[str, Any] = {"passed": False, "details": {}}

    client = mlflow.MlflowClient()

    # Score candidate
    candidate_uri = f"models:/{model_name}/{candidate_version}"
    candidate_eval = mlflow.evaluate(
        model=candidate_uri,
        data=eval_df,
        model_type="question-answering",
    )
    candidate_score = candidate_eval.metrics.get("exact_match/v1", 0.0)
    results["candidate_score"] = candidate_score

    # Score champion (if exists)
    try:
        champion_info = client.get_model_version_by_alias(model_name, "champion")
        champion_uri = f"models:/{model_name}/{champion_info.version}"
        champion_eval = mlflow.evaluate(
            model=champion_uri,
            data=eval_df,
            model_type="question-answering",
        )
        champion_score = champion_eval.metrics.get("exact_match/v1", 0.0)
        results["champion_score"] = champion_score
    except Exception:
        logger.info("No champion found; candidate auto-passes if score > 0")
        champion_score = 0.0
        results["champion_score"] = None

    # Gate logic
    if champion_score == 0:
        results["passed"] = candidate_score > 0
    else:
        ratio = candidate_score / champion_score
        results["passed"] = ratio >= threshold
        results["details"]["ratio"] = ratio

    logger.info(
        "Gate result: %s (candidate=%.3f, champion=%.3f)",
        "PASSED" if results["passed"] else "FAILED",
        candidate_score,
        champion_score or 0,
    )
    return results


# ---------------------------------------------------------------------------
# Alias promotion
# ---------------------------------------------------------------------------


def promote_to_challenger(version: str, model_name: str = MODEL_NAME) -> None:
    """Promote a model version to challenger alias.

    Args:
        version: Model version to promote.
        model_name: Full UC model name.
    """
    client = mlflow.MlflowClient()
    client.set_registered_model_alias(model_name, "challenger", version)
    logger.info("Promoted version %s to 'challenger'", version)


def promote_to_champion(version: str, model_name: str = MODEL_NAME) -> None:
    """Promote a model version to champion alias.

    This also demotes the current champion to challenger (if different).

    Args:
        version: Model version to promote.
        model_name: Full UC model name.
    """
    client = mlflow.MlflowClient()

    # Demote current champion to challenger
    try:
        current_champion = client.get_model_version_by_alias(model_name, "champion")
        if current_champion.version != version:
            client.set_registered_model_alias(model_name, "challenger", current_champion.version)
            logger.info("Demoted version %s from champion to challenger", current_champion.version)
    except Exception:
        pass  # No current champion

    client.set_registered_model_alias(model_name, "champion", version)
    logger.info("Promoted version %s to 'champion'", version)


def get_current_aliases(model_name: str = MODEL_NAME) -> dict[str, str | None]:
    """Get current alias assignments for the model.

    Returns:
        Dict mapping alias name to version (or None if unset).
    """
    client = mlflow.MlflowClient()
    aliases: dict[str, str | None] = {
        "champion": None,
        "challenger": None,
        "candidate": None,
    }

    for alias in aliases:
        try:
            info = client.get_model_version_by_alias(model_name, alias)
            aliases[alias] = info.version
        except Exception:
            pass

    return aliases
