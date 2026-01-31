"""Causal Chain Builder expert for identifying cause-effect relationships."""

import re
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts.base import BaseExpert, cosine_similarity, find_top_k_similar
from src.experts.llm_client import LLMClient
from src.models import Edge, EdgeType, Node, NodeType


class CausalChainBuilder(BaseExpert):
    """
    Identifies causal relationships in financial text.

    Examples:
    - "Revenue increased due to iPhone sales"
    - "Operating expenses rose, resulting in lower margins"
    """

    # Causal connectors - forward direction (A leads to B)
    # Match causal language while avoiding "might cause", "could cause" false positives
    CAUSAL_FORWARD = [
        r"resulted\s+in",
        r"led\s+to",
        r"(?:which|this|that|,\s*which)\s+caused",  # "which caused" - actual causation
        r"drove\s+(?:the|a|an|higher|lower|growth|decline)",
        r"contributed?\s+to",  # "contributed to" or "contribute to"
        r"therefore",
        r"consequently",
        r"as\s+a\s+result(?!\s+of)",  # "as a result" but not "as a result of"
        r"leading\s+to",
        r"resulting\s+in",
        r",\s*causing\s+",  # ", causing the"
    ]

    # Causal connectors - backward direction (B caused by A)
    CAUSAL_BACKWARD = [
        r"due\s+to\s+(?:the|a|an|higher|lower|strong|weak|increased|decreased)",
        r"(?:primarily|largely|mainly|partially)\s+due\s+to",
        r"because\s+of",
        r"driven\s+by",
        r"attributed?\s+to",
        r"as\s+a\s+result\s+of",
        r"resulting\s+from",
        r"caused\s+by",
        r"owing\s+to",
        r"on\s+account\s+of",
        r"stemming\s+from",
        r"partially\s+offset\s+by",
        r"offset\s+by",
        r"impacted\s+by",
        r"affected\s+by",
        r"(?:unfavorable|favorable)\s+(?:impact|effect)",  # "unfavorable impact"
        r"had\s+(?:a|an)\s+(?:unfavorable|favorable|positive|negative)\s+(?:impact|effect)",
    ]

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.config = config or {}
        self.confidence_threshold = self.config.get(
            "confidence_threshold",
            settings.causal_confidence_threshold,
        )
        self.use_llm = self.config.get("use_llm", False)
        self._llm_client = None

    @property
    def llm_client(self) -> LLMClient | None:
        """Lazy-load LLM client."""
        if self.use_llm and self._llm_client is None:
            self._llm_client = LLMClient()
            if not self._llm_client.is_available():
                logger.warning("LLM not available, falling back to pattern-only mode")
                self._llm_client = None
                self.use_llm = False
        return self._llm_client

    def edge_types(self) -> list[EdgeType]:
        return [EdgeType.CAUSED_BY, EdgeType.LEADS_TO]

    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Discover causal edges."""
        edges = []

        # Process text sections AND notes (both contain causal language)
        text_nodes = [n for n in nodes if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE]]
        logger.info(f"CausalChainBuilder processing {len(text_nodes)} text/note nodes")

        for node in text_nodes:
            # Strategy 1: Pattern-based extraction
            pattern_edges = self._extract_causal_patterns(node, nodes, embeddings)
            edges.extend(pattern_edges)

            # Strategy 2: LLM-based extraction (if enabled)
            if self.use_llm and self.llm_client:
                llm_edges = self._extract_causal_llm(node, nodes, embeddings)
                edges.extend(llm_edges)

        # Deduplicate and filter
        edges = self._deduplicate_edges(edges)
        edges = self._filter_by_confidence(edges)

        self.log_stats(edges)
        return edges

    def _extract_causal_patterns(
        self,
        node: Node,
        all_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Extract causal relations using regex patterns."""
        edges = []
        text = node.text

        # Split into sentences
        sentences = self._split_sentences(text)

        for sentence in sentences:
            # Check for forward causal patterns
            for pattern in self.CAUSAL_FORWARD:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    new_edges = self._process_causal_match(
                        sentence,
                        match,
                        "forward",
                        node,
                        all_nodes,
                        embeddings,
                    )
                    edges.extend(new_edges)
                    break  # One pattern per sentence

            # Check for backward causal patterns
            for pattern in self.CAUSAL_BACKWARD:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    new_edges = self._process_causal_match(
                        sentence,
                        match,
                        "backward",
                        node,
                        all_nodes,
                        embeddings,
                    )
                    edges.extend(new_edges)
                    break

        return edges

    def _process_causal_match(
        self,
        sentence: str,
        match: re.Match,
        direction: str,
        source_node: Node,
        all_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Process a causal pattern match and create edges."""
        edges = []

        # Split sentence at the causal connector
        connector_start = match.start()
        connector_end = match.end()

        if direction == "forward":
            # Cause is before connector, effect is after
            cause_text = sentence[:connector_start].strip()
            effect_text = sentence[connector_end:].strip()
        else:
            # Effect is before connector, cause is after
            effect_text = sentence[:connector_start].strip()
            cause_text = sentence[connector_end:].strip()

        # Skip if either part is too short
        if len(cause_text) < 10 or len(effect_text) < 10:
            return edges

        # Find nodes that match cause and effect
        cause_node = self._find_matching_node(cause_text, source_node, all_nodes, embeddings)
        effect_node = self._find_matching_node(effect_text, source_node, all_nodes, embeddings)

        # Strategy 1: If we found two different nodes, create edge between them
        if cause_node and effect_node and cause_node.id != effect_node.id:
            edges.append(self._create_edge(
                source_id=cause_node.id,
                target_id=effect_node.id,
                edge_type=EdgeType.LEADS_TO,
                confidence=0.80,
                evidence=sentence[:500],
                algorithm="regex_pattern",
                direction=direction,
                connector=match.group(0),
            ))

        # Strategy 2: If we found only cause_node, link source to cause
        elif cause_node and cause_node.id != source_node.id:
            edges.append(self._create_edge(
                source_id=source_node.id,
                target_id=cause_node.id,
                edge_type=EdgeType.CAUSED_BY,
                confidence=0.70,
                evidence=sentence[:500],
                algorithm="regex_pattern_partial",
                direction=direction,
                connector=match.group(0),
            ))

        # Strategy 3: If we found only effect_node, link source to effect
        elif effect_node and effect_node.id != source_node.id:
            edges.append(self._create_edge(
                source_id=source_node.id,
                target_id=effect_node.id,
                edge_type=EdgeType.LEADS_TO,
                confidence=0.70,
                evidence=sentence[:500],
                algorithm="regex_pattern_partial",
                direction=direction,
                connector=match.group(0),
            ))

        # Strategy 4: Find any related financial node in same filing
        else:
            related_node = self._find_any_related_financial_node(
                cause_text + " " + effect_text, source_node, all_nodes, embeddings
            )
            if related_node and related_node.id != source_node.id:
                edges.append(self._create_edge(
                    source_id=source_node.id,
                    target_id=related_node.id,
                    edge_type=EdgeType.CAUSED_BY if direction == "backward" else EdgeType.LEADS_TO,
                    confidence=0.65,
                    evidence=sentence[:500],
                    algorithm="regex_pattern_fallback",
                    direction=direction,
                    connector=match.group(0),
                ))
            else:
                # Strategy 5: Find any financial line node in same filing with keyword match
                related_node = self._find_keyword_related_node(
                    cause_text + " " + effect_text, source_node, all_nodes
                )
                if related_node and related_node.id != source_node.id:
                    edges.append(self._create_edge(
                        source_id=source_node.id,
                        target_id=related_node.id,
                        edge_type=EdgeType.CAUSED_BY if direction == "backward" else EdgeType.LEADS_TO,
                        confidence=0.60,
                        evidence=sentence[:500],
                        algorithm="regex_keyword_fallback",
                        direction=direction,
                        connector=match.group(0),
                    ))

        return edges

    def _find_matching_node(
        self,
        text: str,
        source_node: Node,
        all_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> Node | None:
        """Find a node that best matches the given text."""
        # First, check if the text contains a reference to a financial metric
        financial_keywords = [
            "revenue", "sales", "profit", "margin", "expense", "cost",
            "income", "earnings", "cash", "debt", "asset", "liability",
        ]

        text_lower = text.lower()
        for keyword in financial_keywords:
            if keyword in text_lower:
                # Look for financial line nodes
                for node in all_nodes:
                    if node.type == NodeType.FINANCIAL_LINE:
                        if keyword in node.text.lower():
                            if node.metadata.filing_id == source_node.metadata.filing_id:
                                return node

        # Use embedding similarity as fallback
        if source_node.id in embeddings:
            # Create a temporary embedding for the text span
            # For now, just find similar nodes in the same filing
            candidates = [
                n for n in all_nodes
                if n.metadata.filing_id == source_node.metadata.filing_id
                and n.id != source_node.id
                and n.id in embeddings
            ]

            if candidates:
                best_match = None
                best_sim = 0.0

                source_emb = embeddings[source_node.id]
                for candidate in candidates:
                    # Check if the candidate text overlaps with our target text
                    if any(word in candidate.text.lower() for word in text_lower.split()[:5]):
                        sim = cosine_similarity(source_emb, embeddings[candidate.id])
                        if sim > best_sim and sim > 0.5:
                            best_sim = sim
                            best_match = candidate

                return best_match

        return None

    def _find_any_related_financial_node(
        self,
        text: str,
        source_node: Node,
        all_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> Node | None:
        """Find any related financial node in the same filing using embedding similarity."""
        if source_node.id not in embeddings:
            return None

        source_emb = embeddings[source_node.id]

        # Get candidates from same filing
        candidates = [
            n for n in all_nodes
            if n.metadata.filing_id == source_node.metadata.filing_id
            and n.id != source_node.id
            and n.id in embeddings
            and n.type in [NodeType.FINANCIAL_LINE, NodeType.TEXT_SECTION, NodeType.NOTE]
        ]

        if not candidates:
            return None

        # Find most similar node
        best_match = None
        best_sim = 0.6  # Minimum threshold

        for candidate in candidates:
            sim = cosine_similarity(source_emb, embeddings[candidate.id])
            if sim > best_sim:
                best_sim = sim
                best_match = candidate

        return best_match

    def _find_keyword_related_node(
        self,
        text: str,
        source_node: Node,
        all_nodes: list[Node],
    ) -> Node | None:
        """Find a financial node in the same filing based on keyword overlap."""
        text_lower = text.lower()

        # Extract key financial terms from the text
        financial_keywords = [
            "revenue", "sales", "profit", "margin", "expense", "cost",
            "income", "earnings", "cash", "debt", "asset", "liability",
            "iphone", "mac", "ipad", "services", "wearables",
            "operating", "gross", "net", "interest", "tax",
            "americas", "europe", "china", "japan", "asia",
            "segment", "geographic", "region",
        ]

        found_keywords = [kw for kw in financial_keywords if kw in text_lower]

        if not found_keywords:
            # Even without keywords, try to find any financial node in same filing
            for node in all_nodes:
                if node.type == NodeType.FINANCIAL_LINE:
                    if node.metadata.filing_id == source_node.metadata.filing_id:
                        if node.id != source_node.id:
                            return node
            return None

        # Find financial line nodes in same filing with matching keywords
        for node in all_nodes:
            if node.type != NodeType.FINANCIAL_LINE:
                continue
            if node.metadata.filing_id != source_node.metadata.filing_id:
                continue
            if node.id == source_node.id:
                continue

            node_text_lower = node.text.lower()
            # Check if any keyword matches
            if any(kw in node_text_lower for kw in found_keywords):
                return node

        # Fallback: return any financial node from same filing
        for node in all_nodes:
            if node.type == NodeType.FINANCIAL_LINE:
                if node.metadata.filing_id == source_node.metadata.filing_id:
                    if node.id != source_node.id:
                        return node

        return None

    def _extract_causal_llm(
        self,
        node: Node,
        all_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Extract causal relations using LLM."""
        edges = []

        if not self.llm_client:
            return edges

        try:
            relations = self.llm_client.extract_causal_relations(node.text)

            for rel in relations:
                confidence = rel.get("confidence", 0.7)
                evidence = rel.get("evidence", node.text[:200])
                direction = rel.get("direction", "forward")

                # Try to find matching nodes for cause and effect
                cause_text = rel.get("cause", "")
                effect_text = rel.get("effect", "")

                cause_node = self._find_matching_node(cause_text, node, all_nodes, embeddings)
                effect_node = self._find_matching_node(effect_text, node, all_nodes, embeddings)

                if cause_node is None:
                    cause_node = node
                if effect_node is None:
                    effect_node = node

                if cause_node.id != effect_node.id:
                    edge = self._create_edge(
                        source_id=cause_node.id,
                        target_id=effect_node.id,
                        edge_type=EdgeType.LEADS_TO if direction == "forward" else EdgeType.CAUSED_BY,
                        confidence=confidence,
                        evidence=evidence,
                        algorithm="llm_extraction",
                    )
                    edges.append(edge)

        except Exception as e:
            logger.warning(f"LLM causal extraction failed: {e}")

        return edges

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with sample nodes
    expert = CausalChainBuilder({"use_llm": False})

    test_nodes = [
        Node(
            id="test_TS_001",
            type=NodeType.TEXT_SECTION,
            text="Revenue increased by 15% due to strong iPhone sales in emerging markets. The growth in Services revenue contributed to higher gross margins, resulting in improved profitability.",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "section": "Item 7"},
        ),
        Node(
            id="test_FL_001",
            type=NodeType.FINANCIAL_LINE,
            text="Total Revenue: $383.3B (FY2024)",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "xbrl_tag": "us-gaap:Revenues", "value": 383300000000},
        ),
        Node(
            id="test_FL_002",
            type=NodeType.FINANCIAL_LINE,
            text="Gross Profit: $170.8B (FY2024)",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "xbrl_tag": "us-gaap:GrossProfit", "value": 170800000000},
        ),
    ]

    embeddings = {node.id: np.random.randn(768) for node in test_nodes}

    edges = expert.discover_edges(test_nodes, embeddings)

    for edge in edges:
        logger.info(f"Edge: {edge.source_id} -> {edge.target_id} ({edge.edge_type})")
        logger.info(f"  Confidence: {edge.confidence:.2f}")
        logger.info(f"  Evidence: {edge.evidence[:100]}...")
