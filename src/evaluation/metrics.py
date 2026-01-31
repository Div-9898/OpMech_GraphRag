"""Evaluation metrics for expert performance."""

import json
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from src.evaluation.gold_standard import GoldEdge, GoldStandard, load_gold_standard
from src.models import Edge, EdgeType, Metrics


class ExpertEvaluation(BaseModel):
    """Evaluation results for a single expert."""

    expert_name: str
    edge_type: EdgeType
    metrics: Metrics
    threshold_analysis: dict[str, Metrics] | None = None
    confusion_matrix: dict[str, int] = Field(default_factory=dict)
    calibration_error: float | None = None


class EvaluationReport(BaseModel):
    """Full evaluation report for all experts."""

    expert_results: list[ExpertEvaluation]
    summary: dict[str, Any] = Field(default_factory=dict)


def evaluate_expert(
    predictions: list[Edge],
    gold: GoldStandard,
    confidence_threshold: float = 0.5,
) -> ExpertEvaluation:
    """
    Evaluate expert predictions against gold standard.

    Args:
        predictions: Predicted edges from expert
        gold: Gold standard annotations
        confidence_threshold: Minimum confidence to count as positive prediction

    Returns:
        ExpertEvaluation with metrics
    """
    # Build prediction set (edges above threshold)
    pred_set = set()
    pred_confidences = {}

    for edge in predictions:
        if edge.confidence >= confidence_threshold:
            key = (edge.source_id, edge.target_id, edge.edge_type)
            pred_set.add(key)
            pred_confidences[key] = edge.confidence

    # Build gold sets (positive and negative)
    gold_positive = set()
    gold_negative = set()

    for ann in gold.annotations:
        key = (ann.source_id, ann.target_id, ann.edge_type)
        if ann.label:
            gold_positive.add(key)
        else:
            gold_negative.add(key)

    # Calculate confusion matrix
    tp = len(pred_set & gold_positive)
    fp = len(pred_set & gold_negative)  # Predicted positive but gold negative
    fn = len(gold_positive - pred_set)  # Gold positive but not predicted
    tn = len(gold_negative - pred_set)  # Gold negative and not predicted

    # Also count edges predicted but not in gold at all
    gold_all = gold_positive | gold_negative
    pred_not_in_gold = pred_set - gold_all

    # Calculate metrics
    metrics = Metrics.calculate(tp, fp, fn)

    # Calculate calibration error
    calibration_error = calculate_calibration_error(predictions, gold)

    return ExpertEvaluation(
        expert_name=gold.expert_name,
        edge_type=gold.edge_type,
        metrics=metrics,
        confusion_matrix={
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "predictions_not_in_gold": len(pred_not_in_gold),
        },
        calibration_error=calibration_error,
    )


def evaluate_at_thresholds(
    predictions: list[Edge],
    gold: GoldStandard,
    thresholds: list[float] = None,
) -> dict[str, Metrics]:
    """Evaluate at multiple confidence thresholds."""
    if thresholds is None:
        thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    results = {}
    for threshold in thresholds:
        eval_result = evaluate_expert(predictions, gold, threshold)
        results[f"threshold_{threshold}"] = eval_result.metrics

    return results


def calculate_calibration_error(
    predictions: list[Edge],
    gold: GoldStandard,
    n_bins: int = 10,
) -> float:
    """
    Calculate Expected Calibration Error (ECE).

    A well-calibrated model should have predictions with confidence X
    being correct ~X% of the time.
    """
    # Build gold label lookup
    gold_labels = {}
    for ann in gold.annotations:
        key = (ann.source_id, ann.target_id, ann.edge_type)
        gold_labels[key] = ann.label

    # Group predictions by confidence bin
    bins = [[] for _ in range(n_bins)]

    for edge in predictions:
        key = (edge.source_id, edge.target_id, edge.edge_type)
        if key in gold_labels:
            bin_idx = min(int(edge.confidence * n_bins), n_bins - 1)
            is_correct = gold_labels[key]
            bins[bin_idx].append((edge.confidence, is_correct))

    # Calculate ECE
    total_samples = sum(len(b) for b in bins)
    if total_samples == 0:
        return 0.0

    ece = 0.0
    for i, bin_data in enumerate(bins):
        if not bin_data:
            continue

        avg_confidence = sum(c for c, _ in bin_data) / len(bin_data)
        accuracy = sum(1 for _, correct in bin_data if correct) / len(bin_data)
        weight = len(bin_data) / total_samples
        ece += weight * abs(accuracy - avg_confidence)

    return ece


