"""Knowledge Graph Interface for OpMech-GraphRAG.

Provides confidence-weighted traversal of the Neo4j knowledge graph
built by the MoE Graph Builder.
"""

import heapq
import os
from typing import Dict, List, Tuple, Optional

import numpy as np
from loguru import logger
from neo4j import GraphDatabase

from src.opmech.data_classes import Edge, Node, TraversedNode
from src.opmech.edge_scoring import EdgeScorer, TraversalContext, EdgeScore


# Edge-type specific confidence thresholds
# Dense edge types need higher thresholds to prevent traversal explosion
EDGE_CONFIDENCE_OVERRIDES = {
    "SEMANTICALLY_SIMILAR": 0.90,    # Very dense, require high confidence
    "ENTITY_RELATED_TO": 0.85,       # Dense, require high confidence
    "DISCUSSES": 0.80,               # Very dense (avg 38 out-degree), need high threshold
    "MENTIONS_ENTITY": 0.85,         # Dense (avg 27.5 out-degree)
    "TEMPORAL_NEXT": 0.60,           # Sparse, can be lower (XBRL-derived)
    "EXPLAINS_LINE_ITEM": 0.70,      # Moderate density
    "CAUSED_BY": 0.70,               # Sparse
    "LEADS_TO": 0.70,                # Sparse
    "REFERS_TO": 0.70,               # Sparse
}

# BUG 5 FIX: Semantic expansion for concept queries
# Maps high-level concepts to specific XBRL terms and financial metrics
SEMANTIC_CONCEPT_EXPANSION = {
    # Growth-related terms
    "growth": ["Revenue", "NetSales", "TotalRevenue", "RevenueNet", "SalesRevenue"],
    "sustainable": ["Revenue", "NetIncome", "OperatingIncome", "GrossProfit"],
    "sustainability": ["Revenue", "NetIncome", "OperatingIncome", "GrossProfit"],

    # Profitability-related terms
    "profitability": ["GrossProfit", "OperatingIncome", "NetIncome", "GrossProfitMargin", "OperatingMargin"],
    "profit": ["GrossProfit", "OperatingIncome", "NetIncome", "ProfitLoss"],
    "margin": ["GrossProfit", "GrossMargin", "OperatingMargin", "NetMargin", "CostOfGoodsSold"],
    "profitable": ["GrossProfit", "OperatingIncome", "NetIncome"],

    # Segment-related terms
    "segment": ["SegmentRevenue", "ProductRevenue", "ServiceRevenue", "GeographicRevenue"],
    "concerning": ["Impairment", "WriteOff", "Restructuring", "Decline", "Loss"],
    "risk": ["Impairment", "WriteOff", "Restructuring", "LongTermDebt", "ContingentLiability"],

    # Performance-related terms
    "performance": ["Revenue", "OperatingIncome", "NetIncome", "EarningsPerShare"],
    "operating": ["OperatingIncome", "OperatingExpenses", "OperatingMargin", "CostOfSales"],

    # Balance sheet terms
    "balance sheet": ["TotalAssets", "TotalLiabilities", "StockholdersEquity", "Cash", "Debt"],
    "assets": ["TotalAssets", "CurrentAssets", "PropertyPlantEquipment", "Goodwill"],
    "liabilities": ["TotalLiabilities", "CurrentLiabilities", "LongTermDebt", "AccountsPayable"],
    "debt": ["LongTermDebt", "ShortTermDebt", "TotalDebt", "DebtToEquity"],
    "equity": ["StockholdersEquity", "RetainedEarnings", "CommonStock"],
    "cash": ["CashAndCashEquivalents", "FreeCashFlow", "OperatingCashFlow"],

    # Change-related terms
    "change": ["Revenue", "NetIncome", "OperatingIncome"],
    "changed": ["Revenue", "NetIncome", "OperatingIncome"],
    "driving": ["Revenue", "CostOfSales", "OperatingExpenses", "NetIncome"],
    "worried": ["LongTermDebt", "CurrentRatio", "DebtToEquity", "Impairment"],
    "investors": ["EarningsPerShare", "Dividends", "StockholdersEquity", "NetIncome"],
}


