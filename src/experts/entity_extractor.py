"""LLM-powered Entity Extractor for identifying and classifying entities in SEC filings."""

import hashlib
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts.base import BaseExpert, cosine_similarity
from src.experts.llm_client import LLMClient
from src.models import Edge, EdgeType, Node, NodeMetadata, NodeType


class EntityExtractor(BaseExpert):
    """
    Extracts named entities from SEC filings using LLM.

    Entity Types:
    - COMPANY: Companies mentioned (Apple, suppliers, competitors)
    - PRODUCT: Products and services (iPhone, Mac, Services)
    - SEGMENT: Business/geographic segments (Americas, Greater China)
    - PERSON: Key executives mentioned
    - FINANCIAL_METRIC: Revenue, profit, expenses, etc.
    - RISK_FACTOR: Identified risks
    - REGULATION: Laws, regulations, standards mentioned
    """

    ENTITY_TYPES = [
        "COMPANY",
        "PRODUCT",
        "SEGMENT",
        "PERSON",
        "FINANCIAL_METRIC",
        "RISK_FACTOR",
        "REGULATION",
    ]

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.config = config or {}
        self._llm_client = None
        self._entity_cache: dict[str, Node] = {}  # Cache entities by name+type

    @property
    def llm_client(self) -> LLMClient | None:
        """Lazy-load LLM client."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
            if not self._llm_client.is_available():
                logger.error("LLM not available - EntityExtractor requires vLLM server")
                self._llm_client = None
        return self._llm_client

    def edge_types(self) -> list[EdgeType]:
        return [EdgeType.MENTIONS_ENTITY, EdgeType.ENTITY_RELATED_TO]

    def extract_entities_from_nodes(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> tuple[list[Node], list[Edge]]:
        """
        Extract entities from text nodes and create entity nodes + edges.

        Returns:
            Tuple of (entity_nodes, edges)
        """
        if not self.llm_client:
            logger.error("Cannot extract entities - LLM not available")
            return [], []

        entity_nodes = []
        edges = []
        entity_counter = 0

        # Process text sections and notes
        text_nodes = [
            n for n in nodes
            if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE]
        ]

        logger.info(f"Extracting entities from {len(text_nodes)} text nodes using LLM...")

        for i, node in enumerate(text_nodes):
            if i % 50 == 0:
                logger.info(f"Processing node {i+1}/{len(text_nodes)}...")

            try:
                # Extract entities using LLM
                extracted = self._extract_entities_llm(node)

                for entity_data in extracted:
                    entity_name = entity_data.get("name", "").strip()
                    entity_type = entity_data.get("type", "COMPANY").upper()
                    context = entity_data.get("context", "")

                    if not entity_name or len(entity_name) < 2:
                        continue

                    # Validate entity type
                    if entity_type not in self.ENTITY_TYPES:
                        entity_type = "COMPANY"

                    # Create or get existing entity node
                    cache_key = f"{entity_name.lower()}_{entity_type}"

                    if cache_key in self._entity_cache:
                        entity_node = self._entity_cache[cache_key]
                    else:
                        entity_counter += 1
                        entity_node = Node(
                            id=f"ENTITY_{entity_type}_{entity_counter:04d}",
                            type=NodeType.ENTITY,
                            text=f"{entity_name} ({entity_type})",
                            metadata=NodeMetadata(
                                filing_id=node.metadata.filing_id,
                                period=node.metadata.period,
                                entity_type=entity_type,
                            ),
                        )
                        self._entity_cache[cache_key] = entity_node
                        entity_nodes.append(entity_node)

                    # Create edge from source node to entity
                    edge = self._create_edge(
                        source_id=node.id,
                        target_id=entity_node.id,
                        edge_type=EdgeType.MENTIONS_ENTITY,
                        confidence=0.85,
                        evidence=context[:500] if context else f"Mentions {entity_name}",
                        algorithm="llm_entity_extraction",
                        entity_type=entity_type,
                    )
                    edges.append(edge)

            except Exception as e:
                logger.warning(f"Entity extraction failed for node {node.id}: {e}")
                continue

        # Create entity-to-entity relationships based on co-occurrence
        entity_edges = self._create_entity_relationships(entity_nodes, edges)
        edges.extend(entity_edges)

        # Deduplicate edges
        edges = self._deduplicate_edges(edges)

        logger.info(f"Extracted {len(entity_nodes)} unique entities, {len(edges)} edges")
        return entity_nodes, edges

    def _extract_entities_llm(self, node: Node) -> list[dict]:
        """Extract entities from a single node using LLM."""
        if not self.llm_client:
            return []

        system_prompt = """You are an expert at extracting named entities from Apple SEC filings.
Your task is to identify important entities in financial text.