def generate_evaluation_report(
    expert_edges: dict[str, list[Edge]],
    gold_dir: Path = None,
) -> EvaluationReport:
    """
    Generate evaluation report for all experts.

    Args:
        expert_edges: Dict mapping expert_name -> list of predicted edges
        gold_dir: Directory containing gold standard files

    Returns:
        EvaluationReport
    """
    gold_dir = gold_dir or settings.gold_dir

    results = []
    for expert_name, predictions in expert_edges.items():
        gold = load_gold_standard(expert_name)
        if gold is None:
            logger.warning(f"Skipping {expert_name}: no gold standard")
            continue

        eval_result = evaluate_expert(predictions, gold)
        eval_result.threshold_analysis = evaluate_at_thresholds(predictions, gold)
        results.append(eval_result)

    # Calculate summary
    summary = {
        "total_experts_evaluated": len(results),
        "experts_meeting_threshold": 0,
        "average_f1": 0.0,
        "average_precision": 0.0,
        "average_recall": 0.0,
    }

    if results:
        summary["average_f1"] = sum(r.metrics.f1 for r in results) / len(results)
        summary["average_precision"] = sum(r.metrics.precision for r in results) / len(results)
        summary["average_recall"] = sum(r.metrics.recall for r in results) / len(results)

        # Count experts meeting their F1 thresholds
        thresholds = {
            "CrossReferenceHunter": 0.82,
            "CausalChainBuilder": 0.72,
            "TemporalLinker": 0.87,
            "TableTextConnector": 0.80,
            "SemanticBridge": 0.70,
        }

        for result in results:
            threshold = thresholds.get(result.expert_name, 0.70)
            if result.metrics.f1 >= threshold:
                summary["experts_meeting_threshold"] += 1

    return EvaluationReport(
        expert_results=results,
        summary=summary,
    )


def print_evaluation_report(report: EvaluationReport) -> None:
    """Print a formatted evaluation report."""
    logger.info("\n" + "=" * 70)
    logger.info("EXPERT EVALUATION REPORT")
    logger.info("=" * 70)

    # Expert thresholds from TRD
    thresholds = {
        "CrossReferenceHunter": {"min": 0.82, "target": 0.88},
        "CausalChainBuilder": {"min": 0.72, "target": 0.78},
        "TemporalLinker": {"min": 0.87, "target": 0.92},
        "TableTextConnector": {"min": 0.80, "target": 0.85},
        "SemanticBridge": {"min": 0.70, "target": 0.75},
    }

    for result in report.expert_results:
        logger.info(f"\n{result.expert_name}")
        logger.info("-" * 40)

        m = result.metrics
        logger.info(f"  Precision: {m.precision:.3f}")
        logger.info(f"  Recall:    {m.recall:.3f}")
        logger.info(f"  F1 Score:  {m.f1:.3f}")

        # Check against thresholds
        if result.expert_name in thresholds:
            thresh = thresholds[result.expert_name]
            status = "PASS" if m.f1 >= thresh["min"] else "FAIL"
            target_status = "TARGET MET" if m.f1 >= thresh["target"] else ""
            logger.info(f"  Status:    {status} (min: {thresh['min']}) {target_status}")

        logger.info(f"  Confusion Matrix: TP={result.confusion_matrix.get('true_positives', 0)}, "
                   f"FP={result.confusion_matrix.get('false_positives', 0)}, "
                   f"FN={result.confusion_matrix.get('false_negatives', 0)}")

        if result.calibration_error is not None:
            logger.info(f"  Calibration Error: {result.calibration_error:.3f}")

    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Experts Evaluated: {report.summary['total_experts_evaluated']}")
    logger.info(f"  Meeting Threshold: {report.summary['experts_meeting_threshold']}")
    logger.info(f"  Average F1:        {report.summary['average_f1']:.3f}")
    logger.info(f"  Average Precision: {report.summary['average_precision']:.3f}")
    logger.info(f"  Average Recall:    {report.summary['average_recall']:.3f}")
    logger.info("=" * 70)


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Create sample data for testing
    from src.config import settings
    from src.evaluation.gold_standard import GoldEdge, GoldStandard, save_gold_standard

    settings.ensure_dirs()

    # Create sample gold standard
    sample_gold = GoldStandard(
        expert_name="CrossReferenceHunter",
        edge_type=EdgeType.REFERS_TO,
        annotations=[
            GoldEdge(source_id="A", target_id="B", edge_type=EdgeType.REFERS_TO, label=True),
            GoldEdge(source_id="A", target_id="C", edge_type=EdgeType.REFERS_TO, label=True),
            GoldEdge(source_id="B", target_id="C", edge_type=EdgeType.REFERS_TO, label=False),
            GoldEdge(source_id="A", target_id="D", edge_type=EdgeType.REFERS_TO, label=False),
        ],
    )
    save_gold_standard(sample_gold)

    # Create sample predictions
    sample_predictions = [
        Edge(id="1", source_id="A", target_id="B", edge_type=EdgeType.REFERS_TO,
             confidence=0.9, expert="CrossReferenceHunter", evidence="test"),
        Edge(id="2", source_id="A", target_id="C", edge_type=EdgeType.REFERS_TO,
             confidence=0.7, expert="CrossReferenceHunter", evidence="test"),
        Edge(id="3", source_id="B", target_id="C", edge_type=EdgeType.REFERS_TO,
             confidence=0.6, expert="CrossReferenceHunter", evidence="test"),  # FP
        Edge(id="4", source_id="X", target_id="Y", edge_type=EdgeType.REFERS_TO,
             confidence=0.8, expert="CrossReferenceHunter", evidence="test"),  # Not in gold
    ]

    # Evaluate
    eval_result = evaluate_expert(sample_predictions, sample_gold, confidence_threshold=0.5)
    logger.info(f"Metrics: {eval_result.metrics}")
    logger.info(f"Confusion: {eval_result.confusion_matrix}")
