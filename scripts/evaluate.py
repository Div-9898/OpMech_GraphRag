#!/usr/bin/env python3
"""
Evaluate expert performance against gold standard annotations.

Usage:
    python scripts/evaluate.py --expert CrossReferenceHunter
    python scripts/evaluate.py --all
    python scripts/evaluate.py --create-template --expert CrossReferenceHunter
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.config import settings
from src.evaluation import (
    EvaluationReport,
    GoldStandard,
    create_annotation_template,
    evaluate_expert,
    generate_evaluation_report,
    load_gold_standard,
    print_evaluation_report,
)
from src.graph.neo4j_client import Neo4jClient
from src.models import Edge, EdgeType, Node


def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )


def load_predictions_from_neo4j(expert_name: str) -> list[Edge]:
    """Load expert predictions from Neo4j."""
    logger.info(f"Loading predictions for {expert_name} from Neo4j...")

    client = Neo4jClient(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )

    try:
        with client.driver.session() as session:
            result = session.run(
                """
                MATCH (s:Node)-[r]->(t:Node)
                WHERE r.expert = $expert
                RETURN r.id as id, s.id as source_id, t.id as target_id,
                       r.edge_type as edge_type, r.confidence as confidence,
                       r.expert as expert, r.evidence as evidence
                """,
                expert=expert_name,
            )

            edges = []
            for record in result:
                edges.append(Edge(
                    id=record["id"] or f"{record['source_id']}->{record['target_id']}",
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    edge_type=EdgeType(record["edge_type"]),
                    confidence=record["confidence"] or 0.5,
                    expert=record["expert"],
                    evidence=record["evidence"],
                ))

            logger.info(f"Loaded {len(edges)} edges from {expert_name}")
            return edges

    finally:
        client.close()


def load_predictions_from_file(expert_name: str) -> list[Edge]:
    """Load expert predictions from a JSON file."""
    pred_path = settings.data_dir / "predictions" / f"{expert_name}.jsonl"

    if not pred_path.exists():
        logger.warning(f"No prediction file found: {pred_path}")
        return []

    edges = []
    with open(pred_path, "r") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                edges.append(Edge(**data))

    logger.info(f"Loaded {len(edges)} edges from {pred_path}")
    return edges


def evaluate_single_expert(expert_name: str, source: str = "neo4j") -> None:
    """Evaluate a single expert."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Evaluating {expert_name}")
    logger.info("=" * 60)

    # Load gold standard
    gold = load_gold_standard(expert_name)
    if gold is None:
        logger.error(f"No gold standard found for {expert_name}")
        logger.info(f"Create one with: python scripts/evaluate.py --create-template --expert {expert_name}")
        return

    logger.info(f"Gold standard: {len(gold.annotations)} annotations")

    # Load predictions
    if source == "neo4j":
        predictions = load_predictions_from_neo4j(expert_name)
    else:
        predictions = load_predictions_from_file(expert_name)

    if not predictions:
        logger.warning("No predictions found")
        return

    # Evaluate
    result = evaluate_expert(predictions, gold)

    # Print results
    logger.info(f"\nResults for {expert_name}:")
    logger.info("-" * 40)
    logger.info(f"  Precision: {result.metrics.precision:.3f}")
    logger.info(f"  Recall:    {result.metrics.recall:.3f}")
    logger.info(f"  F1 Score:  {result.metrics.f1:.3f}")
    logger.info(f"\n  Confusion Matrix:")
    logger.info(f"    True Positives:  {result.confusion_matrix.get('true_positives', 0)}")
    logger.info(f"    False Positives: {result.confusion_matrix.get('false_positives', 0)}")
    logger.info(f"    False Negatives: {result.confusion_matrix.get('false_negatives', 0)}")
    logger.info(f"    True Negatives:  {result.confusion_matrix.get('true_negatives', 0)}")

    if result.calibration_error is not None:
        logger.info(f"\n  Calibration Error: {result.calibration_error:.3f}")

    # Check against TRD thresholds
    thresholds = {
        "CrossReferenceHunter": {"min": 0.82, "target": 0.88},
        "CausalChainBuilder": {"min": 0.72, "target": 0.78},
        "TemporalLinker": {"min": 0.87, "target": 0.92},
        "TableTextConnector": {"min": 0.80, "target": 0.85},
        "SemanticBridge": {"min": 0.70, "target": 0.75},
    }

    if expert_name in thresholds:
        thresh = thresholds[expert_name]
        status = "PASS" if result.metrics.f1 >= thresh["min"] else "FAIL"
        target_met = result.metrics.f1 >= thresh["target"]
        logger.info(f"\n  TRD Threshold Check:")
        logger.info(f"    Minimum F1: {thresh['min']} - {status}")
        logger.info(f"    Target F1:  {thresh['target']} - {'MET' if target_met else 'NOT MET'}")