class KnowledgeGraphInterface:
    """Interface to Neo4j knowledge graph with confidence-weighted operations."""

    # Traversal caps to prevent explosion
    DEFAULT_MAX_NODES_TOTAL = 150
    DEFAULT_MAX_EDGES_TOTAL = 400

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password123"
    ):
        """
        Initialize the graph interface.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.embeddings = self._load_embeddings()
        logger.info(f"Loaded {len(self.embeddings)} embeddings")

    def _load_embeddings(self) -> Dict[str, np.ndarray]:
        """Load pre-computed FinBERT embeddings from data/embeddings/."""
        embeddings = {}
        emb_dir = "data/embeddings"

        if not os.path.exists(emb_dir):
            logger.warning(f"Embeddings directory not found: {emb_dir}")
            return embeddings

        for filing_dir in os.listdir(emb_dir):
            filing_path = os.path.join(emb_dir, filing_dir)
            if os.path.isdir(filing_path):
                for emb_file in os.listdir(filing_path):
                    if emb_file.endswith('.npz'):
                        npz_path = os.path.join(filing_path, emb_file)
                        try:
                            data = np.load(npz_path)
                            for node_id in data.files:
                                embeddings[node_id] = data[node_id]
                        except Exception as e:
                            logger.warning(f"Failed to load {npz_path}: {e}")

        return embeddings

    def search_by_type(
        self,
        query_embedding: np.ndarray,
        node_types: List[str],
        top_k: int = 5
    ) -> List[Node]:
        """
        Search for nodes by type using embedding similarity.

        Args:
            query_embedding: Query embedding vector
            node_types: List of node types to search
            top_k: Number of top results to return

        Returns:
            List of top-k most similar nodes of specified types
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n:Node)
                WHERE n.type IN $types
                RETURN n.id as id, n.type as type, n.text as text,
                       n.filing_id as filing_id, n.period as period,
                       n.section as section, n.xbrl_tag as xbrl_tag,
                       n.value as value
            """, types=node_types)

            candidates = []
            for record in result:
                node_id = record['id']
                if node_id in self.embeddings:
                    emb = self.embeddings[node_id]

                    # Compute cosine similarity
                    norm_q = np.linalg.norm(query_embedding)
                    norm_e = np.linalg.norm(emb)

                    if norm_q > 0 and norm_e > 0:
                        similarity = np.dot(query_embedding, emb) / (norm_q * norm_e)
                    else:
                        similarity = 0.0

                    candidates.append((similarity, Node(
                        id=node_id,
                        type=record['type'],
                        text=record['text'] or "",
                        metadata={
                            'filing_id': record['filing_id'],
                            'period': record['period'],
                            'section': record['section'],
                            'xbrl_tag': record['xbrl_tag'],
                            'value': record['value']
                        },
                        embedding=emb
                    )))

            # Sort by similarity and return top_k
            candidates.sort(key=lambda x: x[0], reverse=True)
            return [node for _, node in candidates[:top_k]]

    def traverse_with_confidence(
        self,
        seed_ids: List[str],
        edge_types: List[str],
        hops: int,
        max_per_hop: int,
        min_confidence: float,
        confidence_decay: float = 0.9,
        max_nodes_total: int = None,
        max_edges_total: int = None,
    ) -> Tuple[List[TraversedNode], List[Edge]]:
        """
        CONFIDENCE-WEIGHTED multi-hop graph traversal with CAPS.

        KEY FEATURES:
            1. Edges are sorted by confidence (prefer high-confidence paths)
            2. Path confidence is tracked (product of edge confidences)
            3. Hard caps on total nodes/edges to prevent explosion
            4. Edge-type specific confidence thresholds

        Path Confidence Formula:
            path_conf(n) = ∏(edge.confidence * decay^hop) for edges in path to n

        Args:
            seed_ids: Starting node IDs
            edge_types: Allowed edge types for traversal
            hops: Maximum traversal depth
            max_per_hop: Maximum nodes to expand per hop
            min_confidence: Minimum edge confidence to traverse
            confidence_decay: Decay factor for path confidence (default 0.9)
            max_nodes_total: Hard cap on total nodes (default 150)
            max_edges_total: Hard cap on total edges (default 400)

        Returns:
            (traversed_nodes, edges) - nodes with path confidence, all edges used
        """
        # Apply default caps
        if max_nodes_total is None:
            max_nodes_total = self.DEFAULT_MAX_NODES_TOTAL
        if max_edges_total is None:
            max_edges_total = self.DEFAULT_MAX_EDGES_TOTAL

        # Priority queue: (-path_confidence, counter, node_id, hop_distance, incoming_edge)
        # Negative because heapq is min-heap, we want max confidence first
        # Counter is used to break ties and avoid comparing Edge objects
        frontier = []
        counter = 0
        for seed_id in seed_ids:
            heapq.heappush(frontier, (-1.0, counter, seed_id, 0, None))
            counter += 1

        visited = {}  # node_id -> (path_confidence, hop_distance, incoming_edge)
        all_edges = []

        with self.driver.session() as session:
            while frontier:
                # CHECK CAPS - prevent traversal explosion
                if len(visited) >= max_nodes_total:
                    logger.debug(f"Hit max_nodes_total cap ({max_nodes_total})")
                    break
                if len(all_edges) >= max_edges_total:
                    logger.debug(f"Hit max_edges_total cap ({max_edges_total})")
                    break

                neg_conf, _, node_id, hop_dist, incoming_edge = heapq.heappop(frontier)
                path_conf = -neg_conf

                # Skip if already visited with higher confidence
                if node_id in visited:
                    if visited[node_id][0] >= path_conf:
                        continue

                visited[node_id] = (path_conf, hop_dist, incoming_edge)

                # Stop if max hops reached
                if hop_dist >= hops:
                    continue

                # Build edge-type specific confidence thresholds in Cypher
                # This is more efficient than filtering in Python
                edge_result = session.run("""
                    MATCH (source:Node {id: $node_id})-[r]->(target:Node)
                    WHERE (r.type IN $edge_types OR type(r) IN $edge_types)
                    AND (
                        (COALESCE(r.type, type(r)) = 'SEMANTICALLY_SIMILAR' AND COALESCE(r.confidence, 0.5) >= 0.90)
                        OR (COALESCE(r.type, type(r)) = 'ENTITY_RELATED_TO' AND COALESCE(r.confidence, 0.5) >= 0.85)
                        OR (COALESCE(r.type, type(r)) = 'DISCUSSES' AND COALESCE(r.confidence, 0.5) >= 0.80)
                        OR (COALESCE(r.type, type(r)) = 'MENTIONS_ENTITY' AND COALESCE(r.confidence, 0.5) >= 0.85)
                        OR (NOT COALESCE(r.type, type(r)) IN ['SEMANTICALLY_SIMILAR', 'ENTITY_RELATED_TO', 'DISCUSSES', 'MENTIONS_ENTITY']
                            AND COALESCE(r.confidence, 0.5) >= $min_conf)
                    )
                    RETURN target.id as target_id,
                           COALESCE(r.type, type(r)) as edge_type,
                           COALESCE(r.confidence, 0.5) as confidence,
                           r.expert as expert,
                           r.evidence as evidence,
                           target.type as target_type,
                           target.text as target_text,
                           target.filing_id as target_filing_id,
                           target.period as target_period,
                           target.section as target_section,
                           target.xbrl_tag as target_xbrl_tag,
                           target.value as target_value
                    ORDER BY COALESCE(r.confidence, 0.5) DESC
                    LIMIT $limit
                """,
                    node_id=node_id,
                    edge_types=edge_types,
                    min_conf=min_confidence,
                    limit=max_per_hop
                )

                for record in edge_result:
                    # Check edge cap again before adding
                    if len(all_edges) >= max_edges_total:
                        break

                    target_id = record['target_id']
                    edge_conf = record['confidence'] or 0.5

                    # Create edge object
                    edge = Edge(
                        source_id=node_id,
                        target_id=target_id,
                        type=record['edge_type'],
                        confidence=edge_conf,
                        expert=record['expert'] or "unknown",
                        evidence=record['evidence'] or ""
                    )
                    all_edges.append(edge)

                    # Calculate new path confidence with decay
                    # decay^hop prevents long paths from being overly penalized
                    decay_factor = confidence_decay ** (hop_dist + 1)
                    new_path_conf = path_conf * edge_conf * decay_factor

                    # Add to frontier if not visited or better path found
                    if target_id not in visited or visited[target_id][0] < new_path_conf:
                        heapq.heappush(frontier, (-new_path_conf, counter, target_id, hop_dist + 1, edge))
                        counter += 1

            # Build TraversedNode objects
            traversed_nodes = []
            for node_id, (path_conf, hop_dist, incoming_edge) in visited.items():
                # Fetch node details
                node_result = session.run("""
                    MATCH (n:Node {id: $node_id})
                    RETURN n.id as id, n.type as type, n.text as text,
                           n.filing_id as filing_id, n.period as period,
                           n.section as section, n.xbrl_tag as xbrl_tag,
                           n.value as value
                """, node_id=node_id)

                record = node_result.single()
                if record:
                    node = Node(
                        id=record['id'],
                        type=record['type'],
                        text=record['text'] or "",
                        metadata={
                            'filing_id': record['filing_id'],
                            'period': record['period'],
                            'section': record['section'],
                            'xbrl_tag': record['xbrl_tag'],
                            'value': record['value']
                        }
                    )

                    traversed_nodes.append(TraversedNode(
                        node=node,
                        path_confidence=path_conf,
                        incoming_edge=incoming_edge,
                        hop_distance=hop_dist
                    ))

        return traversed_nodes, all_edges

    def get_node_by_id(self, node_id: str) -> Node | None:
        """
        Get a single node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node object or None if not found
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n:Node {id: $node_id})
                RETURN n.id as id, n.type as type, n.text as text,
                       n.filing_id as filing_id, n.period as period,
                       n.section as section, n.xbrl_tag as xbrl_tag,
                       n.value as value
            """, node_id=node_id)

            record = result.single()
            if record:
                return Node(
                    id=record['id'],
                    type=record['type'],
                    text=record['text'] or "",
                    metadata={
                        'filing_id': record['filing_id'],
                        'period': record['period'],
                        'section': record['section'],
                        'xbrl_tag': record['xbrl_tag'],
                        'value': record['value']
                    },
                    embedding=self.embeddings.get(record['id'])
                )
            return None

    def find_revenue_nodes(self, period_filter: str = None, limit: int = 10) -> List[Node]:
        """
        Find FINANCIAL_LINE nodes with revenue XBRL tags.

        This is a direct query to find revenue data without relying on embeddings.

        Args:
            period_filter: Optional period filter (e.g., "FY2023", "2023")
            limit: Maximum nodes to return

        Returns:
            List of revenue nodes sorted by value
        """
        with self.driver.session() as session:
            period_clause = ""
            if period_filter:
                period_clause = f"AND n.period CONTAINS '{period_filter}'"

            result = session.run(f"""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND (
                    toLower(n.xbrl_tag) CONTAINS 'revenue'
                    OR toLower(n.xbrl_tag) CONTAINS 'sales'
                )
                AND n.value IS NOT NULL
                {period_clause}
                RETURN n.id AS id, n.type AS type, n.text AS text,
                       n.filing_id AS filing_id, n.period AS period,
                       n.section AS section, n.xbrl_tag AS xbrl_tag,
                       n.value AS value
                ORDER BY n.value DESC
                LIMIT {limit}
            """)

            nodes = []
            for record in result:
                nodes.append(Node(
                    id=record['id'],
                    type=record['type'],
                    text=record['text'] or "",
                    metadata={
                        'filing_id': record['filing_id'],
                        'period': record['period'],
                        'section': record['section'],
                        'xbrl_tag': record['xbrl_tag'],
                        'value': record['value']
                    },
                    embedding=self.embeddings.get(record['id'])
                ))

            return nodes

    def find_nodes_by_xbrl_keyword(
        self,
        keyword: str,
        node_type: str = "FINANCIAL_LINE",
        period_filter: str = None,
        limit: int = 10
    ) -> List[Node]:
        """
        Find nodes by XBRL tag keyword.

        Args:
            keyword: Keyword to search in XBRL tag
            node_type: Node type to filter
            period_filter: Optional period filter
            limit: Maximum nodes to return

        Returns:
            List of matching nodes
        """
        with self.driver.session() as session:
            period_clause = ""
            if period_filter:
                period_clause = f"AND n.period CONTAINS '{period_filter}'"

            result = session.run(f"""
                MATCH (n:Node)
                WHERE n.type = $node_type
                AND toLower(n.xbrl_tag) CONTAINS toLower($keyword)
                {period_clause}
                RETURN n.id AS id, n.type AS type, n.text AS text,
                       n.filing_id AS filing_id, n.period AS period,
                       n.section AS section, n.xbrl_tag AS xbrl_tag,
                       n.value AS value
                ORDER BY n.value DESC
                LIMIT $limit
            """, node_type=node_type, keyword=keyword, limit=limit)

            nodes = []
            for record in result:
                nodes.append(Node(
                    id=record['id'],
                    type=record['type'],
                    text=record['text'] or "",
                    metadata={
                        'filing_id': record['filing_id'],
                        'period': record['period'],
                        'section': record['section'],
                        'xbrl_tag': record['xbrl_tag'],
                        'value': record['value']
                    },
                    embedding=self.embeddings.get(record['id'])
                ))

            return nodes

    def search_financial_by_concept(
        self,
        concepts: List[str],
        period_filter: str = None,
        limit: int = 10
    ) -> List[Node]:
        """
        Search FINANCIAL_LINE nodes by XBRL concept names.

        This method searches for nodes whose XBRL tags or labels match
        any of the provided concept names. Essential for retrieving
        margin data when queries mention financial metrics.

        Args:
            concepts: List of XBRL concept names to search (e.g., ["GrossProfit", "CostOfGoodsSold"])
            period_filter: Optional period filter (e.g., "FY2023", "2023")
            limit: Maximum nodes to return

        Returns:
            List of matching FINANCIAL_LINE nodes
        """
        with self.driver.session() as session:
            period_clause = ""
            if period_filter:
                period_clause = f"AND n.period CONTAINS '{period_filter}'"

            # Build concept matching clause
            # This matches XBRL tags that contain any of the concept names
            result = session.run(f"""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND any(concept IN $concepts WHERE
                    toLower(n.xbrl_tag) CONTAINS toLower(concept)
                    OR toLower(n.text) CONTAINS toLower(concept)
                )
                {period_clause}
                RETURN n.id AS id, n.type AS type, n.text AS text,
                       n.filing_id AS filing_id, n.period AS period,
                       n.section AS section, n.xbrl_tag AS xbrl_tag,
                       n.value AS value
                ORDER BY n.value DESC
                LIMIT $limit
            """, concepts=concepts, limit=limit)

            nodes = []
            for record in result:
                nodes.append(Node(
                    id=record['id'],
                    type=record['type'],
                    text=record['text'] or "",
                    metadata={
                        'filing_id': record['filing_id'],
                        'period': record['period'],
                        'section': record['section'],
                        'xbrl_tag': record['xbrl_tag'],
                        'value': record['value']
                    },
                    embedding=self.embeddings.get(record['id'])
                ))

            logger.debug(f"search_financial_by_concept: Found {len(nodes)} nodes for concepts {concepts[:3]}...")
            return nodes

    def search_by_type_enhanced(
        self,
        query_embedding: Optional[np.ndarray],
        node_types: List[str],
        text_query: Optional[str] = None,
        xbrl_keywords: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Node]:
        """
        Enhanced search with combined embedding and text/XBRL matching.

        For FINANCIAL_LINE nodes, also searches XBRL tags and text content.
        This ensures margin queries find actual margin data.

        Args:
            query_embedding: Query embedding vector (optional)
            node_types: List of node types to search
            text_query: Optional text to search in node content
            xbrl_keywords: Optional XBRL keywords to search
            top_k: Number of top results to return

        Returns:
            List of top-k most relevant nodes
        """
        with self.driver.session() as session:
            # Build the WHERE clause
            conditions = ["n.type IN $types"]

            if text_query:
                conditions.append("toLower(n.text) CONTAINS toLower($text_query)")

            if xbrl_keywords:
                xbrl_condition = "any(kw IN $xbrl_keywords WHERE toLower(n.xbrl_tag) CONTAINS toLower(kw))"
                conditions.append(xbrl_condition)

            where_clause = " AND ".join(conditions)

            result = session.run(f"""
                MATCH (n:Node)
                WHERE {where_clause}
                RETURN n.id as id, n.type as type, n.text as text,
                       n.filing_id as filing_id, n.period as period,
                       n.section as section, n.xbrl_tag as xbrl_tag,
                       n.value as value
            """, types=node_types, text_query=text_query or "", xbrl_keywords=xbrl_keywords or [])

            candidates = []
            for record in result:
                node_id = record['id']

                # Compute similarity if embedding available
                similarity = 0.0
                if query_embedding is not None and node_id in self.embeddings:
                    emb = self.embeddings[node_id]
                    norm_q = np.linalg.norm(query_embedding)
                    norm_e = np.linalg.norm(emb)
                    if norm_q > 0 and norm_e > 0:
                        similarity = np.dot(query_embedding, emb) / (norm_q * norm_e)

                # Boost score for XBRL keyword matches
                xbrl_boost = 0.0
                if xbrl_keywords and record.get('xbrl_tag'):
                    xbrl_tag_lower = record['xbrl_tag'].lower()
                    for kw in xbrl_keywords:
                        if kw.lower() in xbrl_tag_lower:
                            xbrl_boost = 0.3
                            break

                final_score = similarity + xbrl_boost

                candidates.append((final_score, Node(
                    id=node_id,
                    type=record['type'],
                    text=record['text'] or "",
                    metadata={
                        'filing_id': record['filing_id'],
                        'period': record['period'],
                        'section': record['section'],
                        'xbrl_tag': record['xbrl_tag'],
                        'value': record['value']
                    },
                    embedding=self.embeddings.get(node_id)
                )))

            # Sort by score and return top_k
            candidates.sort(key=lambda x: x[0], reverse=True)
            return [node for _, node in candidates[:top_k]]

    def get_graph_stats(self) -> Dict:
        """Get basic graph statistics."""
        with self.driver.session() as session:
            # Node count
            node_result = session.run("MATCH (n:Node) RETURN count(n) as count")
            node_count = node_result.single()['count']

            # Edge count
            edge_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            edge_count = edge_result.single()['count']

            # Node types
            type_result = session.run("""
                MATCH (n:Node)
                RETURN n.type as type, count(n) as count
            """)
            node_types = {r['type']: r['count'] for r in type_result}

            # Edge types
            edge_type_result = session.run("""
                MATCH ()-[r]->()
                RETURN COALESCE(r.type, type(r)) as type, count(r) as count
            """)
            edge_types = {r['type']: r['count'] for r in edge_type_result}

        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'node_types': node_types,
            'edge_types': edge_types,
            'embeddings_loaded': len(self.embeddings)
        }

    def traverse_with_scoring(
        self,
        seed_ids: List[str],
        edge_types: List[str],
        hops: int,
        max_per_hop: int,
        min_confidence: float,
        confidence_decay: float,
        scorer: EdgeScorer,
        context: TraversalContext,
        min_edge_score: float = 0.3,
    ) -> Tuple[List[TraversedNode], List[Edge], List[EdgeScore]]:
        """
        Score-based graph traversal using reward/penalty system.

        Instead of just filtering by confidence, we compute a full score
        for each potential edge and only traverse high-scoring edges.

        This prevents:
        - Semantic drift (chains of SEMANTICALLY_SIMILAR)
        - Domain isolation (staying in one domain)
        - High-fanout explosion

        Args:
            seed_ids: Starting node IDs
            edge_types: Allowed edge types for traversal
            hops: Maximum traversal depth
            max_per_hop: Maximum nodes to expand per hop
            min_confidence: Minimum edge confidence (pre-filter)
            confidence_decay: Decay factor for path confidence
            scorer: EdgeScorer instance for computing scores
            context: TraversalContext for tracking state
            min_edge_score: Minimum total score to traverse (default 0.3)

        Returns:
            (traversed_nodes, edges, scores) - nodes, edges, and score details
        """
        # Priority queue: (-score, counter, node_id, hop_dist, incoming_edge, path_conf)
        frontier = []
        counter = 0
        for seed_id in seed_ids:
            heapq.heappush(frontier, (-1.0, counter, seed_id, 0, None, 1.0))
            counter += 1

        visited: Dict[str, Tuple[float, int, Edge]] = {}  # node_id -> (score, hop, edge)
        all_edges: List[Edge] = []
        all_scores: List[EdgeScore] = []  # For diagnostics

        with self.driver.session() as session:
            while frontier:
                neg_score, _, node_id, hop_dist, incoming_edge, path_conf = heapq.heappop(frontier)

                if node_id in visited:
                    continue

                if hop_dist > hops:
                    continue

                # Get node details
                node = self._get_node(session, node_id)
                if not node:
                    continue

                # Record visit
                visited[node_id] = (path_conf, hop_dist, incoming_edge)

                # Update context
                if incoming_edge:
                    context.update_after_traversal(
                        node_id, node.type, incoming_edge.type
                    )

                # Don't expand beyond max hops
                if hop_dist >= hops:
                    continue

                # Get outgoing edges with fanout count
                edge_query = """
                    MATCH (source:Node {id: $node_id})-[r]->(target:Node)
                    WHERE (r.type IN $edge_types OR type(r) IN $edge_types)
                    AND COALESCE(r.confidence, 0.5) >= $min_conf
                    WITH r, target, source
                    OPTIONAL MATCH (source)-[all_out]->()
                    WITH r, target, count(all_out) AS fanout
                    RETURN target.id AS target_id, target.type AS target_type,
                           target.text AS target_text, COALESCE(r.type, type(r)) AS edge_type,
                           COALESCE(r.confidence, 0.5) AS confidence, fanout,
                           target.filing_id AS filing_id, target.period AS period,
                           target.section AS section, target.xbrl_tag AS xbrl_tag,
                           target.value AS value
                    ORDER BY COALESCE(r.confidence, 0.5) DESC
                    LIMIT $limit
                """

                result = session.run(edge_query, {
                    "node_id": node_id,
                    "edge_types": edge_types,
                    "min_conf": min_confidence,
                    "limit": max_per_hop * 3  # Get more, then filter by score
                })

                # Score each potential edge
                scored_edges = []
                for record in result:
                    target_node = Node(
                        id=record["target_id"],
                        type=record["target_type"],
                        text=record["target_text"] or "",
                        metadata={
                            'filing_id': record.get('filing_id'),
                            'period': record.get('period'),
                            'section': record.get('section'),
                            'xbrl_tag': record.get('xbrl_tag'),
                            'value': record.get('value')
                        },
                        embedding=self.embeddings.get(record["target_id"])
                    )

                    edge_score = scorer.score_edge(
                        edge_type=record["edge_type"],
                        edge_confidence=record["confidence"],
                        source_node=node,
                        target_node=target_node,
                        path_confidence=path_conf,
                        source_fanout=record["fanout"]
                    )

                    all_scores.append(edge_score)

                    # Only consider edges above minimum score
                    if edge_score.total_score >= min_edge_score:
                        scored_edges.append((edge_score, target_node, record))

                # Sort by score and take top max_per_hop
                scored_edges.sort(key=lambda x: x[0].total_score, reverse=True)

                for edge_score, target_node, record in scored_edges[:max_per_hop]:
                    if target_node.id in visited:
                        continue

                    # Create edge record
                    edge = Edge(
                        source_id=node_id,
                        target_id=target_node.id,
                        type=record["edge_type"],
                        confidence=record["confidence"],
                        expert="scored",
                        evidence=""
                    )
                    all_edges.append(edge)

                    # Compute new path confidence with decay
                    new_path_conf = path_conf * record["confidence"] * confidence_decay

                    # Add to frontier with score as priority
                    heapq.heappush(
                        frontier,
                        (-edge_score.total_score, counter, target_node.id, hop_dist + 1, edge, new_path_conf)
                    )
                    counter += 1

        # Build TraversedNode list from visited
        traversed_nodes = []
        for node_id, (path_conf, hop_dist, incoming_edge) in visited.items():
            node = self._get_node_cached(node_id)
            if node:
                traversed_nodes.append(TraversedNode(
                    node=node,
                    path_confidence=path_conf,
                    hop_distance=hop_dist,
                    incoming_edge=incoming_edge
                ))

        logger.info(f"Scored traversal: {len(traversed_nodes)} nodes, {len(all_edges)} edges, {len(all_scores)} scores")
        return traversed_nodes, all_edges, all_scores

    def _get_node(self, session, node_id: str) -> Optional[Node]:
        """Get a single node by ID within an existing session."""
        result = session.run("""
            MATCH (n:Node {id: $node_id})
            RETURN n.id as id, n.type as type, n.text as text,
                   n.filing_id as filing_id, n.period as period,
                   n.section as section, n.xbrl_tag as xbrl_tag,
                   n.value as value
        """, node_id=node_id)

        record = result.single()
        if record:
            return Node(
                id=record['id'],
                type=record['type'],
                text=record['text'] or "",
                metadata={
                    'filing_id': record['filing_id'],
                    'period': record['period'],
                    'section': record['section'],
                    'xbrl_tag': record['xbrl_tag'],
                    'value': record['value']
                },
                embedding=self.embeddings.get(record['id'])
            )
        return None

    def _get_node_cached(self, node_id: str) -> Optional[Node]:
        """Get a node by ID using cached data if available."""
        with self.driver.session() as session:
            return self._get_node(session, node_id)

    def search_financial_dynamic(
        self,
        query_terms: List[str],
        query_embedding: Optional[np.ndarray] = None,
        period_filter: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.3,
        expand_search: bool = False
    ) -> List[Node]:
        """
        Dynamic search for FINANCIAL_LINE nodes based on query terms.

        This is the key method for ground-truth-first retrieval:
        - No hardcoded segments or XBRL concepts
        - Searches graph dynamically based on query terms
        - Uses both text matching and embedding similarity
        - Can expand search when commutator indicates high divergence

        BUG 5 FIX: Now includes semantic expansion for concept queries.
        E.g., "growth" expands to ["Revenue", "NetSales", ...].

        Args:
            query_terms: List of terms extracted from user query
            query_embedding: Query embedding for similarity search
            period_filter: Optional fiscal period filter (e.g., "2024", "FY2023")
            limit: Maximum nodes to return
            min_similarity: Minimum embedding similarity threshold
            expand_search: If True, broaden search (lower thresholds, more terms)

        Returns:
            List of FINANCIAL_LINE nodes matching the query
        """
        with self.driver.session() as session:
            # BUG 5 FIX: Expand query terms using semantic mapping
            expanded_terms = list(query_terms)  # Start with original terms
            for term in query_terms:
                term_lower = term.lower()
                # Check if term maps to XBRL concepts
                if term_lower in SEMANTIC_CONCEPT_EXPANSION:
                    xbrl_terms = SEMANTIC_CONCEPT_EXPANSION[term_lower]
                    expanded_terms.extend(xbrl_terms)
                    logger.debug(f"Semantic expansion: '{term}' -> {xbrl_terms}")

            # Remove duplicates while preserving order
            seen = set()
            unique_terms = []
            for t in expanded_terms:
                t_lower = t.lower()
                if t_lower not in seen:
                    seen.add(t_lower)
                    unique_terms.append(t)

            logger.debug(f"Query terms after expansion: {len(query_terms)} -> {len(unique_terms)}")

            # Build dynamic search conditions
            term_conditions = []
            for term in unique_terms:
                # Search in text, xbrl_tag, and section
                term_lower = term.lower()
                term_conditions.append(f"""
                    (toLower(n.text) CONTAINS '{term_lower}'
                     OR toLower(COALESCE(n.xbrl_tag, '')) CONTAINS '{term_lower}'
                     OR toLower(COALESCE(n.section, '')) CONTAINS '{term_lower}')
                """)

            # Combine conditions - if expand_search, use OR; otherwise require more matches
            if expand_search or len(term_conditions) <= 2:
                term_clause = " OR ".join(term_conditions) if term_conditions else "TRUE"
            else:
                # Require at least 2 terms to match for stricter search
                term_clause = " OR ".join(term_conditions)

            # Period filter
            period_clause = ""
            if period_filter:
                period_clause = f"AND (n.period CONTAINS '{period_filter}' OR n.text CONTAINS '{period_filter}')"

            # Query for FINANCIAL_LINE nodes
            query = f"""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND ({term_clause})
                {period_clause}
                RETURN n.id AS id, n.type AS type, n.text AS text,
                       n.filing_id AS filing_id, n.period AS period,
                       n.section AS section, n.xbrl_tag AS xbrl_tag,
                       n.value AS value
                LIMIT {limit * 3}
            """

            result = session.run(query)

            candidates = []
            for record in result:
                node_id = record['id']

                # Compute embedding similarity if available
                similarity = 0.0
                if query_embedding is not None and node_id in self.embeddings:
                    emb = self.embeddings[node_id]
                    norm_q = np.linalg.norm(query_embedding)
                    norm_e = np.linalg.norm(emb)
                    if norm_q > 0 and norm_e > 0:
                        similarity = np.dot(query_embedding, emb) / (norm_q * norm_e)

                # Compute term match score
                text_lower = (record['text'] or '').lower()
                xbrl_lower = (record['xbrl_tag'] or '').lower()
                term_matches = sum(1 for t in query_terms if t.lower() in text_lower or t.lower() in xbrl_lower)
                term_score = term_matches / len(query_terms) if query_terms else 0

                # Combined score: embedding similarity + term matching
                combined_score = 0.6 * similarity + 0.4 * term_score

                # Apply minimum threshold (lower if expanding)
                threshold = min_similarity * 0.5 if expand_search else min_similarity
                if combined_score >= threshold or term_matches > 0:
                    candidates.append((combined_score, Node(
                        id=node_id,
                        type=record['type'],
                        text=record['text'] or "",
                        metadata={
                            'filing_id': record['filing_id'],
                            'period': record['period'],
                            'section': record['section'],
                            'xbrl_tag': record['xbrl_tag'],
                            'value': record['value'],
                            'term_matches': term_matches,
                            'similarity': similarity
                        },
                        embedding=self.embeddings.get(node_id)
                    )))

            # Sort by combined score
            candidates.sort(key=lambda x: x[0], reverse=True)

            logger.debug(f"search_financial_dynamic: Found {len(candidates)} candidates for terms {query_terms[:5]}")
            return [node for _, node in candidates[:limit]]

    def search_related_financial_nodes(
        self,
        seed_node_ids: List[str],
        edge_types: List[str] = None,
        limit: int = 10
    ) -> List[Node]:
        """
        Find FINANCIAL_LINE nodes related to seed nodes via graph edges.

        This enables graph-driven discovery of related financial data
        when direct term matching doesn't find enough results.

        Args:
            seed_node_ids: Starting node IDs to expand from
            edge_types: Edge types to follow (default: EXPLAINS_LINE_ITEM, DISCUSSES, REFERS_TO)
            limit: Maximum nodes to return

        Returns:
            List of related FINANCIAL_LINE nodes
        """
        if edge_types is None:
            edge_types = ["EXPLAINS_LINE_ITEM", "DISCUSSES", "REFERS_TO", "TEMPORAL_NEXT"]

        with self.driver.session() as session:
            result = session.run("""
                MATCH (seed:Node)-[r]-(related:Node)
                WHERE seed.id IN $seed_ids
                AND related.type = 'FINANCIAL_LINE'
                AND (r.type IN $edge_types OR type(r) IN $edge_types)
                RETURN DISTINCT related.id AS id, related.type AS type, related.text AS text,
                       related.filing_id AS filing_id, related.period AS period,
                       related.section AS section, related.xbrl_tag AS xbrl_tag,
                       related.value AS value,
                       COALESCE(r.confidence, 0.5) AS edge_confidence
                ORDER BY edge_confidence DESC
                LIMIT $limit
            """, seed_ids=seed_node_ids, edge_types=edge_types, limit=limit)

            nodes = []
            for record in result:
                nodes.append(Node(
                    id=record['id'],
                    type=record['type'],
                    text=record['text'] or "",
                    metadata={
                        'filing_id': record['filing_id'],
                        'period': record['period'],
                        'section': record['section'],
                        'xbrl_tag': record['xbrl_tag'],
                        'value': record['value'],
                        'edge_confidence': record['edge_confidence']
                    },
                    embedding=self.embeddings.get(record['id'])
                ))

            logger.debug(f"search_related_financial_nodes: Found {len(nodes)} related FINANCIAL_LINE nodes")
            return nodes

    def close(self):
        """Close the database connection."""
        self.driver.close()
