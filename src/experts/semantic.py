"""Semantic Bridge expert for connecting semantically similar content."""

from collections import defaultdict
from typing import Any

import numpy as np
from loguru import logger
from tqdm import tqdm

from src.config import settings
from src.experts.base import BaseExpert, batch_cosine_similarity, cosine_similarity
from src.experts.llm_client import LLMClient
from src.models import Edge, EdgeType, Node, NodeType


class SemanticBridge(BaseExpert):
    """
    Creates edges between semantically similar nodes.
    Also serves as fallback to ensure graph connectivity.
    """

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.config = config or {}
        self.similarity_threshold = self.config.get(
            "similarity_threshold",
            settings.semantic_similarity_threshold,
        )
        self.bridge_threshold = self.config.get(
            "bridge_threshold",
            settings.bridge_similarity_threshold,
        )
        self.max_edges_per_node = self.config.get("max_edges_per_node", 5)

        # LLM mode configuration
        self.use_llm = self.config.get("use_llm", False)
        self._llm_client = None

    @property
    def llm_client(self) -> LLMClient | None:
        """Lazy-load LLM client."""
        if self._llm_client is None and self.use_llm:
            self._llm_client = LLMClient()
            if not self._llm_client.is_available():
                logger.warning("LLM not available for SemanticBridge")
                self._llm_client = None
        return self._llm_client

    def edge_types(self) -> list[EdgeType]:
        return [EdgeType.SEMANTICALLY_SIMILAR, EdgeType.BRIDGE]

    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Discover semantic similarity edges."""
        edges = []

        # Strategy 1: High-similarity pairs within same filing
        edges.extend(self._find_similar_within_filing(nodes, embeddings))

        # Strategy 2: Cross-filing similarity (for related topics)
        edges.extend(self._find_cross_filing_similar(nodes, embeddings))

        # Strategy 3: LLM-verified semantic relationships (if enabled)
        if self.use_llm and self.llm_client:
            edges.extend(self._find_semantic_relations_llm(nodes, embeddings))

        # Deduplicate and filter
        edges = self._deduplicate_edges(edges)
        edges = self._filter_by_confidence(edges)

        self.log_stats(edges)
        return edges

    def _find_similar_within_filing(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Find semantically similar nodes within same filing."""
        edges = []

        # Group nodes by filing
        filing_groups = defaultdict(list)
        for node in nodes:
            if node.id in embeddings:
                filing_groups[node.metadata.filing_id].append(node)

        for filing_id, filing_nodes in filing_groups.items():
            logger.debug(f"Processing {filing_id} with {len(filing_nodes)} nodes")

            # Build embedding matrix for efficient computation
            node_ids = [n.id for n in filing_nodes]
            emb_matrix = np.array([embeddings[nid] for nid in node_ids])

            # Normalize embeddings
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            emb_matrix_norm = emb_matrix / norms

            # Compute pairwise similarities
            similarity_matrix = np.dot(emb_matrix_norm, emb_matrix_norm.T)

            # Find pairs above threshold
            for i in range(len(filing_nodes)):
                node1 = filing_nodes[i]
                node1_edges = 0

                for j in range(i + 1, len(filing_nodes)):
                    if node1_edges >= self.max_edges_per_node:
                        break

                    node2 = filing_nodes[j]
                    sim = similarity_matrix[i, j]

                    # Skip adjacent nodes of same type (likely already connected)
                    if node1.type == node2.type:
                        offset1 = node1.metadata.char_offset or 0
                        offset2 = node2.metadata.char_offset or 0
                        if abs(offset1 - offset2) < 1000:
                            continue

                    if sim >= self.similarity_threshold:
                        edge = self._create_edge(
                            source_id=node1.id,
                            target_id=node2.id,
                            edge_type=EdgeType.SEMANTICALLY_SIMILAR,
                            confidence=float(sim),
                            evidence=f"Cosine similarity: {sim:.3f}",
                            algorithm="within_filing_similarity",
                        )
                        edges.append(edge)
                        node1_edges += 1

        return edges

    def _find_cross_filing_similar(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Find similar nodes across different filings."""
        edges = []

        # Group nodes by filing and type
        filing_type_groups = defaultdict(list)
        for node in nodes:
            if node.id in embeddings:
                key = (node.metadata.filing_id, node.type)
                filing_type_groups[key].append(node)

        # Get unique filing IDs
        filing_ids = list(set(node.metadata.filing_id for node in nodes))
        filing_ids.sort()

        # Compare nodes across different filings (same type)
        for node_type in NodeType:
            # Get all nodes of this type grouped by filing
            type_by_filing = {
                fid: [n for n in nodes if n.metadata.filing_id == fid and n.type == node_type and n.id in embeddings]
                for fid in filing_ids
            }

            for i, fid1 in enumerate(filing_ids):
                nodes1 = type_by_filing[fid1]
                if not nodes1:
                    continue

                for fid2 in filing_ids[i + 1:]:
                    nodes2 = type_by_filing[fid2]
                    if not nodes2:
                        continue

                    # Find best matches (limit comparisons for efficiency)
                    sample_size = min(50, len(nodes1), len(nodes2))
                    sampled1 = nodes1[:sample_size]
                    sampled2 = nodes2[:sample_size]

                    for node1 in sampled1:
                        best_match = None
                        best_sim = 0.0

                        for node2 in sampled2:
                            sim = cosine_similarity(
                                embeddings[node1.id],
                                embeddings[node2.id],
                            )
                            if sim > best_sim and sim >= self.similarity_threshold:
                                best_sim = sim
                                best_match = node2

                        if best_match:
                            edge = self._create_edge(
                                source_id=node1.id,
                                target_id=best_match.id,
                                edge_type=EdgeType.SEMANTICALLY_SIMILAR,
                                confidence=best_sim,
                                evidence=f"Cross-filing similarity: {best_sim:.3f}",
                                algorithm="cross_filing_similarity",
                            )
                            edges.append(edge)

        return edges

    def _find_semantic_relations_llm(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Use LLM to analyze semantic relationships between candidate pairs."""
        edges = []

        if not self.llm_client:
            return edges

        # Focus on text sections and notes
        text_nodes = [
            n for n in nodes
            if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE] and n.id in embeddings
        ]

        # Pre-filter candidate pairs using embeddings (moderate similarity)
        # These are pairs that might have interesting relationships beyond simple similarity
        candidates = []

        for i, node1 in enumerate(text_nodes):
            for node2 in text_nodes[i + 1:]:
                # Skip if same node
                if node1.id == node2.id:
                    continue

                sim = cosine_similarity(embeddings[node1.id], embeddings[node2.id])

                # Look for moderate similarity (might have cause-effect or detail-summary relations)
                if 0.5 <= sim < self.similarity_threshold:
                    candidates.append((node1, node2, sim))

        # Sort by similarity and analyze top candidates
        candidates.sort(key=lambda x: x[2], reverse=True)

        for node1, node2, emb_sim in candidates[:30]:  # Analyze top 30
            try:
                result = self.llm_client.extract_semantic_relationships(
                    node1.text[:1000],
                    node2.text[:1000],
                )

                rel_type = result.get("relationship_type", "unrelated")
                llm_sim = result.get("similarity_score", 0.0)
                explanation = result.get("explanation", "")

                # Skip unrelated pairs
                if rel_type == "unrelated" or llm_sim < 0.5:
                    continue

                # Map LLM relationship types to edge types
                if rel_type == "cause_effect":
                    edge_type = EdgeType.CAUSED_BY
                elif rel_type in ["same_topic", "detail_summary"]:
                    edge_type = EdgeType.SEMANTICALLY_SIMILAR
                else:
                    edge_type = EdgeType.SEMANTICALLY_SIMILAR

                # Combine LLM score with embedding similarity
                combined_confidence = (llm_sim + emb_sim) / 2

                edge = self._create_edge(
                    source_id=node1.id,
                    target_id=node2.id,
                    edge_type=edge_type,
                    confidence=combined_confidence,
                    evidence=f"LLM: {rel_type} - {explanation[:100]}",
                    algorithm="llm_semantic",
                )
                edges.append(edge)

            except Exception as e:
                logger.debug(f"LLM semantic analysis failed: {e}")
                continue

        logger.debug(f"LLM semantic linking: {len(edges)} edges")
        return edges


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with sample nodes
    expert = SemanticBridge()

    test_nodes = [
        # Similar content in same filing
        Node(
            id="TS_001",
            type=NodeType.TEXT_SECTION,
            text="The Company's iPhone segment generated significant revenue growth driven by emerging markets.",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "section": "Item 7", "char_offset": 1000},
        ),
        Node(
            id="TS_002",
            type=NodeType.TEXT_SECTION,
            text="iPhone revenue increased substantially due to strong demand in developing regions and markets.",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "section": "Item 7", "char_offset": 5000},
        ),
        Node(
            id="TS_003",
            type=NodeType.TEXT_SECTION,
            text="Services revenue grew as subscription rates increased across all geographic segments.",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "section": "Item 7", "char_offset": 8000},
        ),
        # Similar content in different filing
        Node(
            id="TS_004",
            type=NodeType.TEXT_SECTION,
            text="iPhone sales showed robust growth in emerging markets during the fiscal year.",
            metadata={"filing_id": "AAPL-10K-FY2023", "period": "FY2023", "section": "Item 7", "char_offset": 1000},
        ),
    ]

    # Create embeddings that simulate similarity
    np.random.seed(42)
    base_iphone = np.random.randn(768)
    base_services = np.random.randn(768)

    embeddings = {
        "TS_001": base_iphone + 0.1 * np.random.randn(768),
        "TS_002": base_iphone + 0.1 * np.random.randn(768),
        "TS_003": base_services + 0.1 * np.random.randn(768),
        "TS_004": base_iphone + 0.15 * np.random.randn(768),
    }

    # Normalize embeddings
    for k in embeddings:
        embeddings[k] = embeddings[k] / np.linalg.norm(embeddings[k])

    edges = expert.discover_edges(test_nodes, embeddings)

    for edge in edges:
        logger.info(f"Edge: {edge.source_id} -> {edge.target_id}")
        logger.info(f"  Type: {edge.edge_type}, Confidence: {edge.confidence:.2f}")
        logger.info(f"  Evidence: {edge.evidence}")
