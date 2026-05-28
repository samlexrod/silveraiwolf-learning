"""Configuration loader for the financial risk agent.

Loads model_config.yaml via MLflow's get_model_config() when running inside
a Databricks Model Serving endpoint, with a fallback to the local YAML file
for development.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def load_model_config() -> dict[str, Any]:
    """Load model configuration from MLflow ModelConfig or local YAML.

    Resolution order:
    1. mlflow.models.ModelConfig() — reads embedded config in serving,
       falls back to model_config.yaml locally
    2. Direct YAML load — fallback if ModelConfig is unavailable

    Environment variables DATABRICKS_HOST and DATABRICKS_TOKEN are merged
    into the config if present.

    Returns:
        Dict with keys: llm_endpoint, temperature, max_tokens, system_prompt,
        and optionally databricks_host, databricks_token.
    """
    config: dict[str, Any] = {}

    # Try MLflow ModelConfig first (works in both serving and local dev)
    try:
        from mlflow.models import ModelConfig

        mc = ModelConfig(development_config="model_config.yaml")
        config = mc.to_dict()
    except Exception:
        # Fall back to direct YAML load
        config_path = Path(__file__).resolve().parent.parent.parent / "model_config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
        else:
            raise FileNotFoundError(
                f"model_config.yaml not found at {config_path} and "
                "mlflow.models.ModelConfig() is not available."
            )

    # Merge credentials from environment (not in model_config.yaml for security)
    config.setdefault("databricks_host", os.getenv("DATABRICKS_HOST", ""))
    config.setdefault("databricks_token", os.getenv("DATABRICKS_TOKEN", ""))

    return config
