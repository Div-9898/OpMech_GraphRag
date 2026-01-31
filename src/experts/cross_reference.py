"""Cross-Reference Hunter expert for detecting explicit references between document sections."""

import re
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts.base import BaseExpert, cosine_similarity
from src.experts.llm_client import LLMClient
from src.models import Edge, EdgeType, Node, NodeType


class CrossReferenceHunter(BaseExpert):
    """
    Detects explicit cross-references in SEC filings.

    Examples:
    - "See Note 3"
    - "as discussed in Item 7"
    - "refer to Part II"

    Supports both regex-based and LLM-based extraction.
    """

    # Regex patterns for reference detection
    # Apple SEC filings use specific formats - patterns ordered by specificity
    REFERENCE_PATTERNS = [
        # Note references - Apple formats
        (r"[Ss]ee\s+Note\s*(\d+)", "note"),
        (r"[Rr]efer(?:red)?\s+to\s+Note\s*(\d+)", "note"),
        (r"[Dd]escribed\s+in\s+Note\s*(\d+)", "note"),
        (r"[Dd]iscussed\s+in\s+Note\s*(\d+)", "note"),
        (r"Note\s*(\d+)\s*[-–—,]\s*[,\"\"']([^\"\"']+)[\"\"']", "note_title"),  # Note 5 - , "Income Taxes"
        (r"Note\s*(\d+)\s+(?:provides|contains|discusses|describes)", "note"),
        (r"(?:in|under|per)\s+Note\s*(\d+)", "note"),
        (r"[Ss]ee\s+accompanying\s+[Nn]otes", "notes_general"),

        # Item references - cross-references (not headers)
        (r"[Ss]ee\s+Item\s*(\d+[A-Z]?)", "item"),
        (r"[Rr]efer(?:red)?\s+to\s+Item\s*(\d+[A-Z]?)", "item"),
        (r"[Dd]iscussed\s+in\s+Item\s*(\d+[A-Z]?)", "item"),
        (r"[Dd]escribed\s+in\s+Item\s*(\d+[A-Z]?)", "item"),
        (r"(?:in|under|per)\s+Item\s*(\d+[A-Z]?)\s+(?:of|in)", "item"),
        (r"Item\s*(\d+[A-Z]?)\s+(?:provides|contains|discusses|describes)", "item"),

        # Part + Item references (common in 10-K filings)
        (r"Part\s+(I{1,3}|IV),?\s*Item\s*(\d+[A-Z]?)", "part_item"),
        (r"[Ss]ee\s+Part\s+(I{1,3}|IV)", "part"),
        (r"(?:in|under)\s+Part\s+(I{1,3}|IV),?\s*Item\s*(\d+[A-Z]?)", "part_item"),

        # Section references with quotes (Apple uses this format)
        (r"[Aa]s\s+(?:discussed|described|noted)\s+(?:in|under)\s+[\"\"']([^\"\"']+)[\"\"']", "section_quoted"),
        (r"[Ss]ee\s+[\"\"']([^\"\"']+)[\"\"']", "section_quoted"),
        (r"(?:the|under)\s+heading\s+[\"\"']([^\"\"']+)[\"\"']", "section_quoted"),
        (r"[Dd]escribed\s+(?:below|above)", "section_relative"),
        (r"[Aa]s\s+(?:discussed|described|noted)\s+(?:above|below)", "section_relative"),

        # Table references
        (r"[Ss]ee\s+(?:the\s+)?(?:following|accompanying)\s+table", "table"),
        (r"[Tt]he\s+(?:following|above|below)\s+table", "table"),
        (r"[Ss]ummarized\s+in\s+the\s+(?:following|above)\s+table", "table"),

        # Financial statement references
        (r"[Ss]ee\s+(?:the\s+)?[Cc]onsolidated\s+(?:Statements?|Balance)", "financial_statement"),
        (r"[Ss]ee\s+(?:the\s+)?[Ff]inancial\s+[Ss]tatements?", "financial_statement"),
    ]

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.confidence_threshold = config.get(
            "confidence_threshold",
            settings.cross_ref_confidence_threshold,
        ) if config else settings.cross_ref_confidence_threshold

        # LLM mode configuration
        self.use_llm = config.get("use_llm", False) if config else False
        self._llm_client = None

    @property
    def llm_client(self) -> LLMClient | None:
        """Lazy-load LLM client."""
        if self._llm_client is None and self.use_llm:
            self._llm_client = LLMClient()
            if not self._llm_client.is_available():
                logger.warning("LLM not available for CrossReferenceHunter")
                self._llm_client = None
        return self._llm_client

    def edge_types(self) -> list[EdgeType]:
        return [EdgeType.REFERS_TO, EdgeType.EXPLAINS]

    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """Discover cross-reference edges."""
        edges = []

        # Build lookup maps
        note_nodes = self._build_note_map(nodes)
        section_nodes = self._build_section_map(nodes)
        table_nodes = [n for n in nodes if n.type == NodeType.TABLE_ROW]
        financial_nodes = [n for n in nodes if n.type == NodeType.FINANCIAL_LINE]

        logger.info(f"CrossReferenceHunter: {len(note_nodes)} note mappings, {len(section_nodes)} section mappings")

        # Process text sections and notes for references
        source_nodes = [
            n for n in nodes
            if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE]
        ]

        total_refs_found = 0
        total_refs_resolved = 0

        for source_node in source_nodes:
            # Find references in the text (regex + optionally LLM)
            references = self._extract_references(source_node.text)

            # Add LLM-extracted references if enabled
            if self.use_llm and self.llm_client:
                llm_references = self._extract_references_llm(source_node.text)
                # Merge LLM references, avoiding duplicates
                existing_positions = {pos for _, _, _, pos in references}
                for ref in llm_references:
                    if ref[3] not in existing_positions:
                        references.append(ref)

            total_refs_found += len(references)

            for ref_type, ref_value, match_text, position in references:
                # Try to resolve the reference to a target node
                target_node = self._resolve_reference(
                    ref_type,
                    ref_value,
                    source_node,
                    note_nodes,
                    section_nodes,
                    table_nodes,
                    nodes,
                    embeddings,
                )

                if target_node and target_node.id != source_node.id:
                    total_refs_resolved += 1
                    confidence = self._calculate_confidence(
                        source_node,
                        target_node,
                        ref_type,
                        match_text,
                    )

                    edge = self._create_edge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        edge_type=EdgeType.REFERS_TO,
                        confidence=confidence,
                        evidence=match_text,
                        algorithm="regex_pattern",
                        ref_type=ref_type,
                    )
                    edges.append(edge)

        llm_status = "with LLM" if (self.use_llm and self.llm_client) else "regex only"
        logger.info(f"CrossReferenceHunter ({llm_status}): Found {total_refs_found} references, resolved {total_refs_resolved}")

        # Deduplicate and filter
        edges = self._deduplicate_edges(edges)
        edges = self._filter_by_confidence(edges)

        self.log_stats(edges)
        return edges

    def _build_note_map(self, nodes: list[Node]) -> dict[int, list[Node]]:
        """Build a map of note number -> list of nodes (across filings)."""
        note_map = {}
        for node in nodes:
            if node.type == NodeType.NOTE and node.metadata.note_number:
                note_num = node.metadata.note_number
                if note_num not in note_map:
                    note_map[note_num] = []
                note_map[note_num].append(node)
        return note_map

    def _build_section_map(self, nodes: list[Node]) -> dict[str, list[Node]]:
        """Build a map of section name -> nodes."""
        section_map = {}
        for node in nodes:
            if node.type == NodeType.TEXT_SECTION and node.metadata.section:
                section = node.metadata.section.lower()
                if section not in section_map:
                    section_map[section] = []
                section_map[section].append(node)
        return section_map

    def _extract_references(self, text: str) -> list[tuple[str, str, str, int]]:
        """
        Extract references from text.

        Returns:
            List of (ref_type, ref_value, match_text, position)
        """
        references = []
        seen_positions = set()  # Avoid duplicate matches at same position

        for pattern, ref_type in self.REFERENCE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Skip if we already have a match at this position
                if match.start() in seen_positions:
                    continue

                if ref_type == "part_item":
                    # Special handling for Part X, Item Y format
                    ref_value = f"Part {match.group(1)} Item {match.group(2)}"
                elif ref_type == "note_title":
                    # Note with title: use note number
                    ref_value = match.group(1)
                elif ref_type in ["notes_general", "section_relative", "financial_statement"]:
                    # General references without specific target
                    ref_value = ""
                elif match.groups():
                    ref_value = match.group(1)
                else:
                    ref_value = ""

                references.append((
                    ref_type,
                    ref_value,
                    match.group(0),
                    match.start(),
                ))
                seen_positions.add(match.start())

        return references

    def _extract_references_llm(self, text: str) -> list[tuple[str, str, str, int]]:
        """
        Extract references using LLM.

        Returns:
            List of (ref_type, ref_value, match_text, position)
        """
        if not self.llm_client:
            return []

        try:
            llm_results = self.llm_client.extract_cross_references(text)
            references = []

            for result in llm_results:
                ref_type = result.get("target_type", "section")
                ref_value = result.get("target_id", "")
                match_text = result.get("source_text", "")

                # Map LLM types to our types
                type_map = {
                    "note": "note",
                    "item": "item",
                    "part": "part",
                    "table": "table",
                    "section": "section_quoted",
                }
                ref_type = type_map.get(ref_type, ref_type)

                # Use hash of match_text as pseudo-position (for dedup)
                position = hash(match_text) % 1000000

                references.append((ref_type, ref_value, match_text, position))

            logger.debug(f"LLM extracted {len(references)} cross-references")
            return references

        except Exception as e:
            logger.warning(f"LLM cross-reference extraction failed: {e}")
            return []

    def _resolve_reference(
        self,
        ref_type: str,
        ref_value: str,
        source_node: Node,
        note_nodes: dict[int, Node],
        section_nodes: dict[str, list[Node]],
        table_nodes: list[Node],
        all_nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> Node | None:
        """Resolve a reference to a target node."""

        # Same filing preference
        source_filing = source_node.metadata.filing_id

        if ref_type in ["note", "note_title"]:
            try:
                note_num = int(ref_value)
                # First try exact note number match in same filing
                if note_num in note_nodes:
                    for node in note_nodes[note_num]:
                        if node.metadata.filing_id == source_filing:
                            return node
                    # Fall back to first note with this number
                    return note_nodes[note_num][0]
            except ValueError:
                pass

        elif ref_type == "notes_general":
            # "See accompanying Notes" - link to first note in same filing
            for node in all_nodes:
                if (node.type == NodeType.NOTE and
                    node.metadata.filing_id == source_filing):
                    return node

        elif ref_type in ["item", "part_item", "part"]:
            # Look for matching section
            search_key = f"item {ref_value}".lower() if ref_type == "item" else ref_value.lower()

            for section_key, nodes in section_nodes.items():
                if search_key in section_key or section_key in search_key:
                    # Prefer same filing
                    for node in nodes:
                        if node.metadata.filing_id == source_filing:
                            return node
                    # Fall back to any match
                    if nodes:
                        return nodes[0]

            # Also search by node text/section metadata
            for node in all_nodes:
                if node.type == NodeType.TEXT_SECTION:
                    node_section = (node.metadata.section or "").lower()
                    if search_key in node_section:
                        if node.metadata.filing_id == source_filing:
                            return node

        elif ref_type in ["section", "section_quoted"]:
            # Fuzzy match on section names
            ref_lower = ref_value.lower() if ref_value else ""
            for section_key, nodes in section_nodes.items():
                if ref_lower and (ref_lower in section_key or section_key in ref_lower):
                    for node in nodes:
                        if node.metadata.filing_id == source_filing:
                            return node
                    if nodes:
                        return nodes[0]

        elif ref_type == "section_relative":
            # "described above/below" - find similar section in same filing
            if source_node.id in embeddings:
                source_emb = embeddings[source_node.id]
                best_match = None
                best_sim = 0.6

                for node in all_nodes:
                    if (node.type == NodeType.TEXT_SECTION and
                        node.metadata.filing_id == source_filing and
                        node.id != source_node.id and
                        node.id in embeddings):
                        sim = cosine_similarity(source_emb, embeddings[node.id])
                        if sim > best_sim:
                            best_sim = sim
                            best_match = node

                if best_match:
                    return best_match

        elif ref_type == "table":
            # Find nearest table (by position or embedding similarity)
            if source_node.id in embeddings:
                source_emb = embeddings[source_node.id]

                # Find most similar table in same filing
                best_table = None
                best_sim = 0.5

                for table_node in table_nodes:
                    if table_node.metadata.filing_id != source_filing:
                        continue
                    if table_node.id not in embeddings:
                        continue

                    sim = cosine_similarity(source_emb, embeddings[table_node.id])
                    if sim > best_sim:
                        best_sim = sim
                        best_table = table_node

                if best_table:
                    return best_table

        elif ref_type == "financial_statement":
            # Link to financial line items in same filing
            for node in all_nodes:
                if (node.type == NodeType.FINANCIAL_LINE and
                    node.metadata.filing_id == source_filing):
                    return node

        return None

    def _calculate_confidence(
        self,
        source_node: Node,
        target_node: Node,
        ref_type: str,
        match_text: str,
    ) -> float:
        """Calculate confidence score for the reference."""
        # Confidence by reference type
        confidence_map = {
            "note": 0.95,
            "note_title": 0.95,
            "notes_general": 0.80,
            "item": 0.90,
            "part_item": 0.90,
            "part": 0.85,
            "section_quoted": 0.85,
            "section": 0.75,
            "section_relative": 0.70,
            "table": 0.75,
            "financial_statement": 0.80,
        }

        confidence = confidence_map.get(ref_type, 0.70)

        # Bonus for same filing
        if source_node.metadata.filing_id == target_node.metadata.filing_id:
            confidence = min(1.0, confidence + 0.05)

        return confidence


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with sample nodes
    expert = CrossReferenceHunter()

    test_nodes = [
        Node(
            id="test_TS_001",
            type=NodeType.TEXT_SECTION,
            text="As discussed in Note 3, the Company recognized revenue of $100 million. See Item 7 for more details on management's discussion.",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "section": "Item 1"},
        ),
        Node(
            id="test_NT_003",
            type=NodeType.NOTE,
            text="Note 3 - Revenue Recognition. The Company recognizes revenue when control transfers...",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "section": "Note 3", "note_number": 3},
        ),
        Node(
            id="test_TS_007",
            type=NodeType.TEXT_SECTION,
            text="Management's Discussion and Analysis of Financial Condition...",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "section": "Item 7"},
        ),
    ]

    # Create dummy embeddings
    embeddings = {node.id: np.random.randn(768) for node in test_nodes}

    edges = expert.discover_edges(test_nodes, embeddings)

    for edge in edges:
        logger.info(f"Edge: {edge.source_id} -> {edge.target_id} ({edge.edge_type}, conf={edge.confidence:.2f})")
        logger.info(f"  Evidence: {edge.evidence}")