Entity Types:
- COMPANY: Companies (Apple subsidiaries, suppliers, competitors, partners)
- PRODUCT: Products and services (iPhone, Mac, iPad, Apple Watch, Services, AppleCare)
- SEGMENT: Business or geographic segments (Americas, Europe, Greater China, Japan, Rest of Asia Pacific)
- PERSON: Key executives or board members mentioned by name
- FINANCIAL_METRIC: Specific financial metrics (Revenue, Net Income, Gross Margin, EPS)
- RISK_FACTOR: Identified business risks
- REGULATION: Laws, regulations, accounting standards (GAAP, ASC 606, GDPR)

For each entity, output a JSON object with:
- "name": The entity name (use canonical names, e.g., "iPhone" not "iPhones")
- "type": One of the entity types above
- "context": Brief context (1 sentence) about the entity from the text

Output a JSON array. If no entities found, output [].
Only extract clearly identifiable entities, not generic terms."""

        prompt = f"""Extract entities from this Apple SEC filing text:

---
{node.text[:3000]}
---

Output entities as a JSON array:"""

        try:
            response = self.llm_client.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.1,
            )

            # Parse JSON from response
            import json
            start = response.find("[")
            end = response.rfind("]") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                entities = json.loads(json_str)
                return entities if isinstance(entities, list) else []

            return []

        except Exception as e:
            logger.debug(f"Entity extraction parse error: {e}")
            return []

    def _create_entity_relationships(
        self,
        entity_nodes: list[Node],
        mention_edges: list[Edge],
    ) -> list[Edge]:
        """Create relationships between entities that co-occur in documents."""
        edges = []

        # Build co-occurrence map: which entities appear together in nodes
        node_entities: dict[str, set[str]] = {}  # source_node_id -> set of entity_ids

        for edge in mention_edges:
            if edge.edge_type == EdgeType.MENTIONS_ENTITY:
                source = edge.source_id
                target = edge.target_id
                if source not in node_entities:
                    node_entities[source] = set()
                node_entities[source].add(target)

        # Create edges between entities that co-occur
        entity_pairs_seen = set()

        for source_node, entities in node_entities.items():
            entities_list = list(entities)
            for i, ent1 in enumerate(entities_list):
                for ent2 in entities_list[i+1:]:
                    pair_key = tuple(sorted([ent1, ent2]))
                    if pair_key not in entity_pairs_seen:
                        entity_pairs_seen.add(pair_key)

                        edge = self._create_edge(
                            source_id=ent1,
                            target_id=ent2,
                            edge_type=EdgeType.ENTITY_RELATED_TO,
                            confidence=0.70,
                            evidence=f"Co-occur in document section",
                            algorithm="co_occurrence",
                        )
                        edges.append(edge)

        return edges

    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """
        Discover edges (implements BaseExpert interface).
        Note: For entity extraction, use extract_entities_from_nodes() instead.
        """
        # This method creates edges between existing nodes and entities
        entity_nodes = [n for n in nodes if n.type == NodeType.ENTITY]
        text_nodes = [n for n in nodes if n.type in [NodeType.TEXT_SECTION, NodeType.NOTE]]

        edges = []

        # Link text nodes to entities based on text matching
        for entity in entity_nodes:
            entity_name = entity.text.split(" (")[0].lower()

            for text_node in text_nodes:
                if entity_name in text_node.text.lower():
                    edge = self._create_edge(
                        source_id=text_node.id,
                        target_id=entity.id,
                        edge_type=EdgeType.MENTIONS_ENTITY,
                        confidence=0.80,
                        evidence=f"Text contains '{entity_name}'",
                        algorithm="text_match",
                    )
                    edges.append(edge)

        edges = self._deduplicate_edges(edges)
        self.log_stats(edges)
        return edges


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Test entity extraction
    extractor = EntityExtractor()

    if extractor.llm_client and extractor.llm_client.is_available():
        test_node = Node(
            id="test_TS_001",
            type=NodeType.TEXT_SECTION,
            text="""
            Apple Inc. reported strong iPhone revenue growth in Greater China and the Americas.
            Tim Cook, CEO, noted that Services revenue including AppleCare and Apple Music
            contributed significantly to gross margin improvements. The Company faces risks
            related to GDPR compliance in Europe and supply chain concentration in China.
            Revenue increased by $5 billion compared to the prior year period.
            """,
            metadata=NodeMetadata(
                filing_id="AAPL-10K-FY2024",
                period="FY2024",
            ),
        )

        entity_nodes, edges = extractor.extract_entities_from_nodes([test_node], {})

        logger.info(f"\nExtracted {len(entity_nodes)} entities:")
        for node in entity_nodes:
            logger.info(f"  {node.text} ({node.metadata.entity_type})")

        logger.info(f"\nCreated {len(edges)} edges")
    else:
        logger.warning("vLLM server not available. Start with: ./scripts/start_vllm.sh")
