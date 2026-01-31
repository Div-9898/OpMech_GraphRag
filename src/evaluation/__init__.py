"""Evaluation framework for expert performance."""

from src.evaluation.gold_standard import (
    GoldEdge,
    GoldStandard,
    convert_template_to_gold,
    create_annotation_template,
    load_gold_standard,
    save_gold_standard,
    sample_candidate_pairs,
)
from src.evaluation.metrics import (
    EvaluationReport,
    ExpertEvaluation,
    calculate_calibration_error,
    evaluate_at_thresholds,
    evaluate_expert,
    generate_evaluation_report,
    print_evaluation_report,
)

__all__ = [
    # Gold standard
    "GoldEdge",
    "GoldStandard",
    "load_gold_standard",
    "save_gold_standard",
    "sample_candidate_pairs",
    "create_annotation_template",
    "convert_template_to_gold",
    # Metrics
    "ExpertEvaluation",
    "EvaluationReport",
    "evaluate_expert",
    "evaluate_at_thresholds",
    "calculate_calibration_error",
    "generate_evaluation_report",
    "print_evaluation_report",
]