def evaluate_all_experts(source: str = "neo4j") -> None:
    """Evaluate all experts."""
    experts = [
        "CrossReferenceHunter",
        "CausalChainBuilder",
        "TemporalLinker",
        "TableTextConnector",
        "SemanticBridge",
    ]

    expert_edges = {}
    for expert in experts:
        if source == "neo4j":
            edges = load_predictions_from_neo4j(expert)
        else:
            edges = load_predictions_from_file(expert)

        if edges:
            expert_edges[expert] = edges

    if not expert_edges:
        logger.error("No predictions found for any expert")
        return

    report = generate_evaluation_report(expert_edges)
    print_evaluation_report(report)

    # Save report
    report_path = settings.data_dir / "evaluation_report.json"
    with open(report_path, "w") as f:
        f.write(report.model_dump_json(indent=2))
    logger.info(f"\nReport saved to: {report_path}")


def create_gold_template(expert_name: str) -> None:
    """Create annotation template for an expert."""
    logger.info(f"Creating annotation template for {expert_name}...")

    # Map expert to edge type
    expert_edge_types = {
        "CrossReferenceHunter": EdgeType.REFERS_TO,
        "CausalChainBuilder": EdgeType.CAUSED_BY,
        "TemporalLinker": EdgeType.TEMPORAL_NEXT,
        "TableTextConnector": EdgeType.EXPLAINS,
        "SemanticBridge": EdgeType.SIMILAR_TO,
    }

    edge_type = expert_edge_types.get(expert_name, EdgeType.EXPLAINS)

    # Load nodes from Neo4j
    client = Neo4jClient(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )

    try:
        with client.driver.session() as session:
            result = session.run(
                """
                MATCH (n:Node)
                RETURN n.id as id, n.type as type, n.text as text,
                       n.filing_id as filing_id, n.period as period
                LIMIT 1000
                """
            )

            nodes = []
            for record in result:
                from src.models import NodeMetadata, NodeType
                nodes.append(Node(
                    id=record["id"],
                    type=NodeType(record["type"]),
                    text=record["text"] or "",
                    metadata=NodeMetadata(
                        filing_id=record["filing_id"] or "unknown",
                        period=record["period"] or "unknown",
                    ),
                ))

        if not nodes:
            logger.error("No nodes found in database. Run build_graph.py first.")
            return

        template_path = create_annotation_template(
            nodes=nodes,
            expert_name=expert_name,
            edge_type=edge_type,
            n_samples=100,
        )

        logger.info(f"\nTemplate created: {template_path}")
        logger.info("\nNext steps:")
        logger.info("1. Open the template file and fill in the 'label' field (true/false)")
        logger.info("2. Add your name to the 'annotator' field")
        logger.info("3. Optionally add confidence (1-5) and notes")
        logger.info("4. Save as annotations.jsonl in the same directory")

    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Evaluate expert performance")
    parser.add_argument(
        "--expert",
        choices=[
            "CrossReferenceHunter",
            "CausalChainBuilder",
            "TemporalLinker",
            "TableTextConnector",
            "SemanticBridge",
        ],
        help="Expert to evaluate",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all experts",
    )
    parser.add_argument(
        "--source",
        choices=["neo4j", "file"],
        default="neo4j",
        help="Source of predictions (default: neo4j)",
    )
    parser.add_argument(
        "--create-template",
        action="store_true",
        help="Create annotation template instead of evaluating",
    )

    args = parser.parse_args()

    setup_logging()
    settings.ensure_dirs()

    if args.create_template:
        if not args.expert:
            parser.error("--create-template requires --expert")
        create_gold_template(args.expert)
    elif args.all:
        evaluate_all_experts(args.source)
    elif args.expert:
        evaluate_single_expert(args.expert, args.source)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
