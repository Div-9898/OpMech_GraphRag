"""Neo4j client for graph storage and querying."""

from contextlib import contextmanager
from typing import Any, Generator

from loguru import logger
from neo4j import GraphDatabase, Session

from src.config import settings
from src.models import Edge, EdgeType, GraphStats, Node, NodeType


class Neo4jClient:
    """Client for interacting with Neo4j graph database."""

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
    ):
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self._driver = None

    @property
    def driver(self):
        """Lazy-load Neo4j driver."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        return self._driver

    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a Neo4j session."""
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def verify_connectivity(self) -> bool:
        """Verify connection to Neo4j."""
        try:
            with self.session() as session:
                result = session.run("RETURN 1 AS n")
                return result.single()["n"] == 1
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            return False

    def create_indexes(self):
        """Create indexes for efficient querying."""
        index_queries = [
            "CREATE INDEX node_id IF NOT EXISTS FOR (n:Node) ON (n.id)",
            "CREATE INDEX node_filing IF NOT EXISTS FOR (n:Node) ON (n.filing_id)",
            "CREATE INDEX node_period IF NOT EXISTS FOR (n:Node) ON (n.period)",
            "CREATE INDEX node_type IF NOT EXISTS FOR (n:Node) ON (n.type)",
        ]

        with self.session() as session:
            for query in index_queries:
                try:
                    session.run(query)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")

        logger.info("Created Neo4j indexes")

    def clear_database(self):
        """Clear all nodes and edges from the database."""
        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Cleared Neo4j database")

    def insert_nodes(self, nodes: list[Node], batch_size: int = 1000):
        """Insert nodes into Neo4j."""
        logger.info(f"Inserting {len(nodes)} nodes...")

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # Prepare node data
            node_data = []
            for node in batch:
                data = {
                    "id": node.id,
                    "type": node.type.value if isinstance(node.type, NodeType) else node.type,
                    "text": node.text[:2000],  # Truncate for safety
                    "filing_id": node.metadata.filing_id,
                    "period": node.metadata.period,
                    "section": node.metadata.section,
                    "xbrl_tag": node.metadata.xbrl_tag,
                    "value": node.metadata.value,
                    "unit": node.metadata.unit,
                    "note_number": node.metadata.note_number,
                }
                node_data.append(data)

            # Batch insert
            query = """
            UNWIND $nodes AS node
            CREATE (n:Node {
                id: node.id,
                type: node.type,
                text: node.text,
                filing_id: node.filing_id,
                period: node.period,
                section: node.section,
                xbrl_tag: node.xbrl_tag,
                value: node.value,
                unit: node.unit,
                note_number: node.note_number
            })
            """

            with self.session() as session:
                session.run(query, nodes=node_data)

            logger.debug(f"Inserted nodes {i} to {i + len(batch)}")

        logger.info(f"Inserted {len(nodes)} nodes")

    def insert_edges(self, edges: list[Edge], batch_size: int = 1000):
        """Insert edges into Neo4j."""
        logger.info(f"Inserting {len(edges)} edges...")

        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]

            # Prepare edge data
            edge_data = []
            for edge in batch:
                data = {
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "edge_type": edge.edge_type.value if isinstance(edge.edge_type, EdgeType) else edge.edge_type,
                    "confidence": edge.confidence,
                    "expert": edge.expert,
                    "evidence": edge.evidence[:500] if edge.evidence else "",
                }
                edge_data.append(data)

            # Batch insert edges
            query = """
            UNWIND $edges AS edge
            MATCH (source:Node {id: edge.source_id})
            MATCH (target:Node {id: edge.target_id})
            CREATE (source)-[r:RELATED {
                id: edge.id,
                type: edge.edge_type,
                confidence: edge.confidence,
                expert: edge.expert,
                evidence: edge.evidence
            }]->(target)
            """

            with self.session() as session:
                session.run(query, edges=edge_data)

            logger.debug(f"Inserted edges {i} to {i + len(batch)}")

        logger.info(f"Inserted {len(edges)} edges")

    def get_graph_stats(self) -> GraphStats:
        """Get graph statistics including connectivity info."""
        with self.session() as session:
            # Count nodes and edges
            result = session.run("""
                MATCH (n:Node)
                RETURN count(n) AS node_count
            """)
            node_count = result.single()["node_count"]

            result = session.run("""
                MATCH ()-[r]->()
                RETURN count(r) AS edge_count
            """)
            edge_count = result.single()["edge_count"]

            # Count by node type
            result = session.run("""
                MATCH (n:Node)
                RETURN n.type AS type, count(n) AS count
            """)
            nodes_by_type = {record["type"]: record["count"] for record in result}

            # Count by edge type/expert
            result = session.run("""
                MATCH ()-[r]->()
                RETURN r.expert AS expert, count(r) AS count
            """)
            edges_by_expert = {record["expert"]: record["count"] for record in result}

            result = session.run("""
                MATCH ()-[r]->()
                RETURN r.type AS type, count(r) AS count
            """)
            edges_by_type = {record["type"]: record["count"] for record in result}

            # Count isolated nodes (degree 0)
            result = session.run("""
                MATCH (n:Node)
                WHERE NOT (n)--()
                RETURN count(n) AS isolated_count
            """)
            isolated_count = result.single()["isolated_count"]

            # Degree statistics
            result = session.run("""
                MATCH (n:Node)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) AS degree
                RETURN
                    avg(degree) AS avg_degree,
                    max(degree) AS max_degree,
                    min(degree) AS min_degree
            """)
            degree_stats = result.single()

            # Count connected components using GDS if available, otherwise estimate
            try:
                result = session.run("""
                    CALL gds.wcc.stream({
                        nodeProjection: 'Node',
                        relationshipProjection: {
                            RELATED: { orientation: 'UNDIRECTED' }
                        }
                    })
                    YIELD componentId
                    RETURN count(DISTINCT componentId) AS component_count,
                           max(componentId) AS max_component
                """)
                record = result.single()
                component_count = record["component_count"]
            except Exception:
                # Fallback: estimate using simple query
                component_count = 1 if isolated_count == 0 else -1  # -1 means unknown

            # Count bridge edges
            bridge_count = edges_by_type.get("BRIDGE", 0)

            return GraphStats(
                connected_components=component_count,
                is_connected=component_count == 1,
                total_nodes=node_count,
                total_edges=edge_count,
                isolated_nodes=isolated_count,
                average_degree=float(degree_stats["avg_degree"] or 0),
                max_degree=int(degree_stats["max_degree"] or 0),
                min_degree=int(degree_stats["min_degree"] or 0),
                largest_component_size=node_count - isolated_count,  # Approximation
                bridge_edges=bridge_count,
                nodes_by_type=nodes_by_type,
                edges_by_expert=edges_by_expert,
                edges_by_type=edges_by_type,
            )

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
    ) -> list[dict] | None:
        """Find shortest path between two nodes."""
        query = """
        MATCH path = shortestPath(
            (source:Node {id: $source_id})-[*]-(target:Node {id: $target_id})
        )
        RETURN [n IN nodes(path) | n.id] AS node_ids,
               [r IN relationships(path) | {type: r.type, confidence: r.confidence}] AS edges,
               length(path) AS path_length
        """

        with self.session() as session:
            result = session.run(query, source_id=source_id, target_id=target_id)
            record = result.single()

            if record:
                return {
                    "path": record["node_ids"],
                    "edges": record["edges"],
                    "length": record["path_length"],
                }
            return None

    def get_node(self, node_id: str) -> dict | None:
        """Get a single node by ID."""
        query = """
        MATCH (n:Node {id: $node_id})
        RETURN n
        """

        with self.session() as session:
            result = session.run(query, node_id=node_id)
            record = result.single()
            if record:
                return dict(record["n"])
            return None

    def get_neighbors(self, node_id: str, limit: int = 100) -> list[dict]:
        """Get neighbors of a node."""
        query = """
        MATCH (n:Node {id: $node_id})-[r]-(neighbor:Node)
        RETURN neighbor.id AS id,
               neighbor.type AS type,
               neighbor.text AS text,
               r.type AS edge_type,
               r.confidence AS confidence
        LIMIT $limit
        """

        with self.session() as session:
            result = session.run(query, node_id=node_id, limit=limit)
            return [dict(record) for record in result]

    def search_nodes(
        self,
        query: str,
        node_type: str = None,
        filing_id: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search nodes by text content."""
        where_clauses = ["n.text CONTAINS $query"]
        params = {"query": query, "limit": limit}

        if node_type:
            where_clauses.append("n.type = $node_type")
            params["node_type"] = node_type

        if filing_id:
            where_clauses.append("n.filing_id = $filing_id")
            params["filing_id"] = filing_id

        cypher = f"""
        MATCH (n:Node)
        WHERE {' AND '.join(where_clauses)}
        RETURN n.id AS id, n.type AS type, n.text AS text, n.filing_id AS filing_id
        LIMIT $limit
        """

        with self.session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]

    def export_graph(self) -> tuple[list[dict], list[dict]]:
        """Export full graph as nodes and edges."""
        with self.session() as session:
            # Export nodes
            result = session.run("MATCH (n:Node) RETURN n")
            nodes = [dict(record["n"]) for record in result]

            # Export edges
            result = session.run("""
                MATCH (s:Node)-[r]->(t:Node)
                RETURN s.id AS source, t.id AS target,
                       r.type AS type, r.confidence AS confidence,
                       r.expert AS expert
            """)
            edges = [dict(record) for record in result]

        return nodes, edges


# Global client instance
_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client."""
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    client = Neo4jClient()

    if client.verify_connectivity():
        logger.info("Connected to Neo4j successfully")

        # Create indexes
        client.create_indexes()

        # Get stats
        stats = client.get_graph_stats()
        logger.info(f"Graph stats: {stats.total_nodes} nodes, {stats.total_edges} edges")
    else:
        logger.error("Failed to connect to Neo4j")
        logger.info("Start Neo4j with: docker-compose up -d neo4j")
