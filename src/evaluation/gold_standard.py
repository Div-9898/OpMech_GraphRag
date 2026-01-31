"""Gold standard annotation management for expert evaluation."""

import json
import random
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from src.config import settings
from src.models import Edge, EdgeType, Node


class GoldEdge(BaseModel):
    """A gold standard edge annotation."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    label: bool = Field(..., description="True if edge should exist, False if not")
    annotator: str | None = None
    confidence: float | None = Field(default=None, description="Annotator confidence 1-5")
    notes: str | None = None


class GoldStandard(BaseModel):
    """Gold standard dataset for an expert."""

    expert_name: str
    edge_type: EdgeType
    annotations: list[GoldEdge]
    metadata: dict[str, Any] = Field(default_factory=dict)


def load_gold_standard(expert_name: str) -> GoldStandard | None:
    """Load gold standard annotations for an expert."""
    gold_path = settings.gold_dir / expert_name / "annotations.jsonl"

    if not gold_path.exists():
        logger.warning(f"No gold standard found for {expert_name}")
        return None

    annotations = []
    with open(gold_path, "r") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                annotations.append(GoldEdge(**data))

    # Determine edge type from annotations
    edge_types = set(a.edge_type for a in annotations)
    primary_edge_type = list(edge_types)[0] if edge_types else EdgeType.EXPLAINS

    return GoldStandard(
        expert_name=expert_name,
        edge_type=primary_edge_type,
        annotations=annotations,
    )


def save_gold_standard(gold: GoldStandard) -> Path:
    """Save gold standard annotations."""
    output_dir = settings.gold_dir / gold.expert_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "annotations.jsonl"
    with open(output_path, "w") as f:
        for annotation in gold.annotations:
            f.write(annotation.model_dump_json() + "\n")

    logger.info(f"Saved {len(gold.annotations)} annotations to {output_path}")
    return output_path


def sample_candidate_pairs(
    nodes: list[Node],
    edge_type: EdgeType,
    n_samples: int = 100,
    same_filing_ratio: float = 0.8,
) -> list[tuple[str, str]]:
    """
    Sample candidate node pairs for annotation.

    Args:
        nodes: List of nodes
        edge_type: Type of edge to sample for
        n_samples: Number of pairs to sample
        same_filing_ratio: Ratio of pairs from same filing

    Returns:
        List of (source_id, target_id) tuples
    """
    pairs = []

    # Group nodes by filing
    by_filing = {}
    for node in nodes:
        fid = node.metadata.filing_id
        if fid not in by_filing:
            by_filing[fid] = []
        by_filing[fid].append(node)

    filing_ids = list(by_filing.keys())

    # Sample within-filing pairs
    n_same = int(n_samples * same_filing_ratio)
    for _ in range(n_same):
        fid = random.choice(filing_ids)
        if len(by_filing[fid]) >= 2:
            n1, n2 = random.sample(by_filing[fid], 2)
            pairs.append((n1.id, n2.id))

    # Sample cross-filing pairs
    n_cross = n_samples - n_same
    for _ in range(n_cross):
        if len(filing_ids) >= 2:
            fid1, fid2 = random.sample(filing_ids, 2)
            if by_filing[fid1] and by_filing[fid2]:
                n1 = random.choice(by_filing[fid1])
                n2 = random.choice(by_filing[fid2])
                pairs.append((n1.id, n2.id))

    return pairs[:n_samples]


def create_annotation_template(
    nodes: list[Node],
    expert_name: str,
    edge_type: EdgeType,
    n_samples: int = 100,
) -> Path:
    """
    Create an annotation template file for manual labeling.

    Args:
        nodes: List of nodes
        expert_name: Name of expert
        edge_type: Type of edge
        n_samples: Number of pairs to annotate

    Returns:
        Path to the template file
    """
    # Sample candidate pairs
    pairs = sample_candidate_pairs(nodes, edge_type, n_samples)

    # Create node lookup
    node_map = {n.id: n for n in nodes}

    # Create template
    output_dir = settings.gold_dir / expert_name
    output_dir.mkdir(parents=True, exist_ok=True)

    template_path = output_dir / "template.jsonl"
    with open(template_path, "w") as f:
        for source_id, target_id in pairs:
            source = node_map.get(source_id)
            target = node_map.get(target_id)

            if not source or not target:
                continue

            entry = {
                "source_id": source_id,
                "target_id": target_id,
                "edge_type": edge_type.value,
                "source_text": source.text[:500],
                "target_text": target.text[:500],
                "source_type": source.type.value if hasattr(source.type, 'value') else str(source.type),
                "target_type": target.type.value if hasattr(target.type, 'value') else str(target.type),
                "label": None,  # To be filled by annotator
                "annotator": "",
                "confidence": None,
                "notes": "",
            }
            f.write(json.dumps(entry) + "\n")

    logger.info(f"Created annotation template with {len(pairs)} pairs: {template_path}")
    return template_path


def convert_template_to_gold(template_path: Path) -> GoldStandard:
    """
    Convert a completed annotation template to gold standard format.

    Args:
        template_path: Path to completed template file

    Returns:
        GoldStandard object
    """
    annotations = []
    expert_name = template_path.parent.name

    with open(template_path, "r") as f:
        for line in f:
            if not line.strip():
                continue

            data = json.loads(line)

            # Skip unannotated entries
            if data.get("label") is None:
                continue

            annotation = GoldEdge(
                source_id=data["source_id"],
                target_id=data["target_id"],
                edge_type=EdgeType(data["edge_type"]),
                label=bool(data["label"]),
                annotator=data.get("annotator"),
                confidence=data.get("confidence"),
                notes=data.get("notes"),
            )
            annotations.append(annotation)

    edge_types = set(a.edge_type for a in annotations)
    primary_edge_type = list(edge_types)[0] if edge_types else EdgeType.EXPLAINS

    return GoldStandard(
        expert_name=expert_name,
        edge_type=primary_edge_type,
        annotations=annotations,
    )


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Create sample gold standard
    from src.models import NodeType

    sample_nodes = [
        Node(id="A1", type=NodeType.TEXT_SECTION, text="Revenue increased due to iPhone sales.",
             metadata={"filing_id": "F1", "period": "FY2024"}),
        Node(id="A2", type=NodeType.TEXT_SECTION, text="See Note 3 for revenue details.",
             metadata={"filing_id": "F1", "period": "FY2024"}),
        Node(id="B1", type=NodeType.NOTE, text="Note 3 - Revenue Recognition.",
             metadata={"filing_id": "F1", "period": "FY2024", "note_number": 3}),
    ]

    # Create template
    settings.ensure_dirs()
    template_path = create_annotation_template(
        sample_nodes,
        "cross_reference",
        EdgeType.REFERS_TO,
        n_samples=5,
    )
    logger.info(f"Template created: {template_path}")
