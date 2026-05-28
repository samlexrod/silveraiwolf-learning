"""DSPy optimization module for the financial risk agent.

Uses BootstrapFewShot and MIPROv2 to optimize prompt templates, then
compares all variants on the evaluation set.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import dspy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DSPy Signature and Module
# ---------------------------------------------------------------------------


class RiskAnswerer(dspy.Signature):
    """Answer financial risk questions using tool results from Gold tables.

    Given a user question and the JSON results from querying financial data tools,
    produce a clear, data-backed answer citing specific numbers and risk tiers.
    """

    question: str = dspy.InputField(desc="The user's financial risk question")
    tool_results: str = dspy.InputField(desc="JSON results from UC function tool calls")
    answer: str = dspy.OutputField(desc="A clear, data-backed answer citing specific numbers")


class RiskAgent(dspy.Module):
    """DSPy module wrapping chain-of-thought reasoning over tool results."""

    def __init__(self) -> None:
        super().__init__()
        self.chain = dspy.ChainOfThought(RiskAnswerer)

    def forward(self, question: str, tool_results: str) -> dspy.Prediction:
        """Run chain-of-thought reasoning to produce an answer."""
        return self.chain(question=question, tool_results=tool_results)


# ---------------------------------------------------------------------------
# Metric
# ---------------------------------------------------------------------------


def _answer_quality_metric(example: dspy.Example, prediction: dspy.Prediction, trace: Any = None) -> float:
    """Score answer quality: checks for data citation and relevance.

    Returns a float between 0 and 1.
    """
    answer = prediction.answer.lower()
    expected = example.expected_answer.lower() if hasattr(example, "expected_answer") else ""

    score = 0.0

    # Check if answer contains key terms from expected answer
    if expected:
        expected_terms = set(expected.split())
        answer_terms = set(answer.split())
        overlap = len(expected_terms & answer_terms) / max(len(expected_terms), 1)
        score += overlap * 0.5

    # Check if answer cites specific numbers (contains digits)
    if any(char.isdigit() for char in answer):
        score += 0.3

    # Check if answer is not a refusal
    refusal_phrases = ["i don't know", "i cannot", "no data", "not available"]
    if not any(phrase in answer for phrase in refusal_phrases):
        score += 0.2

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Optimization functions
# ---------------------------------------------------------------------------


def load_training_set(eval_path: str | Path | None = None) -> list[dspy.Example]:
    """Load evaluation set and convert to DSPy examples.

    Args:
        eval_path: Path to evaluation_set.json. Defaults to data/eval/evaluation_set.json.

    Returns:
        List of dspy.Example objects.
    """
    if eval_path is None:
        eval_path = Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "evaluation_set.json"

    with open(eval_path) as f:
        raw = json.load(f)

    examples = []
    for item in raw:
        examples.append(
            dspy.Example(
                question=item["request"],
                tool_results=json.dumps(item.get("context", {})),
                expected_answer=item.get("expected_response", ""),
            ).with_inputs("question", "tool_results")
        )
    return examples


def optimize_prompts(
    train_set: list[dspy.Example] | None = None,
) -> dict[str, dspy.Module]:
    """Run BootstrapFewShot and MIPROv2 optimizers.

    Args:
        train_set: Training examples. Loaded from default path if None.

    Returns:
        Dict mapping variant name to optimized module.
    """
    if train_set is None:
        train_set = load_training_set()

    base_module = RiskAgent()
    variants: dict[str, dspy.Module] = {"baseline": base_module}

    # --- BootstrapFewShot ---
    logger.info("Running BootstrapFewShot optimization...")
    bootstrap_optimizer = dspy.BootstrapFewShot(
        metric=_answer_quality_metric,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    variants["bootstrap"] = bootstrap_optimizer.compile(base_module, trainset=train_set)

    # --- MIPROv2 ---
    logger.info("Running MIPROv2 optimization...")
    try:
        mipro_optimizer = dspy.MIPROv2(
            metric=_answer_quality_metric,
            num_candidates=3,
            init_temperature=0.7,
        )
        variants["mipro"] = mipro_optimizer.compile(base_module, trainset=train_set)
    except Exception as e:
        logger.warning("MIPROv2 optimization failed (may require OpenAI key): %s", e)

    return variants


def compare_variants(variants: dict[str, dspy.Module], test_set: list[dspy.Example] | None = None) -> dict[str, float]:
    """Evaluate all variants on the test set and return scores.

    Args:
        variants: Dict of variant name -> optimized module.
        test_set: Test examples. Loaded from default path if None.

    Returns:
        Dict mapping variant name to average score.
    """
    if test_set is None:
        test_set = load_training_set()

    scores: dict[str, float] = {}

    for name, module in variants.items():
        total = 0.0
        for example in test_set:
            prediction = module(question=example.question, tool_results=example.tool_results)
            total += _answer_quality_metric(example, prediction)
        scores[name] = total / max(len(test_set), 1)
        logger.info("Variant '%s': avg score = %.3f", name, scores[name])

    return scores


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    variants = optimize_prompts()
    results = compare_variants(variants)
    print("\n--- Variant Comparison ---")
    for name, score in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  {name}: {score:.3f}")
