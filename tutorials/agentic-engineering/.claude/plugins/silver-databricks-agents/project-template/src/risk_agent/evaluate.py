"""MLflow 3.x native evaluation module.

Uses mlflow.genai built-in scorers, datasets, and labeling sessions
instead of custom LLM judge calls. This is the single evaluation backbone
used by the Automated Gate, DSPy optimization, and MemAlign alignment.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import mlflow
from mlflow.genai.scorers import (
    Correctness,
    Guidelines,
    RelevanceToQuery,
    RetrievalGroundedness,
    Safety,
)

logger = logging.getLogger(__name__)

EXPERIMENT_NAME = "/Shared/risk-agent"


# ---------------------------------------------------------------------------
# Built-in Scorers — the evaluation backbone
# ---------------------------------------------------------------------------

def get_scorers() -> list:
    """Return the standard set of scorers for the financial risk agent.

    These scorers are used across:
    - Stage 5: Baseline evaluation
    - Stage 7: Automated Gate (candidate vs champion)
    - Stage 10: MemAlign alignment
    - Playground: DSPy optimization metric
    """
    return [
        Correctness(),
        RetrievalGroundedness(),
        RelevanceToQuery(),
        Safety(),
        Guidelines(
            name="risk_domain_guidelines",
            guidelines=(
                "The response must cite specific counterparty names, risk tiers, and numerical values "
                "from the tool results. It must not give financial advice or make investment recommendations. "
                "It must present data in tables when showing multiple counterparties. "
                "It must not explain its methodology — lead with the answer, not the process."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Dataset Management
# ---------------------------------------------------------------------------

def create_eval_dataset(
    name: str = "risk-agent-eval-v1",
) -> Any:
    """Create and register an evaluation dataset in MLflow.

    The dataset is stored as a Unity Catalog table and visible in
    the MLflow UI under Evaluation > Datasets.

    Returns:
        An EvaluationDataset object.
    """
    mlflow.set_experiment(EXPERIMENT_NAME)

    dataset = mlflow.genai.create_dataset(name=name)
    logger.info("Created dataset: %s", name)
    return dataset


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_from_traces(
    model_id: str | None = None,
    scorers: list | None = None,
) -> Any:
    """Run evaluation on existing traces using built-in scorers.

    This evaluates traces already logged in MLflow — no need to re-run
    the agent. The scorers inspect the trace spans for inputs, outputs,
    retrieved context, and tool calls.

    Args:
        model_id: The model ID to filter traces. If None, uses recent traces.
        scorers: List of scorers. Defaults to get_scorers().

    Returns:
        EvaluationResult with metrics and per-row assessments.
    """
    mlflow.set_experiment(EXPERIMENT_NAME)

    if scorers is None:
        scorers = get_scorers()

    if model_id:
        trace_df = mlflow.search_traces(model_id=model_id)
    else:
        exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        trace_df = mlflow.search_traces(experiment_ids=[exp.experiment_id])

    if trace_df.empty:
        logger.warning("No traces found for evaluation")
        return None

    result = mlflow.genai.evaluate(
        data=trace_df,
        scorers=scorers,
    )

    logger.info("Evaluation complete: %d traces scored", len(trace_df))
    return result


def evaluate_with_predict(
    predict_fn: Any,
    eval_data: list[dict],
    scorers: list | None = None,
) -> Any:
    """Run evaluation by calling a predict function on eval data.

    This is the path for comparing prompts — pass a predict function
    that uses a specific system prompt, and the eval data with questions.

    Args:
        predict_fn: A callable that takes input dict and returns output.
        eval_data: List of dicts with at least 'inputs' key.
        scorers: List of scorers. Defaults to get_scorers().

    Returns:
        EvaluationResult with metrics and per-row assessments.
    """
    import pandas as pd

    mlflow.set_experiment(EXPERIMENT_NAME)

    if scorers is None:
        scorers = get_scorers()

    df = pd.DataFrame(eval_data)

    result = mlflow.genai.evaluate(
        data=df,
        predict_fn=predict_fn,
        scorers=scorers,
    )

    return result


# ---------------------------------------------------------------------------
# Labeling
# ---------------------------------------------------------------------------

def create_review_schemas() -> list[str]:
    """Create label schemas for human review.

    Creates two schemas:
    1. winner — who produced the better response (Champion/Custom/Neither)
    2. rationale — free-text explanation for MemAlign alignment

    Returns:
        List of schema names.
    """
    from mlflow.genai.label_schemas import (
        InputCategorical,
        InputText,
        create_label_schema,
    )

    schemas = []

    try:
        schema = create_label_schema(
            name="risk_winner",
            type="feedback",
            title="Which response is better?",
            input=InputCategorical(options=["Champion", "Custom", "Neither"]),
            enable_comment=True,
            overwrite=True,
        )
        schemas.append(schema.name)
        logger.info("Created label schema: risk_winner")
    except Exception as e:
        logger.warning("Could not create risk_winner schema: %s", e)
        schemas.append("risk_winner")

    try:
        schema = create_label_schema(
            name="risk_rationale",
            type="feedback",
            title="Why did you choose this winner?",
            input=InputText(),
            overwrite=True,
        )
        schemas.append(schema.name)
        logger.info("Created label schema: risk_rationale")
    except Exception as e:
        logger.warning("Could not create risk_rationale schema: %s", e)
        schemas.append("risk_rationale")

    return schemas


def create_ab_labeling_session(
    name: str,
    traces: list | None = None,
    assigned_users: list[str] | None = None,
) -> Any:
    """Create a labeling session for A/B testing.

    Domain experts review traces and label them with winner + rationale.
    Results are stored in MLflow and visible in the Evaluation > Labeling Sessions tab.

    Args:
        name: Session name (e.g., "ab-test-v1-alpha-growth")
        traces: List of trace objects to review.
        assigned_users: List of user emails to assign.

    Returns:
        LabelingSession object with .url for the review UI.
    """
    schemas = create_review_schemas()

    session = mlflow.genai.create_labeling_session(
        name=name,
        assigned_users=assigned_users or [],
        label_schemas=schemas,
    )

    if traces:
        session.add_traces(traces)

    logger.info("Created labeling session: %s (url: %s)", name, session.url)
    return session


# ---------------------------------------------------------------------------
# Automated Gate
# ---------------------------------------------------------------------------

def run_automated_gate(
    candidate_traces: Any,
    champion_traces: Any,
    scorers: list | None = None,
) -> dict:
    """Run the Automated Gate: evaluate candidate vs champion.

    Compares evaluation scores between candidate and champion traces.
    The candidate passes if it scores higher on average across all scorers.

    Args:
        candidate_traces: DataFrame of candidate traces.
        champion_traces: DataFrame of champion traces.
        scorers: List of scorers. Defaults to get_scorers().

    Returns:
        Dict with keys: passed, candidate_scores, champion_scores, details.
    """
    if scorers is None:
        scorers = get_scorers()

    candidate_result = mlflow.genai.evaluate(data=candidate_traces, scorers=scorers)
    champion_result = mlflow.genai.evaluate(data=champion_traces, scorers=scorers)

    candidate_avg = sum(candidate_result.metrics.values()) / max(len(candidate_result.metrics), 1)
    champion_avg = sum(champion_result.metrics.values()) / max(len(champion_result.metrics), 1)

    return {
        "passed": candidate_avg > champion_avg,
        "candidate_scores": candidate_result.metrics,
        "champion_scores": champion_result.metrics,
        "candidate_avg": candidate_avg,
        "champion_avg": champion_avg,
    }
