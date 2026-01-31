"""Temporal Linker expert for connecting same entities across time periods."""

from collections import defaultdict
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts.base import BaseExpert, cosine_similarity
from src.experts.llm_client import LLMClient
from src.models import Edge, EdgeType, Node, NodeType


class TemporalLinker(BaseExpert):
    """
    Links the same financial items across time periods.

    Examples:
    - Revenue FY2022 -> Revenue FY2023 -> Revenue FY2024
    - Risk Factor about China in Q1 -> same topic in Q2
    """

    # Period ordering (earlier to later)
    PERIOD_ORDER = [
        "Q1-2022", "Q2-2022", "Q3-2022", "FY2022",
        "Q1-2023", "Q2-2023", "Q3-2023", "FY2023",
        "Q1-2024", "Q2-2024", "Q3-2024", "FY2024",
    ]

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.config = config or {}
        self.similarity_threshold = self.config.get(
            "similarity_threshold",
            settings.temporal_similarity_threshold,
        )

        # LLM mode configuration
        self.use_llm = self.config.get("use_llm", False)
        self._llm_client = None

    @property
    def llm_client(self) -> LLMClient | None:
        """Lazy-load LLM client."""
        if self._llm_client is None and self.use_llm:
            self._llm_client = LLMClient()
            if not self._llm_client.is_available():
                logger.warning("LLM not available for TemporalLinker")
                self._llm_client = None
        return self._llm_client

    def edge_types(self) -> list[EdgeType]:
        return [EdgeType.TEMPORAL_NEXT]

    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Discover temporal edges."""
        edges = []

        # Strategy 1: XBRL tag matching across periods
        edges.extend(self._link_by_xbrl_tag(nodes))

        # Strategy 2: Note number matching across filings
        edges.extend(self._link_by_note_number(nodes))

        # Strategy 3: Section matching across filings
        edges.extend(self._link_by_section(nodes, embeddings))

        # Strategy 4: High-similarity text across periods
        edges.extend(self._link_by_embedding_similarity(nodes, embeddings))

        # Strategy 5: LLM-verified temporal links (if enabled)
        if self.use_llm and self.llm_client:
            edges.extend(self._link_by_llm(nodes, embeddings))

        # Deduplicate and filter
        edges = self._deduplicate_edges(edges)
        edges = self._filter_by_confidence(edges)

        self.log_stats(edges)
        return edges

    def _get_period_index(self, period: str) -> int:
        """Get the ordering index for a period."""
        try:
            return self.PERIOD_ORDER.index(period)
        except ValueError:
            # Handle unknown periods
            return -1

    def _link_by_xbrl_tag(self, nodes: list[Node]) -> list[Edge]:
        """Link nodes with same XBRL tag across periods."""
        edges = []

        # Group financial line nodes by XBRL tag
        tag_groups = defaultdict(list)
        for node in nodes:
            if node.type == NodeType.FINANCIAL_LINE:
                tag = node.metadata.xbrl_tag
                if tag:
                    tag_groups[tag].append(node)

        # Create temporal edges within each group
        for tag, group_nodes in tag_groups.items():
            # Sort by period
            sorted_nodes = sorted(
                group_nodes,
                key=lambda n: self._get_period_index(n.metadata.period),
            )

            # Create edges between consecutive periods
            for i in range(len(sorted_nodes) - 1):
                source = sorted_nodes[i]
                target = sorted_nodes[i + 1]

                # Ensure they're actually different periods
                if source.metadata.period == target.metadata.period:
                    continue

                edge = self._create_edge(
                    source_id=source.id,
                    target_id=target.id,
                    edge_type=EdgeType.TEMPORAL_NEXT,
                    confidence=0.95,  # High confidence for exact XBRL match
                    evidence=f"Same XBRL tag: {tag}",
                    algorithm="xbrl_tag_match",
                )
                edges.append(edge)

        logger.debug(f"XBRL tag linking: {len(edges)} edges")
        return edges

    def _link_by_note_number(self, nodes: list[Node]) -> list[Edge]:
        """Link notes with same number across filings."""
        edges = []

        # Group notes by note number
        note_groups = defaultdict(list)
        for node in nodes:
            if node.type == NodeType.NOTE and node.metadata.note_number:
                note_groups[node.metadata.note_number].append(node)

        # Create temporal edges within each group
        for note_num, group_nodes in note_groups.items():
            sorted_nodes = sorted(
                group_nodes,
                key=lambda n: self._get_period_index(n.metadata.period),
            )

            for i in range(len(sorted_nodes) - 1):
                source = sorted_nodes[i]
                target = sorted_nodes[i + 1]

                if source.metadata.period == target.metadata.period:
                    continue

                edge = self._create_edge(
                    source_id=source.id,
                    target_id=target.id,
                    edge_type=EdgeType.TEMPORAL_NEXT,
                    confidence=0.90,  # High confidence for note number match
                    evidence=f"Same note number: Note {note_num}",
                    algorithm="note_number_match",
                )
                edges.append(edge)

        logger.debug(f"Note number linking: {len(edges)} edges")
        return edges

    def _link_by_section(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Link sections with same name across filings."""
        edges = []

        # Group text sections by section name
        section_groups = defaultdict(list)
        for node in nodes:
            if node.type == NodeType.TEXT_SECTION and node.metadata.section:
                section = node.metadata.section.lower()
                section_groups[section].append(node)

        # Create temporal edges within each group
        for section, group_nodes in section_groups.items():
            sorted_nodes = sorted(
                group_nodes,
                key=lambda n: self._get_period_index(n.metadata.period),
            )

            # For sections, use embedding similarity to verify match
            for i in range(len(sorted_nodes) - 1):
                source = sorted_nodes[i]
                target = sorted_nodes[i + 1]

                if source.metadata.period == target.metadata.period:
                    continue

                # Check embedding similarity
                if source.id in embeddings and target.id in embeddings:
                    sim = cosine_similarity(embeddings[source.id], embeddings[target.id])

                    if sim >= 0.7:  # Lower threshold for same-section links
                        edge = self._create_edge(
                            source_id=source.id,
                            target_id=target.id,
                            edge_type=EdgeType.TEMPORAL_NEXT,
                            confidence=sim,
                            evidence=f"Same section: {section} (similarity: {sim:.3f})",
                            algorithm="section_match",
                        )
                        edges.append(edge)

        logger.debug(f"Section linking: {len(edges)} edges")
        return edges

    def _link_by_embedding_similarity(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Link high-similarity nodes across different periods."""
        edges = []

        # Group nodes by type
        for node_type in [NodeType.TEXT_SECTION, NodeType.NOTE]:
            type_nodes = [n for n in nodes if n.type == node_type]

            # Group by period
            period_groups = defaultdict(list)
            for node in type_nodes:
                period_groups[node.metadata.period].append(node)

            # Compare nodes across consecutive periods
            sorted_periods = sorted(
                period_groups.keys(),
                key=lambda p: self._get_period_index(p),
            )

            for i in range(len(sorted_periods) - 1):
                current_period = sorted_periods[i]
                next_period = sorted_periods[i + 1]

                current_nodes = period_groups[current_period]
                next_nodes = period_groups[next_period]

                # Find highly similar pairs
                for node1 in current_nodes:
                    if node1.id not in embeddings:
                        continue

                    best_match = None
                    best_sim = 0.0

                    for node2 in next_nodes:
                        if node2.id not in embeddings:
                            continue

                        sim = cosine_similarity(embeddings[node1.id], embeddings[node2.id])

                        if sim > best_sim and sim >= self.similarity_threshold:
                            best_sim = sim
                            best_match = node2

                    if best_match:
                        edge = self._create_edge(
                            source_id=node1.id,
                            target_id=best_match.id,
                            edge_type=EdgeType.TEMPORAL_NEXT,
                            confidence=best_sim,
                            evidence=f"Embedding similarity: {best_sim:.3f}",
                            algorithm="embedding_similarity",
                        )
                        edges.append(edge)

        logger.debug(f"Embedding similarity linking: {len(edges)} edges")
        return edges

    def _link_by_llm(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Use LLM to verify and discover temporal links."""
        edges = []

        if not self.llm_client:
            return edges

        # Focus on text sections that might discuss same topics
        text_nodes = [n for n in nodes if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE]]

        # Group by period
        period_groups = defaultdict(list)
        for node in text_nodes:
            period_groups[node.metadata.period].append(node)

        sorted_periods = sorted(
            period_groups.keys(),
            key=lambda p: self._get_period_index(p),
        )

        # Compare candidate pairs across consecutive periods
        for i in range(len(sorted_periods) - 1):
            current_period = sorted_periods[i]
            next_period = sorted_periods[i + 1]

            current_nodes = period_groups[current_period]
            next_nodes = period_groups[next_period]

            # Pre-filter candidates using embeddings (similarity > 0.6)
            candidates = []
            for node1 in current_nodes[:20]:  # Limit for efficiency
                if node1.id not in embeddings:
                    continue
                for node2 in next_nodes[:20]:
                    if node2.id not in embeddings:
                        continue
                    sim = cosine_similarity(embeddings[node1.id], embeddings[node2.id])
                    if sim >= 0.6:
                        candidates.append((node1, node2, sim))

            # Sort by similarity and verify top candidates with LLM
            candidates.sort(key=lambda x: x[2], reverse=True)

            for node1, node2, emb_sim in candidates[:10]:  # Verify top 10
                try:
                    result = self.llm_client.extract_temporal_links(
                        node1.text[:1000],
                        node2.text[:1000],
                        current_period,
                        next_period,
                    )

                    if result.get("is_related", False):
                        llm_confidence = result.get("confidence", 0.7)
                        topic = result.get("topic", "same topic")

                        # Combine LLM confidence with embedding similarity
                        combined_confidence = (llm_confidence + emb_sim) / 2

                        edge = self._create_edge(
                            source_id=node1.id,
                            target_id=node2.id,
                            edge_type=EdgeType.TEMPORAL_NEXT,
                            confidence=combined_confidence,
                            evidence=f"LLM verified: {topic} (emb_sim: {emb_sim:.3f})",
                            algorithm="llm_temporal",
                        )
                        edges.append(edge)

                except Exception as e:
                    logger.debug(f"LLM temporal verification failed: {e}")
                    continue

        logger.debug(f"LLM temporal linking: {len(edges)} edges")
        return edges


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with sample nodes
    expert = TemporalLinker()

    test_nodes = [
        # Financial line items across years
        Node(
            id="FL_2022_001",
            type=NodeType.FINANCIAL_LINE,
            text="Total Revenue: $394.3B (FY2022)",
            metadata={"filing_id": "AAPL-10K-FY2022", "period": "FY2022", "xbrl_tag": "us-gaap:Revenues", "value": 394300000000},
        ),
        Node(
            id="FL_2023_001",
            type=NodeType.FINANCIAL_LINE,
            text="Total Revenue: $383.3B (FY2023)",
            metadata={"filing_id": "AAPL-10K-FY2023", "period": "FY2023", "xbrl_tag": "us-gaap:Revenues", "value": 383300000000},
        ),
        Node(
            id="FL_2024_001",
            type=NodeType.FINANCIAL_LINE,
            text="Total Revenue: $391.0B (FY2024)",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "xbrl_tag": "us-gaap:Revenues", "value": 391000000000},
        ),
        # Notes across years
        Node(
            id="NT_2023_003",
            type=NodeType.NOTE,
            text="Note 3 - Revenue Recognition policies...",
            metadata={"filing_id": "AAPL-10K-FY2023", "period": "FY2023", "note_number": 3},
        ),
        Node(
            id="NT_2024_003",
            type=NodeType.NOTE,
            text="Note 3 - Revenue Recognition policies...",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "note_number": 3},
        ),
    ]

    embeddings = {node.id: np.random.randn(768) for node in test_nodes}

    edges = expert.discover_edges(test_nodes, embeddings)

    for edge in edges:
        logger.info(f"Edge: {edge.source_id} -> {edge.target_id}")
        logger.info(f"  Type: {edge.edge_type}, Confidence: {edge.confidence:.2f}")
        logger.info(f"  Evidence: {edge.evidence}")
