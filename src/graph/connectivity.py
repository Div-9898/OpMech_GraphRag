"""Connectivity Enforcer for ensuring single connected component."""

from collections import defaultdict
from typing import Any

import numpy as np
from loguru import logger

from src.config import settings
from src.experts.base import cosine_similarity
from src.models import Edge, EdgeType, Node


class ConnectivityEnforcer:
    """
    Ensures the graph is fully connected (single component).
    Adds minimal BRIDGE edges to connect disconnected components.
    """

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.bridge_threshold = self.config.get(
            "bridge_threshold",
            settings.bridge_similarity_threshold,
        )

    def enforce_connectivity(
        self,
        nodes: list[Node],
        edges: list[Edge],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        """
        Add bridge edges to ensure single connected component.

        Algorithm:
        1. Find all connected components
        2. While more than 1 component exists:
           a. Find best edge to connect two components
           b. Add edge and merge components
        3. Return list of added bridge edges

        Args:
            nodes: List of all nodes
            edges: List of existing edges
            embeddings: Dictionary mapping node_id -> embedding

        Returns:
            List of BRIDGE edges added to ensure connectivity
        """
        logger.info("Enforcing graph connectivity...")

        # Build adjacency list
        adj = defaultdict(set)
        for edge in edges:
            adj[edge.source_id].add(edge.target_id)
            adj[edge.target_id].add(edge.source_id)

        # Find connected components
        node_ids = {node.id for node in nodes}
        components = self._find_components(node_ids, adj)

        logger.info(f"Found {len(components)} connected components")

        if len(components) <= 1:
            logger.info("Graph is already connected")
            return []

        # Log component sizes
        component_sizes = sorted([len(c) for c in components], reverse=True)
        logger.info(f"Component sizes: {component_sizes[:10]}{'...' if len(component_sizes) > 10 else ''}")

        bridge_edges = []
        iteration = 0

        while len(components) > 1:
            iteration += 1
            best_edge = None
            best_score = 0.0
            best_pair = None

            # Find best edge to connect any two components
            # Optimize by only comparing largest components first
            components.sort(key=len, reverse=True)

            for i, comp1 in enumerate(components[:min(10, len(components))]):
                for j, comp2 in enumerate(components[i + 1:min(20, len(components))], i + 1):
                    # Sample nodes from each component for efficiency
                    sample1 = list(comp1)[:50]
                    sample2 = list(comp2)[:50]

                    for node1_id in sample1:
                        if node1_id not in embeddings:
                            continue

                        for node2_id in sample2:
                            if node2_id not in embeddings:
                                continue

                            sim = cosine_similarity(
                                embeddings[node1_id],
                                embeddings[node2_id],
                            )

                            if sim > best_score:
                                best_score = sim
                                best_edge = Edge(
                                    id=f"{node1_id}__BRIDGE__{node2_id}",
                                    source_id=node1_id,
                                    target_id=node2_id,
                                    edge_type=EdgeType.BRIDGE,
                                    confidence=float(sim),
                                    expert="ConnectivityEnforcer",
                                    evidence=f"Bridge edge (similarity: {sim:.3f})",
                                )
                                best_pair = (i, j)

            if best_edge:
                # Check if we need to force connection below threshold
                if best_score < self.bridge_threshold:
                    logger.warning(
                        f"Forcing bridge edge with low similarity: {best_score:.3f}"
                    )
                    best_edge.metadata.forced = True
                    best_edge.confidence = max(0.5, best_score)

                bridge_edges.append(best_edge)

                # Store sizes before merging
                size1 = len(components[best_pair[0]])
                size2 = len(components[best_pair[1]])

                # Merge components
                merged = components[best_pair[0]] | components[best_pair[1]]
                components = [
                    c for idx, c in enumerate(components)
                    if idx not in best_pair
                ]
                components.append(merged)

                logger.debug(
                    f"Iteration {iteration}: Merged components "
                    f"({size1} + {size2} nodes), "
                    f"similarity: {best_score:.3f}, "
                    f"remaining components: {len(components)}"
                )
            else:
                logger.error("Could not find any edge to connect components!")
                break

        logger.info(f"Added {len(bridge_edges)} bridge edges to ensure connectivity")
        return bridge_edges

    def _find_components(
        self,
        node_ids: set[str],
        adj: dict[str, set[str]],
    ) -> list[set[str]]:
        """Find connected components using BFS."""
        visited = set()
        components = []

        for node_id in node_ids:
            if node_id in visited:
                continue

            # BFS to find component
            component = set()
            queue = [node_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue

                visited.add(current)
                component.add(current)

                # Add unvisited neighbors
                for neighbor in adj.get(current, []):
                    if neighbor not in visited and neighbor in node_ids:
                        queue.append(neighbor)

            if component:
                components.append(component)

        return components

    def verify_connectivity(
        self,
        nodes: list[Node],
        edges: list[Edge],
    ) -> dict[str, Any]:
        """
        Verify graph connectivity and return metrics.

        Returns:
            Dictionary with connectivity statistics
        """
        # Build adjacency list
        adj = defaultdict(set)
        for edge in edges:
            adj[edge.source_id].add(edge.target_id)
            adj[edge.target_id].add(edge.source_id)

        node_ids = {node.id for node in nodes}
        components = self._find_components(node_ids, adj)

        # Find isolated nodes (degree 0)
        isolated = [
            nid for nid in node_ids
            if nid not in adj or len(adj[nid]) == 0
        ]

        # Calculate degree statistics
        degrees = [len(adj.get(nid, set())) for nid in node_ids]

        # Count bridge edges
        bridge_count = len([e for e in edges if e.edge_type == EdgeType.BRIDGE])

        return {
            "connected_components": len(components),
            "is_connected": len(components) == 1,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "isolated_nodes": len(isolated),
            "isolated_node_ids": isolated[:10],  # First 10 for debugging
            "average_degree": sum(degrees) / len(degrees) if degrees else 0,
            "max_degree": max(degrees) if degrees else 0,
            "min_degree": min(degrees) if degrees else 0,
            "largest_component_size": max(len(c) for c in components) if components else 0,
            "component_sizes": sorted([len(c) for c in components], reverse=True)[:10],
            "bridge_edges": bridge_count,
        }


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with sample data
    enforcer = ConnectivityEnforcer()

    # Create test nodes in two disconnected components
    test_nodes = [
        # Component 1
        Node(id="A1", type="TEXT_SECTION", text="Component A node 1",
             metadata={"filing_id": "test", "period": "FY2024"}),
        Node(id="A2", type="TEXT_SECTION", text="Component A node 2",
             metadata={"filing_id": "test", "period": "FY2024"}),
        Node(id="A3", type="TEXT_SECTION", text="Component A node 3",
             metadata={"filing_id": "test", "period": "FY2024"}),
        # Component 2
        Node(id="B1", type="TEXT_SECTION", text="Component B node 1",
             metadata={"filing_id": "test", "period": "FY2024"}),
        Node(id="B2", type="TEXT_SECTION", text="Component B node 2",
             metadata={"filing_id": "test", "period": "FY2024"}),
        # Isolated node
        Node(id="C1", type="TEXT_SECTION", text="Isolated node",
             metadata={"filing_id": "test", "period": "FY2024"}),
    ]

    test_edges = [
        Edge(id="A1__A2", source_id="A1", target_id="A2",
             edge_type=EdgeType.SEMANTICALLY_SIMILAR, confidence=0.9,
             expert="test", evidence="test"),
        Edge(id="A2__A3", source_id="A2", target_id="A3",
             edge_type=EdgeType.SEMANTICALLY_SIMILAR, confidence=0.85,
             expert="test", evidence="test"),
        Edge(id="B1__B2", source_id="B1", target_id="B2",
             edge_type=EdgeType.SEMANTICALLY_SIMILAR, confidence=0.88,
             expert="test", evidence="test"),
    ]

    # Create similar embeddings for nodes we want to bridge
    np.random.seed(42)
    base_emb = np.random.randn(768)
    embeddings = {
        "A1": base_emb + 0.1 * np.random.randn(768),
        "A2": base_emb + 0.1 * np.random.randn(768),
        "A3": base_emb + 0.1 * np.random.randn(768),
        "B1": base_emb + 0.15 * np.random.randn(768),  # Similar to A
        "B2": base_emb + 0.2 * np.random.randn(768),
        "C1": np.random.randn(768),  # Different
    }

    # Normalize
    for k in embeddings:
        embeddings[k] = embeddings[k] / np.linalg.norm(embeddings[k])

    # Verify initial connectivity
    stats = enforcer.verify_connectivity(test_nodes, test_edges)
    logger.info(f"Initial connectivity: {stats}")

    # Enforce connectivity
    bridge_edges = enforcer.enforce_connectivity(test_nodes, test_edges, embeddings)

    logger.info(f"\nAdded {len(bridge_edges)} bridge edges:")
    for edge in bridge_edges:
        logger.info(f"  {edge.source_id} -> {edge.target_id} (conf: {edge.confidence:.3f})")

    # Verify final connectivity
    all_edges = test_edges + bridge_edges
    stats = enforcer.verify_connectivity(test_nodes, all_edges)
    logger.info(f"\nFinal connectivity: {stats}")
