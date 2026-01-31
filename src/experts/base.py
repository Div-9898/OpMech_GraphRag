"""Base expert class and common utilities for MoE experts."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from loguru import logger

from src.models import Edge, EdgeType, Metrics, Node


class BaseExpert(ABC):
    """Abstract base class for all experts."""

    def __init__(self, config: dict[str, Any] = None):
        """
        Initialize the expert.

        Args:
            config: Configuration dictionary with expert-specific settings
        """
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """
        Discover edges of this expert's type.

        Args:
            nodes: List of all nodes in the graph
            embeddings: Dictionary mapping node_id -> embedding vector

        Returns:
            List of discovered edges with confidence scores
        """
        pass

    @abstractmethod
    def edge_types(self) -> list[EdgeType]:
        """Return edge types this expert discovers."""
        pass

    def get_confidence_threshold(self) -> float:
        """Get minimum confidence threshold for emitting edges."""
        return self.config.get("confidence_threshold", 0.5)

    def evaluate(
        self,
        predictions: list[Edge],
        gold: list[Edge],
    ) -> Metrics:
        """
        Evaluate expert predictions against gold standard.

        Args:
            predictions: Predicted edges
            gold: Gold standard edges

        Returns:
            Metrics object with precision, recall, F1
        """
        # Create sets for comparison (using source_id, target_id, edge_type)
        pred_set = {
            (e.source_id, e.target_id, e.edge_type)
            for e in predictions
        }
        gold_set = {
            (e.source_id, e.target_id, e.edge_type)
            for e in gold
        }

        # Calculate metrics
        tp = len(pred_set & gold_set)
        fp = len(pred_set - gold_set)
        fn = len(gold_set - pred_set)

        return Metrics.calculate(tp, fp, fn)

    def _deduplicate_edges(self, edges: list[Edge]) -> list[Edge]:
        """Remove duplicate edges, keeping the one with highest confidence."""
        edge_map: dict[str, Edge] = {}

        for edge in edges:
            key = f"{edge.source_id}__{edge.edge_type}__{edge.target_id}"

            if key not in edge_map or edge.confidence > edge_map[key].confidence:
                edge_map[key] = edge

        return list(edge_map.values())

    def _filter_by_confidence(
        self,
        edges: list[Edge],
        threshold: float = None,
    ) -> list[Edge]:
        """Filter edges by confidence threshold."""
        threshold = threshold or self.get_confidence_threshold()
        return [e for e in edges if e.confidence >= threshold]

    def _create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        confidence: float,
        evidence: str,
        **metadata,
    ) -> Edge:
        """Helper to create an edge with consistent formatting."""
        # Clamp confidence to [0, 1] to handle floating point precision issues
        clamped_confidence = max(0.0, min(1.0, confidence))
        return Edge(
            id=Edge.create_id(source_id, edge_type, target_id),
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            confidence=clamped_confidence,
            expert=self.name,
            evidence=evidence[:500] if evidence else "",
            metadata=metadata,
        )

    def log_stats(self, edges: list[Edge]) -> None:
        """Log statistics about discovered edges."""
        if not edges:
            logger.info(f"{self.name}: No edges discovered")
            return

        # Count by edge type
        type_counts = {}
        confidence_sum = 0.0

        for edge in edges:
            type_counts[edge.edge_type] = type_counts.get(edge.edge_type, 0) + 1
            confidence_sum += edge.confidence

        avg_confidence = confidence_sum / len(edges)

        logger.info(f"{self.name}: Discovered {len(edges)} edges")
        logger.info(f"  Average confidence: {avg_confidence:.3f}")
        for edge_type, count in type_counts.items():
            logger.info(f"  {edge_type}: {count}")


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(emb1, emb2) / (norm1 * norm2))


def batch_cosine_similarity(
    query: np.ndarray,
    embeddings: np.ndarray,
) -> np.ndarray:
    """
    Compute cosine similarity between a query and multiple embeddings.

    Args:
        query: Query embedding (768,)
        embeddings: Matrix of embeddings (N, 768)

    Returns:
        Array of similarities (N,)
    """
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.zeros(len(embeddings))

    query_normalized = query / query_norm
    emb_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    emb_norms = np.where(emb_norms == 0, 1, emb_norms)  # Avoid division by zero
    embeddings_normalized = embeddings / emb_norms

    return np.dot(embeddings_normalized, query_normalized)


def find_top_k_similar(
    query_embedding: np.ndarray,
    embeddings: dict[str, np.ndarray],
    k: int = 10,
    threshold: float = 0.0,
    exclude_ids: set[str] = None,
) -> list[tuple[str, float]]:
    """
    Find top-k most similar nodes to a query.

    Args:
        query_embedding: Query embedding
        embeddings: Dictionary of node_id -> embedding
        k: Number of results
        threshold: Minimum similarity
        exclude_ids: Node IDs to exclude from results

    Returns:
        List of (node_id, similarity) tuples
    """
    exclude_ids = exclude_ids or set()

    similarities = []
    for node_id, embedding in embeddings.items():
        if node_id in exclude_ids:
            continue
        sim = cosine_similarity(query_embedding, embedding)
        if sim >= threshold:
            similarities.append((node_id, sim))

    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:k]
