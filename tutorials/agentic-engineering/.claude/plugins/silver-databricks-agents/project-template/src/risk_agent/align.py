"""MemAlign judge alignment module.

Creates LLM judges using mlflow.genai.judges.make_judge(), aligns them to
human preferences using MemAlignOptimizer with Databricks-hosted models,
and compares before/after alignment scores.

Usage:
    python -m risk_agent.align
"""

from __future__ import annotations

import logging
import time
from typing import Any

import mlflow
from mlflow.entities.assessment import AssessmentSource
from mlflow.genai.judges import make_judge
from mlflow.genai.judges.optimizers import MemAlignOptimizer

logger = logging.getLogger(__name__)

# Databricks-hosted models — no external API keys needed
# Format: "databricks:<endpoint-name>" (colon, no slash)
JUDGE_MODEL = "databricks:/databricks-meta-llama-3-3-70b-instruct"
EMBEDDING_MODEL = "databricks:/databricks-gte-large-en"


# ---------------------------------------------------------------------------
# Judge definitions
# ---------------------------------------------------------------------------


def create_judges() -> dict[str, Any]:
    """Create three domain-specific LLM judges.

    Returns:
        Dict mapping judge name to the Judge object.
    """
    judges = {
        "risk_correctness": make_judge(
            name="risk_correctness",
            instructions="""Evaluate if the agent's response correctly answers
            the financial risk question using data from the Gold tables.

            Question: {{ inputs }}
            Response: {{ outputs }}
            Expected: {{ expectations }}

            Return True if the response is factually correct, False otherwise.""",
            feedback_value_type=bool,
            model=JUDGE_MODEL,
        ),
        "risk_groundedness": make_judge(
            name="risk_groundedness",
            instructions="""Evaluate if the agent's response is grounded in
            tool results (data from Gold tables) rather than hallucinated.

            Question: {{ inputs }}
            Response: {{ outputs }}

            Return True if the response cites specific data from tools, False
            if it makes claims not supported by tool results.""",
            feedback_value_type=bool,
            model=JUDGE_MODEL,
        ),
        "risk_relevance": make_judge(
            name="risk_relevance",
            instructions="""Evaluate if the agent's response appropriately
            addresses the financial risk question. Does it provide actionable
            risk information? Does it stay within data rather than giving advice?

            Question: {{ inputs }}
            Response: {{ outputs }}

            Return True if the response is relevant and appropriate, False otherwise.""",
            feedback_value_type=bool,
            model=JUDGE_MODEL,
        ),
    }
    logger.info("Created %d judges with model %s", len(judges), JUDGE_MODEL)
    return judges


# ---------------------------------------------------------------------------
# Alignment trace creation
# ---------------------------------------------------------------------------


def create_alignment_traces(
    agent: Any,
    feedback_data: list[dict[str, Any]],
    judge_name: str,
    experiment_name: str = "/Shared/risk-agent",
    wait_seconds: int = 10,
) -> list[Any]:
    """Generate traces with human feedback for MemAlign alignment.

    Args:
        agent: The FinancialRiskAgent instance.
        feedback_data: List of dicts with keys: question, feedback (bool), rationale (str).
        judge_name: Assessment name — MUST match the judge name for MemAlign to find it.
        experiment_name: MLflow experiment for trace storage.
        wait_seconds: Seconds to wait for async trace export before logging feedback.

    Returns:
        List of Trace objects with assessments attached.
    """
    mlflow.set_experiment(experiment_name)

    # Step 1: Run queries to generate traces
    trace_ids = []
    for item in feedback_data:
        with mlflow.start_span(name="agent_query") as span:
            span.set_inputs({"question": item["question"]})
            try:
                result = agent.predict(
                    model_input={"messages": [{"role": "user", "content": item["question"]}]}
                )
                span.set_outputs({"response": result.get("content", "")})
            except Exception as e:
                span.set_outputs({"error": str(e)})
        trace_ids.append(mlflow.get_last_active_trace_id())

    # Step 2: Wait for async trace export to Databricks
    logger.info("Waiting %ds for trace export...", wait_seconds)
    time.sleep(wait_seconds)

    # Step 3: Log human feedback as assessments (name must match judge name)
    for trace_id, item in zip(trace_ids, feedback_data):
        mlflow.log_feedback(
            trace_id=trace_id,
            name=judge_name,
            value=item["feedback"],
            rationale=item["rationale"],
            source=AssessmentSource(source_type="HUMAN", source_id="domain_expert"),
        )
        logger.info("Logged feedback for trace %s: %s", trace_id[:16], item["feedback"])

    # Step 4: Retrieve Trace objects
    client = mlflow.MlflowClient()
    return [client.get_trace(tid) for tid in trace_ids]


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------


def align_judge(
    judge: Any,
    traces: list[Any],
    retrieval_k: int = 3,
) -> Any:
    """Align a judge to human preferences using MemAlignOptimizer.

    Args:
        judge: The Judge object to align.
        traces: List of Trace objects with human assessments matching judge.name.
        retrieval_k: Number of similar examples to retrieve from episodic memory.

    Returns:
        Aligned Judge (MemoryAugmentedJudge).
    """
    optimizer = MemAlignOptimizer(
        reflection_lm=JUDGE_MODEL,
        embedding_model=EMBEDDING_MODEL,
        retrieval_k=retrieval_k,
    )

    aligned = optimizer.align(judge, traces)
    logger.info("Judge '%s' aligned successfully", judge.name)
    return aligned


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def compare_judges(
    original: Any,
    aligned: Any,
    eval_data: list[dict[str, Any]],
) -> dict[str, float]:
    """Compare original vs aligned judge scores.

    Args:
        original: Unaligned judge.
        aligned: Aligned judge.
        eval_data: List of dicts with keys: question, response.

    Returns:
        Dict with original_pct and aligned_pct.
    """
    orig_correct = 0
    aligned_correct = 0

    for item in eval_data:
        q = item["question"]
        r = item["response"]

        orig_fb = original.run(inputs=q, outputs=r)
        aligned_fb = aligned.run(inputs=q, outputs=r)

        if orig_fb and orig_fb.value:
            orig_correct += 1
        if aligned_fb and aligned_fb.value:
            aligned_correct += 1

    n = max(len(eval_data), 1)
    return {
        "original_pct": orig_correct / n * 100,
        "aligned_pct": aligned_correct / n * 100,
    }
