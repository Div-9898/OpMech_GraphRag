"""Graph Builder for orchestrating the MoE graph construction."""

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts import get_all_experts, get_expert, EntityExtractor
from src.graph.connectivity import ConnectivityEnforcer
from src.graph.neo4j_client import Neo4jClient, get_neo4j_client
from src.models import Edge, GraphStats, Node


class GraphBuilder:
    """
    Orchestrates the construction of the knowledge graph.

    1. Runs all experts to discover edges
    2. Merges and deduplicates edges
    3. Enforces connectivity
    4. Exports to Neo4j
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient = None,
        expert_config: dict[str, Any] = None,
    ):
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.expert_config = expert_config or {}
        self.connectivity_enforcer = ConnectivityEnforcer()

    def build_graph(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
        experts: list[str] = None,
        use_llm: bool = False,
        extract_entities: bool = False,
    ) -> tuple[list[Node], list[Edge], GraphStats]:
        """
        Build the knowledge graph from nodes and embeddings.

        Args:
            nodes: List of all nodes
            embeddings: Dictionary mapping node_id -> embedding
            experts: List of expert names to run (None = all)
            use_llm: Whether to use LLM for causal extraction
            extract_entities: Whether to use LLM for entity extraction

        Returns:
            Tuple of (all nodes including entities, all edges, graph statistics)
        """
        logger.info(f"Building graph from {len(nodes)} nodes...")

        # Step 0: Entity extraction using LLM (if enabled)
        entity_nodes = []
        entity_edges = []
        if extract_entities:
            logger.info("Running LLM entity extraction...")
            entity_extractor = EntityExtractor()
            if entity_extractor.llm_client and entity_extractor.llm_client.is_available():
                entity_nodes, entity_edges = entity_extractor.extract_entities_from_nodes(
                    nodes, embeddings
                )
                logger.info(f"Extracted {len(entity_nodes)} entities, {len(entity_edges)} entity edges")
                # Add entities to nodes list
                nodes = nodes + entity_nodes
            else:
                logger.warning("LLM not available for entity extraction - skipping")

        # Step 1: Run experts to discover edges
        all_edges = self._run_experts(nodes, embeddings, experts, use_llm)
        all_edges.extend(entity_edges)
        logger.info(f"Discovered {len(all_edges)} edges from experts")

        # Step 2: Merge and deduplicate edges
        all_edges = self._deduplicate_edges(all_edges)
        logger.info(f"After deduplication: {len(all_edges)} edges")

        # Step 3: Verify connectivity and add bridges if needed
        stats_before = self.connectivity_enforcer.verify_connectivity(nodes, all_edges)
        logger.info(f"Connectivity before bridges: {stats_before['connected_components']} components")

        if stats_before["connected_components"] > 1:
            bridge_edges = self.connectivity_enforcer.enforce_connectivity(
                nodes, all_edges, embeddings
            )
            all_edges.extend(bridge_edges)
            logger.info(f"Added {len(bridge_edges)} bridge edges")

        # Step 4: Final verification
        stats_after = self.connectivity_enforcer.verify_connectivity(nodes, all_edges)
        logger.info(f"Final connectivity: {stats_after['connected_components']} components")

        # Create GraphStats object
        edge_type_counts = {}
        expert_counts = {}
        for edge in all_edges:
            edge_type = edge.edge_type.value if hasattr(edge.edge_type, 'value') else str(edge.edge_type)
            edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
            expert_counts[edge.expert] = expert_counts.get(edge.expert, 0) + 1

        node_type_counts = {}
        for node in nodes:
            node_type = node.type.value if hasattr(node.type, 'value') else str(node.type)
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

        graph_stats = GraphStats(
            connected_components=stats_after["connected_components"],
            is_connected=stats_after["is_connected"],
            total_nodes=len(nodes),
            total_edges=len(all_edges),
            isolated_nodes=stats_after["isolated_nodes"],
            average_degree=stats_after["average_degree"],
            max_degree=stats_after["max_degree"],
            min_degree=stats_after["min_degree"],
            largest_component_size=stats_after["largest_component_size"],
            bridge_edges=stats_after["bridge_edges"],
            nodes_by_type=node_type_counts,
            edges_by_expert=expert_counts,
            edges_by_type=edge_type_counts,
        )

        return nodes, all_edges, graph_stats

    def _run_experts(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
        expert_names: list[str] = None,
        use_llm: bool = False,
    ) -> list[Edge]:
        """Run all experts to discover edges."""
        all_edges = []

        # Determine which experts to run
        if expert_names:
            experts = [get_expert(name, self.expert_config) for name in expert_names]
        else:
            experts = get_all_experts(self.expert_config)

        # Configure LLM usage for all experts that support it
        for expert in experts:
            if hasattr(expert, 'use_llm'):
                expert.use_llm = use_llm
                if use_llm:
                    logger.debug(f"LLM mode enabled for {expert.name}")

        # Run each expert
        for expert in experts:
            logger.info(f"Running expert: {expert.name}")
            try:
                edges = expert.discover_edges(nodes, embeddings)
                all_edges.extend(edges)
                logger.info(f"  {expert.name}: {len(edges)} edges")
            except Exception as e:
                logger.error(f"  {expert.name} failed: {e}")

        return all_edges

    def _deduplicate_edges(self, edges: list[Edge]) -> list[Edge]:
        """Remove duplicate edges, keeping the one with highest confidence."""
        edge_map: dict[str, Edge] = {}

        for edge in edges:
            # Create a normalized key (order-independent for undirected comparison)
            key = tuple(sorted([edge.source_id, edge.target_id])) + (edge.edge_type,)

            if key not in edge_map or edge.confidence > edge_map[key].confidence:
                edge_map[key] = edge

        return list(edge_map.values())

    def export_to_neo4j(
        self,
        nodes: list[Node],
        edges: list[Edge],
        clear_existing: bool = True,
    ) -> None:
        """Export nodes and edges to Neo4j."""
        logger.info("Exporting to Neo4j...")

        if clear_existing:
            self.neo4j_client.clear_database()

        self.neo4j_client.create_indexes()
        self.neo4j_client.insert_nodes(nodes)
        self.neo4j_client.insert_edges(edges)

        logger.info("Export to Neo4j complete")

    def save_graph(
        self,
        nodes: list[Node],
        edges: list[Edge],
        stats: GraphStats,
        output_dir: Path,
    ) -> None:
        """Save graph to JSON files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save nodes
        nodes_path = output_dir / "nodes.jsonl"
        with open(nodes_path, "w") as f:
            for node in nodes:
                f.write(node.model_dump_json() + "\n")
        logger.info(f"Saved {len(nodes)} nodes to {nodes_path}")

        # Save edges
        edges_path = output_dir / "edges.jsonl"
        with open(edges_path, "w") as f:
            for edge in edges:
                f.write(edge.model_dump_json() + "\n")
        logger.info(f"Saved {len(edges)} edges to {edges_path}")

        # Save stats
        stats_path = output_dir / "stats.json"
        stats_path.write_text(stats.model_dump_json(indent=2))
        logger.info(f"Saved stats to {stats_path}")

    def load_graph(self, input_dir: Path) -> tuple[list[Node], list[Edge], GraphStats]:
        """Load graph from JSON files."""
        input_dir = Path(input_dir)

        # Load nodes
        nodes = []
        nodes_path = input_dir / "nodes.jsonl"
        if nodes_path.exists():
            with open(nodes_path, "r") as f:
                for line in f:
                    nodes.append(Node.model_validate_json(line))

        # Load edges
        edges = []
        edges_path = input_dir / "edges.jsonl"
        if edges_path.exists():
            with open(edges_path, "r") as f:
                for line in f:
                    edges.append(Edge.model_validate_json(line))

        # Load stats
        stats = None
        stats_path = input_dir / "stats.json"
        if stats_path.exists():
            stats = GraphStats.model_validate_json(stats_path.read_text())

        logger.info(f"Loaded {len(nodes)} nodes and {len(edges)} edges")
        return nodes, edges, stats


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Test with sample data
    from src.models import NodeType

    test_nodes = [
        Node(
            id="TS_001",
            type=NodeType.TEXT_SECTION,
            text="Revenue increased due to strong iPhone sales. See Note 3 for details.",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "section": "Item 7"},
        ),
        Node(
            id="TS_002",
            type=NodeType.TEXT_SECTION,
            text="Services segment showed growth driven by App Store and iCloud subscriptions.",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "section": "Item 7"},
        ),
        Node(
            id="NT_003",
            type=NodeType.NOTE,
            text="Note 3 - Revenue Recognition. The Company recognizes revenue when control transfers.",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "note_number": 3},
        ),
        Node(
            id="FL_001",
            type=NodeType.FINANCIAL_LINE,
            text="Total Revenue: $383.3B",
            metadata={"filing_id": "AAPL-10K-2024", "period": "FY2024", "xbrl_tag": "us-gaap:Revenues", "value": 383300000000},
        ),
    ]

    # Create embeddings
    np.random.seed(42)
    embeddings = {node.id: np.random.randn(768) for node in test_nodes}
    for k in embeddings:
        embeddings[k] = embeddings[k] / np.linalg.norm(embeddings[k])

    # Build graph
    builder = GraphBuilder()
    edges, stats = builder.build_graph(test_nodes, embeddings, use_llm=False)

    logger.info(f"\nGraph Statistics:")
    logger.info(f"  Nodes: {stats.total_nodes}")
    logger.info(f"  Edges: {stats.total_edges}")
    logger.info(f"  Connected: {stats.is_connected}")
    logger.info(f"  Components: {stats.connected_components}")
    logger.info(f"  Edges by expert: {stats.edges_by_expert}")
