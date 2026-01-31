"""Table-Text Connector expert for linking table data to explanatory text."""

import re
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts.base import BaseExpert, cosine_similarity
from src.experts.llm_client import LLMClient
from src.models import Edge, EdgeType, Node, NodeType


class TableTextConnector(BaseExpert):
    """
    Connects table rows to text that explains them.

    Examples:
    - Table showing revenue by segment <-> MD&A discussing segment performance
    - Balance sheet line item <-> Note explaining the item
    """

    # Numeric patterns to extract from text
    NUMERIC_PATTERNS = [
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:billion|B)",  # $X billion
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:million|M)",  # $X million
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:thousand|K)?",  # $X or $X thousand
        r"([\d,]+(?:\.\d+)?)\s*(?:percent|%)",  # X percent
    ]

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.config = config or {}
        self.similarity_threshold = self.config.get(
            "similarity_threshold",
            settings.table_text_similarity_threshold,
        )
        self.numeric_tolerance = self.config.get("numeric_tolerance", 0.05)  # 5%

        # LLM mode configuration
        self.use_llm = self.config.get("use_llm", False)
        self._llm_client = None

    @property
    def llm_client(self) -> LLMClient | None:
        """Lazy-load LLM client."""
        if self._llm_client is None and self.use_llm:
            self._llm_client = LLMClient()
            if not self._llm_client.is_available():
                logger.warning("LLM not available for TableTextConnector")
                self._llm_client = None
        return self._llm_client

    def edge_types(self) -> list[EdgeType]:
        return [EdgeType.EXPLAINS_LINE_ITEM, EdgeType.DISCUSSES]

    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Discover table-text connector edges."""
        edges = []

        # Get table nodes and text nodes
        table_nodes = [
            n for n in nodes
            if n.type in [NodeType.TABLE_ROW, NodeType.FINANCIAL_LINE]
        ]
        text_nodes = [
            n for n in nodes
            if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE]
        ]

        for table_node in table_nodes:
            # Strategy 1: Numeric value matching
            if table_node.metadata.value:
                numeric_edges = self._find_numeric_matches(table_node, text_nodes)
                edges.extend(numeric_edges)

            # Strategy 2: XBRL tag to text matching
            if table_node.metadata.xbrl_tag:
                xbrl_edges = self._find_xbrl_text_matches(table_node, text_nodes, embeddings)
                edges.extend(xbrl_edges)

            # Strategy 3: Embedding similarity
            sim_edges = self._find_similar_text(table_node, text_nodes, embeddings)
            edges.extend(sim_edges)

        # Strategy 4: LLM-based table-text connection (if enabled)
        if self.use_llm and self.llm_client:
            llm_edges = self._find_connections_llm(table_nodes, text_nodes, embeddings)
            edges.extend(llm_edges)

        # Deduplicate and filter
        edges = self._deduplicate_edges(edges)
        edges = self._filter_by_confidence(edges)

        self.log_stats(edges)
        return edges

    def _find_numeric_matches(
        self,
        table_node: Node,
        text_nodes: list[Node],
    ) -> list[Edge]:
        """Find text nodes mentioning similar numeric values."""
        edges = []
        target_value = table_node.metadata.value

        if target_value is None or target_value == 0:
            return edges

        # Determine scale for comparison
        abs_value = abs(target_value)

        for text_node in text_nodes:
            # Must be same filing
            if text_node.metadata.filing_id != table_node.metadata.filing_id:
                continue

            # Extract numbers from text
            text_numbers = self._extract_numbers(text_node.text)

            for num, match_text in text_numbers:
                if num == 0:
                    continue

                # Check for match within tolerance
                rel_diff = abs(num - abs_value) / abs_value if abs_value != 0 else float('inf')

                if rel_diff <= self.numeric_tolerance:
                    edge = self._create_edge(
                        source_id=text_node.id,
                        target_id=table_node.id,
                        edge_type=EdgeType.EXPLAINS_LINE_ITEM,
                        confidence=0.85,
                        evidence=f"Numeric match: {match_text} ~ {abs_value:,.0f}",
                        algorithm="numeric_match",
                    )
                    edges.append(edge)
                    break  # One match per text node

        return edges

    def _extract_numbers(self, text: str) -> list[tuple[float, str]]:
        """Extract numeric values from text."""
        numbers = []

        for pattern in self.NUMERIC_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    num_str = match.group(1).replace(",", "")
                    num = float(num_str)

                    # Apply scale multipliers
                    match_text = match.group(0).lower()
                    if "billion" in match_text or match_text.endswith("b"):
                        num *= 1_000_000_000
                    elif "million" in match_text or match_text.endswith("m"):
                        num *= 1_000_000
                    elif "thousand" in match_text or match_text.endswith("k"):
                        num *= 1_000

                    numbers.append((num, match.group(0)))
                except (ValueError, IndexError):
                    continue

        return numbers

    def _find_xbrl_text_matches(
        self,
        table_node: Node,
        text_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Find text that discusses the XBRL concept."""
        edges = []

        xbrl_tag = table_node.metadata.xbrl_tag
        if not xbrl_tag:
            return edges

        # Extract concept name from XBRL tag
        concept = xbrl_tag.split(":")[-1]

        # Convert CamelCase to words
        words = re.findall(r"[A-Z][a-z]+|[a-z]+", concept)
        keywords = [w.lower() for w in words]

        for text_node in text_nodes:
            # Must be same filing
            if text_node.metadata.filing_id != table_node.metadata.filing_id:
                continue

            text_lower = text_node.text.lower()

            # Check if keywords appear in text
            keyword_matches = sum(1 for kw in keywords if kw in text_lower)
            keyword_ratio = keyword_matches / len(keywords) if keywords else 0

            if keyword_ratio >= 0.5:  # At least half the keywords match
                # Verify with embedding similarity
                if table_node.id in embeddings and text_node.id in embeddings:
                    sim = cosine_similarity(embeddings[table_node.id], embeddings[text_node.id])

                    if sim >= 0.6:  # Lower threshold since we have keyword match
                        confidence = (keyword_ratio + sim) / 2

                        edge = self._create_edge(
                            source_id=text_node.id,
                            target_id=table_node.id,
                            edge_type=EdgeType.DISCUSSES,
                            confidence=confidence,
                            evidence=f"XBRL concept match: {concept} (keywords: {keyword_matches}/{len(keywords)}, sim: {sim:.3f})",
                            algorithm="xbrl_concept_match",
                        )
                        edges.append(edge)

        return edges

    def _find_similar_text(
        self,
        table_node: Node,
        text_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Find semantically similar text nodes."""
        edges = []

        if table_node.id not in embeddings:
            return edges

        table_emb = embeddings[table_node.id]

        for text_node in text_nodes:
            # Must be same filing
            if text_node.metadata.filing_id != table_node.metadata.filing_id:
                continue

            if text_node.id not in embeddings:
                continue

            sim = cosine_similarity(table_emb, embeddings[text_node.id])

            if sim >= self.similarity_threshold:
                edge = self._create_edge(
                    source_id=text_node.id,
                    target_id=table_node.id,
                    edge_type=EdgeType.DISCUSSES,
                    confidence=sim,
                    evidence=f"Semantic similarity: {sim:.3f}",
                    algorithm="embedding_similarity",
                )
                edges.append(edge)

        return edges

    def _find_connections_llm(
        self,
        table_nodes: list[Node],
        text_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Use LLM to find connections between tables and text."""
        edges = []

        if not self.llm_client:
            return edges

        # Group nodes by filing
        table_by_filing = {}
        text_by_filing = {}

        for node in table_nodes:
            filing_id = node.metadata.filing_id
            if filing_id not in table_by_filing:
                table_by_filing[filing_id] = []
            table_by_filing[filing_id].append(node)

        for node in text_nodes:
            filing_id = node.metadata.filing_id
            if filing_id not in text_by_filing:
                text_by_filing[filing_id] = []
            text_by_filing[filing_id].append(node)

        # Process each filing
        for filing_id in table_by_filing:
            if filing_id not in text_by_filing:
                continue

            filing_tables = table_by_filing[filing_id][:20]  # Limit for efficiency
            filing_texts = text_by_filing[filing_id][:20]

            for text_node in filing_texts:
                # Combine table texts for context
                table_text = "\n".join([
                    f"- {t.text[:200]}" for t in filing_tables[:10]
                ])

                try:
                    connections = self.llm_client.extract_table_text_connections(
                        table_text[:1500],
                        text_node.text[:1500],
                    )

                    for conn in connections:
                        table_item = conn.get("table_item", "")
                        confidence = conn.get("confidence", 0.7)
                        conn_type = conn.get("connection_type", "metric_discussion")

                        # Find the matching table node
                        best_table = None
                        best_match_score = 0

                        for t_node in filing_tables:
                            # Simple text overlap check
                            if table_item.lower() in t_node.text.lower():
                                # Use embedding similarity to confirm
                                if t_node.id in embeddings and text_node.id in embeddings:
                                    sim = cosine_similarity(
                                        embeddings[t_node.id],
                                        embeddings[text_node.id]
                                    )
                                    if sim > best_match_score:
                                        best_match_score = sim
                                        best_table = t_node

                        if best_table:
                            edge_type = EdgeType.EXPLAINS_LINE_ITEM if conn_type == "numeric_match" else EdgeType.DISCUSSES

                            edge = self._create_edge(
                                source_id=text_node.id,
                                target_id=best_table.id,
                                edge_type=edge_type,
                                confidence=min(confidence, best_match_score + 0.2),
                                evidence=f"LLM connection: {conn_type} - {table_item[:50]}",
                                algorithm="llm_table_text",
                            )
                            edges.append(edge)

                except Exception as e:
                    logger.debug(f"LLM table-text connection failed: {e}")
                    continue

        logger.debug(f"LLM table-text linking: {len(edges)} edges")
        return edges


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with sample nodes
    expert = TableTextConnector()

    test_nodes = [
        # Financial line item
        Node(
            id="FL_001",
            type=NodeType.FINANCIAL_LINE,
            text="Total Revenue: $383.3B (FY2024)",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "xbrl_tag": "us-gaap:Revenues", "value": 383_300_000_000},
        ),
        # Table row
        Node(
            id="TR_001",
            type=NodeType.TABLE_ROW,
            text="iPhone | $200,583 | $205,489 | (2%)",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "value": 200_583_000_000},
        ),
        # Text discussing revenue
        Node(
            id="TS_001",
            type=NodeType.TEXT_SECTION,
            text="Total net sales increased by $383 billion, or 2%, during 2024 compared to 2023. The growth was primarily driven by higher iPhone and Services revenue.",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "section": "Item 7"},
        ),
        # Note about iPhone
        Node(
            id="NT_001",
            type=NodeType.NOTE,
            text="iPhone revenue of $200.6 billion represented 52% of total net sales for fiscal 2024.",
            metadata={"filing_id": "AAPL-10K-FY2024", "period": "FY2024", "section": "Note 1"},
        ),
    ]

    embeddings = {node.id: np.random.randn(768) for node in test_nodes}

    edges = expert.discover_edges(test_nodes, embeddings)

    for edge in edges:
        logger.info(f"Edge: {edge.source_id} -> {edge.target_id}")
        logger.info(f"  Type: {edge.edge_type}, Confidence: {edge.confidence:.2f}")
        logger.info(f"  Evidence: {edge.evidence}")
