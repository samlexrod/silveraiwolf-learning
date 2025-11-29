"""
Production Model Registration Criteria
Defines validation gates for promoting models to production registry
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import mlflow


@dataclass
class ProductionCriteria:
    """Criteria thresholds for production model registration"""

    # Performance thresholds
    min_accuracy: float = 0.90  # 90% minimum accuracy
    min_f1_score: float = 0.85  # 85% minimum F1
    min_precision: float = 0.80  # 80% minimum precision
    min_recall: float = 0.80  # 80% minimum recall

    # Improvement thresholds (vs current champion)
    min_accuracy_improvement: float = 0.02  # 2% improvement required

    # Latency requirements (seconds)
    max_latency_p95: float = 3.0  # 95th percentile
    max_latency_p99: float = 5.0  # 99th percentile

    # Cost criteria
    max_cost_increase: float = 0.20  # 20% cost increase allowed if accuracy improves
    min_cost_savings: float = 0.30  # 30% cost savings for similar accuracy


def evaluate_performance_criteria(
    metrics: Dict[str, float],
    criteria: ProductionCriteria = None
) -> Tuple[bool, str]:
    """
    Evaluate if model meets minimum performance criteria

    Args:
        metrics: Dictionary of model metrics
        criteria: ProductionCriteria instance (uses defaults if None)

    Returns:
        Tuple of (passes: bool, reason: str)
    """
    if criteria is None:
        criteria = ProductionCriteria()

    reasons = []

    # Check accuracy
    accuracy = metrics.get('category_accuracy', 0.0)
    if accuracy < criteria.min_accuracy:
        reasons.append(f"Accuracy {accuracy:.2%} below {criteria.min_accuracy:.2%} threshold")

    # Check F1 score
    f1 = metrics.get('category_f1_weighted', 0.0)
    if f1 < criteria.min_f1_score:
        reasons.append(f"F1 score {f1:.3f} below {criteria.min_f1_score:.3f} threshold")

    # Check precision
    precision = metrics.get('category_precision_weighted', 0.0)
    if precision < criteria.min_precision:
        reasons.append(f"Precision {precision:.3f} below {criteria.min_precision:.3f} threshold")

    # Check recall
    recall = metrics.get('category_recall_weighted', 0.0)
    if recall < criteria.min_recall:
        reasons.append(f"Recall {recall:.3f} below {criteria.min_recall:.3f} threshold")

    if reasons:
        return False, "; ".join(reasons)

    return True, "All performance criteria met"


def evaluate_champion_criteria(
    new_accuracy: float,
    current_accuracy: float,
    criteria: ProductionCriteria = None
) -> Tuple[bool, str]:
    """
    Evaluate if new model beats current champion

    Args:
        new_accuracy: New model's accuracy
        current_accuracy: Current production model's accuracy
        criteria: ProductionCriteria instance

    Returns:
        Tuple of (passes: bool, reason: str)
    """
    if criteria is None:
        criteria = ProductionCriteria()

    improvement = new_accuracy - current_accuracy

    if improvement < criteria.min_accuracy_improvement:
        return False, (
            f"Accuracy improvement {improvement:.2%} below "
            f"{criteria.min_accuracy_improvement:.2%} threshold "
            f"(current: {current_accuracy:.2%}, new: {new_accuracy:.2%})"
        )

    return True, f"Beats champion by {improvement:.2%}"


def evaluate_cost_performance_tradeoff(
    accuracy_diff: float,
    cost_diff: float,
    criteria: ProductionCriteria = None
) -> Tuple[bool, str]:
    """
    Evaluate cost vs performance trade-off

    Args:
        accuracy_diff: Difference in accuracy (new - current)
        cost_diff: Difference in cost (new - current) / current
        criteria: ProductionCriteria instance

    Returns:
        Tuple of (passes: bool, reason: str)
    """
    if criteria is None:
        criteria = ProductionCriteria()

    # Similar accuracy with significant cost savings
    if abs(accuracy_diff) < 0.05 and cost_diff < -criteria.min_cost_savings:
        return True, f"Similar accuracy ({accuracy_diff:+.2%}) with {abs(cost_diff):.0%} cost savings"

    # Better accuracy with acceptable cost increase
    if accuracy_diff > 0.05 and cost_diff < criteria.max_cost_increase:
        return True, f"Better accuracy ({accuracy_diff:+.2%}) with acceptable cost increase ({cost_diff:+.0%})"

    # Better accuracy and lower cost (ideal)
    if accuracy_diff > 0 and cost_diff < 0:
        return True, f"Better accuracy ({accuracy_diff:+.2%}) AND lower cost ({cost_diff:+.0%})"

    return False, (
        f"Poor cost/performance trade-off: "
        f"accuracy {accuracy_diff:+.2%}, cost {cost_diff:+.0%}"
    )


def get_registration_tags(
    metrics: Dict[str, float],
    track: str,
    provider: str,
    model: str,
    passes_criteria: bool,
    reason: str
) -> Dict[str, str]:
    """
    Generate tags for Unity Catalog model registration

    Args:
        metrics: Model metrics
        track: Track identifier (A or B)
        provider: Model provider
        model: Model name
        passes_criteria: Whether model passes production criteria
        reason: Reason for pass/fail

    Returns:
        Dictionary of tags
    """
    tags = {
        "track": track,
        "provider": provider,
        "model": model,
        "category_accuracy": str(round(metrics.get('category_accuracy', 0.0), 4)),
        "category_f1": str(round(metrics.get('category_f1_weighted', 0.0), 4)),
        "sentiment_accuracy": str(round(metrics.get('sentiment_accuracy', 0.0), 4)),
        "production_ready": str(passes_criteria).lower(),
        "validation_reason": reason[:250],  # Limit length
    }

    return tags


def get_champion_metrics(
    catalog: str,
    schema: str,
    model_name: str,
    alias: str = "Champion"
) -> Optional[Dict[str, float]]:
    """
    Get metrics from current champion model in Unity Catalog

    Args:
        catalog: Unity Catalog name
        schema: Schema name
        model_name: Model name
        alias: Alias to look up (default: Champion)

    Returns:
        Dictionary of metrics from champion model, or None if no champion exists
    """
    try:
        client = mlflow.MlflowClient()
        full_model_name = f"{catalog}.{schema}.{model_name}"

        # Try to get model version by alias
        try:
            model_version = client.get_model_version_by_alias(full_model_name, alias)
        except Exception:
            # No champion exists yet
            return None

        # Get run ID from model version
        run_id = model_version.run_id

        # Get metrics from the run
        run = client.get_run(run_id)
        metrics = run.data.metrics

        return {
            'category_accuracy': metrics.get('category_accuracy', 0.0),
            'category_f1_weighted': metrics.get('category_f1_weighted', 0.0),
            'category_precision_weighted': metrics.get('category_precision_weighted', 0.0),
            'category_recall_weighted': metrics.get('category_recall_weighted', 0.0),
        }

    except Exception as e:
        # Champion doesn't exist or other error
        return None


def format_criteria_summary(
    metrics: Dict[str, float],
    criteria: ProductionCriteria = None
) -> str:
    """
    Format a summary of how model performs against criteria

    Args:
        metrics: Model metrics
        criteria: ProductionCriteria instance

    Returns:
        Formatted string summary
    """
    if criteria is None:
        criteria = ProductionCriteria()

    lines = []
    lines.append("=" * 80)
    lines.append("PRODUCTION CRITERIA EVALUATION")
    lines.append("=" * 80)

    # Performance metrics
    accuracy = metrics.get('category_accuracy', 0.0)
    f1 = metrics.get('category_f1_weighted', 0.0)
    precision = metrics.get('category_precision_weighted', 0.0)
    recall = metrics.get('category_recall_weighted', 0.0)

    lines.append("\nPerformance Metrics:")
    lines.append(f"  Accuracy:  {accuracy:.2%} {'✅' if accuracy >= criteria.min_accuracy else '❌'} (threshold: {criteria.min_accuracy:.2%})")
    lines.append(f"  F1 Score:  {f1:.3f} {'✅' if f1 >= criteria.min_f1_score else '❌'} (threshold: {criteria.min_f1_score:.3f})")
    lines.append(f"  Precision: {precision:.3f} {'✅' if precision >= criteria.min_precision else '❌'} (threshold: {criteria.min_precision:.3f})")
    lines.append(f"  Recall:    {recall:.3f} {'✅' if recall >= criteria.min_recall else '❌'} (threshold: {criteria.min_recall:.3f})")

    # Overall evaluation
    passes, reason = evaluate_performance_criteria(metrics, criteria)
    lines.append("\n" + "=" * 80)
    if passes:
        lines.append("✅ PASSES PRODUCTION CRITERIA")
    else:
        lines.append("❌ FAILS PRODUCTION CRITERIA")
    lines.append(f"Reason: {reason}")
    lines.append("=" * 80)

    return "\n".join(lines)