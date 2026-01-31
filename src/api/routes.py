"""API routes for MoE Graph Builder."""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from src.api.schemas import (
    ConnectivityResponse,
    EdgeResponse,
    ErrorResponse,
    EvidenceItem,
    ExpertStatsResponse,
    FilterRequest,
    GraphResponse,
    GraphStatsResponse,
    HealthResponse,
    NodeResponse,
    PathResponse,
    QueryEvidence,
    QueryMetrics,
    QueryRequest,
    QueryResponse,
    QueryVisualization,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TrajectoryHop,
    WebSocketMessage,
)
from src.graph.neo4j_client import Neo4jClient
from src.models import EdgeType, NodeType
from src.config import settings
from src.company_config import CompanyConfig, get_active_company, set_active_company

router = APIRouter()

# Global Neo4j client (set in main.py)
_neo4j_client: Neo4jClient | None = None


def get_neo4j() -> Neo4jClient:
    """Dependency to get Neo4j client."""
    if _neo4j_client is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    return _neo4j_client


def set_neo4j_client(client: Neo4jClient) -> None:
    """Set the global Neo4j client."""
    global _neo4j_client
    _neo4j_client = client


# Health check
@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(neo4j: Neo4jClient = Depends(get_neo4j)) -> HealthResponse:
    """Check API and database health."""
    neo4j_connected = False
    try:
        # Try a simple query
        neo4j.driver.verify_connectivity()
        neo4j_connected = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if neo4j_connected else "degraded",
        neo4j_connected=neo4j_connected,
        timestamp=datetime.utcnow(),
    )


# Graph endpoints
@router.get("/graph", response_model=GraphResponse, tags=["Graph"])
async def get_graph(
    limit: int = Query(default=2000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    edge_limit: int = Query(default=25000, ge=1, le=50000),
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> GraphResponse:
    """Get graph nodes and edges with pagination."""
    try:
        with neo4j.driver.session() as session:
            # Get nodes
            node_result = session.run(
                """
                MATCH (n:Node)
                RETURN n
                ORDER BY n.id
                SKIP $offset LIMIT $limit
                """,
                offset=offset,
                limit=limit,
            )
            nodes = []
            node_ids = set()
            for record in node_result:
                n = record["n"]
                nodes.append(NodeResponse(
                    id=n["id"],
                    type=NodeType(n["type"]),
                    text=n.get("text", ""),
                    metadata=dict(n) if n else {},
                ))
                node_ids.add(n["id"])

            # Get edges between the returned nodes
            edge_result = session.run(
                """
                MATCH (s:Node)-[r]->(t:Node)
                WHERE s.id IN $node_ids AND t.id IN $node_ids
                RETURN r, s.id as source_id, t.id as target_id
                LIMIT $edge_limit
                """,
                node_ids=list(node_ids),
                edge_limit=edge_limit,
            )
            edges = []
            for record in edge_result:
                r = record["r"]
                edges.append(EdgeResponse(
                    id=r.get("id", f"{record['source_id']}->{record['target_id']}"),
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    edge_type=EdgeType(r.get("edge_type", "EXPLAINS")),
                    confidence=r.get("confidence", 0.5),
                    expert=r.get("expert", "unknown"),
                    evidence=r.get("evidence"),
                ))

            # Get totals
            count_result = session.run(
                "MATCH (n:Node) RETURN count(n) as nodes"
            ).single()
            total_nodes = count_result["nodes"] if count_result else 0

            edge_count_result = session.run(
                "MATCH ()-[r]->() RETURN count(r) as edges"
            ).single()
            total_edges = edge_count_result["edges"] if edge_count_result else 0

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=total_nodes,
            total_edges=total_edges,
        )
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats", response_model=GraphStatsResponse, tags=["Graph"])
async def get_graph_stats(neo4j: Neo4jClient = Depends(get_neo4j)) -> GraphStatsResponse:
    """Get graph statistics."""
    try:
        stats = neo4j.get_graph_stats()
        # Convert GraphStats model to dict for GraphStatsResponse
        stats_dict = stats.model_dump() if hasattr(stats, 'model_dump') else dict(stats)
        return GraphStatsResponse(**stats_dict)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/connectivity", response_model=ConnectivityResponse, tags=["Graph"])
async def get_connectivity(neo4j: Neo4jClient = Depends(get_neo4j)) -> ConnectivityResponse:
    """Get graph connectivity information."""
    try:
        with neo4j.driver.session() as session:
            # Use APOC or manual component detection
            result = session.run(
                """
                MATCH (n:Node)
                WITH collect(n) as nodes
                CALL {
                    WITH nodes
                    UNWIND nodes as n
                    MATCH (n)-[*]-(connected:Node)
                    WITH n, collect(DISTINCT connected) + [n] as component
                    RETURN n.id as node_id, size(component) as component_size
                }
                RETURN count(DISTINCT component_size) as num_components,
                       max(component_size) as largest,
                       min(component_size) as smallest
                """
            ).single()

            if result:
                return ConnectivityResponse(
                    is_connected=result["num_components"] == 1,
                    num_components=result["num_components"] or 1,
                    largest_component_size=result["largest"] or 0,
                    smallest_component_size=result["smallest"] or 0,
                    bridge_edges_added=0,
                )
            else:
                return ConnectivityResponse(
                    is_connected=True,
                    num_components=1,
                    largest_component_size=0,
                    smallest_component_size=0,
                    bridge_edges_added=0,
                )
    except Exception as e:
        logger.error(f"Error getting connectivity: {e}")
        # Fallback response
        return ConnectivityResponse(
            is_connected=True,
            num_components=1,
            largest_component_size=0,
            smallest_component_size=0,
            bridge_edges_added=0,
        )


# Node endpoints
@router.get("/nodes/{node_id}", response_model=NodeResponse, tags=["Nodes"])
async def get_node(
    node_id: str,
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> NodeResponse:
    """Get a specific node by ID."""
    try:
        with neo4j.driver.session() as session:
            result = session.run(
                "MATCH (n:Node {id: $id}) RETURN n",
                id=node_id,
            ).single()

            if not result:
                raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

            n = result["n"]
            return NodeResponse(
                id=n["id"],
                type=NodeType(n["type"]),
                text=n.get("text", ""),
                metadata=dict(n) if n else {},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}/neighbors", response_model=GraphResponse, tags=["Nodes"])
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> GraphResponse:
    """Get neighbors of a node up to a certain depth."""
    try:
        with neo4j.driver.session() as session:
            # Get neighbors
            result = session.run(
                f"""
                MATCH path = (start:Node {{id: $id}})-[*1..{depth}]-(neighbor:Node)
                WITH neighbor, relationships(path) as rels
                UNWIND rels as r
                WITH DISTINCT neighbor, collect(DISTINCT r) as edges
                RETURN neighbor, edges
                """,
                id=node_id,
            )

            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()

            for record in result:
                n = record["neighbor"]
                if n["id"] not in seen_nodes:
                    nodes.append(NodeResponse(
                        id=n["id"],
                        type=NodeType(n["type"]),
                        text=n.get("text", ""),
                        metadata=dict(n) if n else {},
                    ))
                    seen_nodes.add(n["id"])

                for r in record["edges"]:
                    edge_id = r.get("id", f"{r.start_node['id']}->{r.end_node['id']}")
                    if edge_id not in seen_edges:
                        edges.append(EdgeResponse(
                            id=edge_id,
                            source_id=r.start_node.get("id", ""),
                            target_id=r.end_node.get("id", ""),
                            edge_type=EdgeType(r.get("edge_type", "EXPLAINS")),
                            confidence=r.get("confidence", 0.5),
                            expert=r.get("expert", "unknown"),
                        ))
                        seen_edges.add(edge_id)

            return GraphResponse(
                nodes=nodes,
                edges=edges,
                total_nodes=len(nodes),
                total_edges=len(edges),
            )
    except Exception as e:
        logger.error(f"Error getting neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Path endpoints
@router.get("/path", response_model=PathResponse, tags=["Path"])
async def find_path(
    source_id: str = Query(..., description="Source node ID"),
    target_id: str = Query(..., description="Target node ID"),
    max_depth: int = Query(default=10, ge=1, le=20),
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> PathResponse:
    """Find shortest path between two nodes."""
    try:
        result = neo4j.find_shortest_path(source_id, target_id)

        if not result:
            return PathResponse(path_exists=False)

        # Fetch full node data for path
        nodes = []
        with neo4j.driver.session() as session:
            for node_id in result["path"]:
                node_result = session.run(
                    "MATCH (n:Node {id: $id}) RETURN n",
                    id=node_id,
                ).single()
                if node_result:
                    n = node_result["n"]
                    nodes.append(NodeResponse(
                        id=n["id"],
                        type=NodeType(n["type"]),
                        text=n.get("text", ""),
                        metadata=dict(n) if n else {},
                    ))

        return PathResponse(
            path_exists=True,
            path_length=result["length"],
            nodes=nodes,
            edges=[],  # Edge details not returned by shortestPath
        )
    except Exception as e:
        logger.error(f"Error finding path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Filter endpoints
@router.post("/filter", response_model=GraphResponse, tags=["Filter"])
async def filter_graph(
    request: FilterRequest,
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> GraphResponse:
    """Filter graph by various criteria."""
    try:
        with neo4j.driver.session() as session:
            # Build dynamic query
            conditions = []
            params: dict[str, Any] = {
                "limit": request.limit,
                "offset": request.offset,
            }

            if request.node_types:
                conditions.append("n.type IN $node_types")
                params["node_types"] = [t.value for t in request.node_types]

            if request.filing_ids:
                conditions.append("n.filing_id IN $filing_ids")
                params["filing_ids"] = request.filing_ids

            if request.periods:
                conditions.append("n.period IN $periods")
                params["periods"] = request.periods

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            # Get filtered nodes
            node_query = f"""
                MATCH (n:Node)
                WHERE {where_clause}
                RETURN n
                ORDER BY n.id
                SKIP $offset LIMIT $limit
            """
            node_result = session.run(node_query, **params)

            nodes = []
            node_ids = set()
            for record in node_result:
                n = record["n"]
                nodes.append(NodeResponse(
                    id=n["id"],
                    type=NodeType(n["type"]),
                    text=n.get("text", ""),
                    metadata=dict(n) if n else {},
                ))
                node_ids.add(n["id"])

            # Get edges between filtered nodes
            edge_conditions = ["s.id IN $node_ids AND t.id IN $node_ids"]

            if request.edge_types:
                edge_conditions.append("r.edge_type IN $edge_types")
                params["edge_types"] = [t.value for t in request.edge_types]

            if request.experts:
                edge_conditions.append("r.expert IN $experts")
                params["experts"] = request.experts

            if request.min_confidence > 0:
                edge_conditions.append("r.confidence >= $min_confidence")
                params["min_confidence"] = request.min_confidence

            params["node_ids"] = list(node_ids)
            edge_where = " AND ".join(edge_conditions)

            edge_query = f"""
                MATCH (s:Node)-[r]->(t:Node)
                WHERE {edge_where}
                RETURN r, s.id as source_id, t.id as target_id
                LIMIT $limit
            """
            edge_result = session.run(edge_query, **params)

            edges = []
            for record in edge_result:
                r = record["r"]
                edges.append(EdgeResponse(
                    id=r.get("id", f"{record['source_id']}->{record['target_id']}"),
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    edge_type=EdgeType(r.get("edge_type", "EXPLAINS")),
                    confidence=r.get("confidence", 0.5),
                    expert=r.get("expert", "unknown"),
                    evidence=r.get("evidence"),
                ))

            return GraphResponse(
                nodes=nodes,
                edges=edges,
                total_nodes=len(nodes),
                total_edges=len(edges),
            )
    except Exception as e:
        logger.error(f"Error filtering graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoints
@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_nodes(
    request: SearchRequest,
    neo4j: Neo4jClient = Depends(get_neo4j),
) -> SearchResponse:
    """Search nodes by text content."""
    try:
        with neo4j.driver.session() as session:
            conditions = ["toLower(n.text) CONTAINS toLower($search_text)"]
            params: dict[str, Any] = {
                "search_text": request.query,
                "limit": request.limit,
            }

            if request.node_types:
                conditions.append("n.type IN $node_types")
                params["node_types"] = [t.value for t in request.node_types]

            where_clause = " AND ".join(conditions)

            cypher_query = f"""
                MATCH (n:Node)
                WHERE {where_clause}
                RETURN n,
                       CASE WHEN toLower(n.text) STARTS WITH toLower($search_text)
                            THEN 1.0
                            ELSE 0.5 END as score
                ORDER BY score DESC
                LIMIT $limit
            """

            result = session.run(cypher_query, **params)

            results = []
            for record in result:
                n = record["n"]
                node = NodeResponse(
                    id=n["id"],
                    type=NodeType(n["type"]),
                    text=n.get("text", ""),
                    metadata=dict(n) if n else {},
                )

                # Create highlight snippet
                text = n.get("text", "")
                query_lower = request.query.lower()
                idx = text.lower().find(query_lower)
                if idx >= 0:
                    start = max(0, idx - 50)
                    end = min(len(text), idx + len(request.query) + 50)
                    highlight = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
                else:
                    highlight = text[:100] + "..." if len(text) > 100 else text

                results.append(SearchResult(
                    node=node,
                    score=record["score"],
                    highlight=highlight,
                ))

            return SearchResponse(
                query=request.query,
                results=results,
                total=len(results),
            )
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Expert stats
@router.get("/experts", response_model=list[ExpertStatsResponse], tags=["Experts"])
async def get_expert_stats(neo4j: Neo4jClient = Depends(get_neo4j)) -> list[ExpertStatsResponse]:
    """Get statistics for each expert."""
    try:
        with neo4j.driver.session() as session:
            result = session.run(
                """
                MATCH ()-[r]->()
                WITH r.expert as expert, r.edge_type as edge_type,
                     collect(r.confidence) as confidences
                RETURN expert,
                       edge_type,
                       size(confidences) as total,
                       avg(confidences[0]) as avg_conf,
                       min(confidences[0]) as min_conf,
                       max(confidences[0]) as max_conf
                ORDER BY total DESC
                """
            )

            stats = []
            for record in result:
                if record["expert"]:
                    stats.append(ExpertStatsResponse(
                        expert_name=record["expert"],
                        total_edges=record["total"],
                        avg_confidence=record["avg_conf"] or 0.0,
                        min_confidence=record["min_conf"] or 0.0,
                        max_confidence=record["max_conf"] or 0.0,
                        edge_type=EdgeType(record["edge_type"]) if record["edge_type"] else EdgeType.EXPLAINS,
                    ))

            return stats
    except Exception as e:
        logger.error(f"Error getting expert stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for real-time updates
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: WebSocketMessage):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message.model_dump(mode="json"))
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")


manager = ConnectionManager()


@router.websocket("/ws/graph/stream")
async def websocket_graph_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time graph updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            logger.debug(f"Received WS message: {data}")

            # Echo back with acknowledgment
            await websocket.send_json({
                "type": "ack",
                "data": {"message": data},
                "timestamp": datetime.utcnow().isoformat(),
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_update(update_type: str, data: dict[str, Any]):
    """Helper to broadcast updates to all connected clients."""
    message = WebSocketMessage(
        type=update_type,
        data=data,
        timestamp=datetime.utcnow(),
    )
    await manager.broadcast(message)


# ═══════════════════════════════════════════════════════════════════════════
# OpMech Query Endpoint
# ═══════════════════════════════════════════════════════════════════════════

# Global OpMech system (lazy initialized)
_opmech_system = None
_enhanced_opmech_system = None
_unified_system = None

# System selection flags
# UNIFIED: Ground truth FIRST, then LLM (recommended - fixes the core architectural flaw)
# ENHANCED: LLM FIRST, then ground truth validation/correction
# BASE: LLM only, no ground truth validation
USE_UNIFIED_SYSTEM = True  # Use the new unified pipeline architecture
USE_ENHANCED_SYSTEM = True  # Fallback if unified fails


def get_opmech_system():
    """Get or create the OpMech system."""
    global _opmech_system
    if _opmech_system is None:
        try:
            from src.opmech.system import OpMechGraphRAG
            _opmech_system = OpMechGraphRAG(
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password,
                vllm_url=settings.vllm_api_base,
            )
            logger.info("OpMech-GraphRAG system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpMech system: {e}")
            raise
    return _opmech_system


def get_enhanced_opmech_system():
    """Get or create the Enhanced OpMech system with ground truth validation."""
    global _enhanced_opmech_system
    if _enhanced_opmech_system is None:
        try:
            from src.opmech.enhanced_system import EnhancedOpMechGraphRAG
            # COMPANY-AGNOSTIC: Use active company config if set, otherwise use default ticker
            company_config = get_active_company()
            company = company_config.ticker if company_config else settings.default_ticker
            _enhanced_opmech_system = EnhancedOpMechGraphRAG(
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password,
                vllm_url=settings.vllm_api_base,
                company=company,
            )
            logger.info(f"Enhanced OpMech-GraphRAG system initialized for company: {company}")
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced OpMech system: {e}")
            # Fall back to base system
            logger.info("Falling back to base OpMech system")
            return get_opmech_system()
    return _enhanced_opmech_system


def get_unified_system():
    """
    Get or create the Integrated OpMech system.

    This uses the FULL OpMech pipeline (graph traversal, dual operators, commutator)
    with ground-truth-first architecture:
    - Graph traversal happens normally (multiple hops, explore/exploit)
    - Ground truth is INJECTED into LLM prompts BEFORE answer generation
    - All original metrics are preserved (trajectory, divergence, etc.)

    This fixes the core problem while keeping full functionality:
    - OLD: Graph traversal -> LLM answer -> Ground truth validates/corrects AFTER
    - NEW: Graph traversal -> Ground truth injected -> LLM answer WITH facts

    COMPANY-AGNOSTIC: Uses active company config if set.
    """
    global _unified_system
    if _unified_system is None:
        try:
            from src.core.integrated_system import IntegratedOpMechSystem
            # COMPANY-AGNOSTIC: Use active company config if set, otherwise use default ticker
            company_config = get_active_company()
            company = company_config.ticker if company_config else settings.default_ticker
            _unified_system = IntegratedOpMechSystem(
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password,
                vllm_url=settings.vllm_api_base,
                company=company,
            )
            logger.info(f"Integrated OpMech system initialized for company: {company}")
        except Exception as e:
            logger.error(f"Failed to initialize Integrated system: {e}")
            raise
    return _unified_system


@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_opmech(request: QueryRequest) -> QueryResponse:
    """
    Process a query using the OpMech-GraphRAG system.

    System selection priority:
    1. UNIFIED (default): Ground truth FIRST, then LLM generates WITH the facts
       - Fixes the core architectural flaw of the old system
    2. ENHANCED: LLM FIRST, then ground truth validation/correction (fallback)
    3. BASE: LLM only, no ground truth validation

    The unified system addresses the fundamental problem:
    - OLD: LLM says "cannot determine" -> Ground truth appended AFTER
    - NEW: Ground truth retrieved FIRST -> LLM generates coherent answer WITH the facts
    """
    try:
        logger.info(f"Processing query: {request.query[:100]}...")

        # ═══════════════════════════════════════════════════════════════════════
        # INTEGRATED SYSTEM: Full pipeline + ground truth injection
        # ═══════════════════════════════════════════════════════════════════════
        if USE_UNIFIED_SYSTEM:
            try:
                integrated_system = get_unified_system()
                integrated_result = integrated_system.query(query=request.query)

                logger.info(f"Integrated system: Hops={integrated_result.hops_used}, "
                           f"Ground truth injected={integrated_result.ground_truth_injected}, "
                           f"XBRL facts={integrated_result.xbrl_facts_count}")

                # Build trajectory from real graph traversal data
                trajectory = []
                for t in integrated_result.trajectory:
                    trajectory.append(TrajectoryHop(
                        hop=t.get("hop", 1),
                        delta=t.get("delta", 0.0),
                        delta_E=t.get("delta_E", 0.0),
                        delta_V=t.get("delta_V", 0.0),
                        delta_A=t.get("delta_A", 0.0),
                        delta_C=t.get("delta_C", 0.0),
                        nodesA=t.get("nodesA", 0),
                        nodesB=t.get("nodesB", 0),
                        bridgeSeeds=t.get("bridgeSeeds", 0),
                    ))

                # Extract evidence from graph traversal
                evidence_a = []
                evidence_b = []
                if integrated_result.evidence_A:
                    for e in integrated_result.evidence_A:
                        content = getattr(e, 'text', None) or getattr(e, 'content', str(e))
                        node_type = getattr(e, 'type', 'FINANCIAL_LINE')
                        metadata = getattr(e, 'metadata', {}) or {}
                        score = metadata.get('score', metadata.get('confidence', 0.0))
                        evidence_a.append(EvidenceItem(
                            type=node_type,
                            content=content,
                            score=float(score) if score else 0.0,
                        ))
                if integrated_result.evidence_B:
                    for e in integrated_result.evidence_B:
                        content = getattr(e, 'text', None) or getattr(e, 'content', str(e))
                        node_type = getattr(e, 'type', 'TEXT_SECTION')
                        metadata = getattr(e, 'metadata', {}) or {}
                        score = metadata.get('score', metadata.get('confidence', 0.0))
                        evidence_b.append(EvidenceItem(
                            type=node_type,
                            content=content,
                            score=float(score) if score else 0.0,
                        ))

                # Determine trust decision based on mode
                mode_value = integrated_result.mode.upper()
                if mode_value == 'EXPLOIT':
                    trust_decision = 'TRUST_A' if integrated_result.reliability_A > integrated_result.reliability_B else 'TRUST_B'
                elif mode_value == 'EXPLORE':
                    trust_decision = 'MERGE_EQUAL'
                else:
                    trust_decision = 'MERGE_WEIGHTED'

                response = QueryResponse(
                    answer=integrated_result.answer,
                    mode=mode_value,
                    confidence=integrated_result.confidence,
                    answer_A=integrated_result.answer_A,
                    answer_B=integrated_result.answer_B,
                    metrics=QueryMetrics(
                        hops_used=integrated_result.hops_used,
                        final_delta=integrated_result.final_delta,
                        delta_E=integrated_result.delta_E,
                        delta_V=integrated_result.delta_V,
                        delta_A=integrated_result.delta_A,
                        delta_C=integrated_result.delta_C,
                        trust_decision=trust_decision,
                        reliability_A=integrated_result.reliability_A,
                        reliability_B=integrated_result.reliability_B,
                        path_confidence_A=integrated_result.path_confidence_A,
                        path_confidence_B=integrated_result.path_confidence_B,
                        financial_ratio_A=integrated_result.inclusion_rate,
                        financial_ratio_B=integrated_result.inclusion_rate,
                        query_type="factual",
                        query_complexity="medium" if integrated_result.hops_used > 2 else "simple",
                        evidence_count_A=len(evidence_a) + integrated_result.xbrl_facts_count,
                        evidence_count_B=len(evidence_b) + integrated_result.xbrl_facts_count,
                        trajectory=trajectory,
                    ),
                    evidence=QueryEvidence(
                        evidence_A=evidence_a,
                        evidence_B=evidence_b,
                    ),
                    visualization=QueryVisualization(
                        traversal_A={"nodes": [], "edges": []},
                        traversal_B={"nodes": [], "edges": []},
                        bridge_edges=[],
                        final_evidence_nodes=[],
                    ),
                    reasoning=integrated_result.reasoning + f"\n\n[Integrated: Full pipeline + "
                             f"Ground truth injected, XBRL facts: {integrated_result.xbrl_facts_count}, "
                             f"Inclusion rate: {integrated_result.inclusion_rate:.0%}]",
                )

                logger.info(f"Query processed with integrated system. Mode: {response.mode}, "
                           f"Hops: {response.metrics.hops_used}, Confidence: {response.confidence:.1%}")

                return response

            except Exception as e:
                logger.warning(f"Integrated system failed, falling back to enhanced: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                # Fall through to enhanced system

        # ═══════════════════════════════════════════════════════════════════════
        # ENHANCED SYSTEM (Fallback): LLM first, then validation
        # ═══════════════════════════════════════════════════════════════════════
        if USE_ENHANCED_SYSTEM:
            try:
                enhanced_system = get_enhanced_opmech_system()
                enhanced_result = enhanced_system.query(query=request.query)

                # Get original result for evidence extraction
                result = enhanced_result.original_result

                # Log enhanced features
                logger.info(f"Enhanced validation: {enhanced_result.validations_passed} passed, "
                           f"{enhanced_result.validations_failed} failed")
                logger.info(f"Ground truth used: {enhanced_result.ground_truth_used}")
                logger.info(f"XBRL evidence: {enhanced_result.xbrl_evidence_count} nodes")
                if enhanced_result.corrections_applied:
                    logger.info(f"Corrections applied: {len(enhanced_result.corrections_applied)}")

                # Override answer with enhanced answer
                final_answer = enhanced_result.answer
                final_confidence = enhanced_result.confidence
                reasoning_suffix = f"\n\n[Enhanced: Validations {enhanced_result.validations_passed}/{enhanced_result.validations_passed + enhanced_result.validations_failed}, "
                reasoning_suffix += f"XBRL evidence: {enhanced_result.xbrl_evidence_count}]"

            except Exception as e:
                logger.warning(f"Enhanced system failed, falling back to base: {e}")
                system = get_opmech_system()
                result = system.query(query=request.query)
                final_answer = result.answer
                final_confidence = result.confidence
                reasoning_suffix = ""
        else:
            # Get the base OpMech system
            system = get_opmech_system()

            # Run the query through the OpMech system
            # Note: max_hops, tau_low, tau_high are set during system initialization
            result = system.query(query=request.query)
            final_answer = result.answer
            final_confidence = result.confidence
            reasoning_suffix = ""

        # Log raw result attributes for debugging
        logger.info(f"Raw result attributes: {dir(result)}")
        logger.info(f"Raw result dict: {result.__dict__ if hasattr(result, '__dict__') else 'no __dict__'}")

        # Extract evidence from the result (Node objects have: id, type, text, metadata)
        evidence_a = []
        evidence_b = []
        if hasattr(result, 'evidence_A') and result.evidence_A:
            for e in result.evidence_A:
                # Node has 'text' field, not 'content'
                content = getattr(e, 'text', None) or getattr(e, 'content', str(e))
                node_type = getattr(e, 'type', 'FINANCIAL_LINE')
                # Get score from metadata if available
                metadata = getattr(e, 'metadata', {}) or {}
                score = metadata.get('score', metadata.get('confidence', 0.0))
                evidence_a.append(EvidenceItem(
                    type=node_type,
                    content=content,
                    score=float(score) if score else 0.0,
                ))
        if hasattr(result, 'evidence_B') and result.evidence_B:
            for e in result.evidence_B:
                content = getattr(e, 'text', None) or getattr(e, 'content', str(e))
                node_type = getattr(e, 'type', 'TEXT_SECTION')
                metadata = getattr(e, 'metadata', {}) or {}
                score = metadata.get('score', metadata.get('confidence', 0.0))
                evidence_b.append(EvidenceItem(
                    type=node_type,
                    content=content,
                    score=float(score) if score else 0.0,
                ))

        logger.info(f"Evidence extracted - A: {len(evidence_a)} nodes, B: {len(evidence_b)} nodes")

        # Calculate financial evidence ratios
        financial_count_a = sum(1 for e in evidence_a if e.type == 'FINANCIAL_LINE')
        financial_count_b = sum(1 for e in evidence_b if e.type == 'FINANCIAL_LINE')
        financial_ratio_a = financial_count_a / len(evidence_a) if evidence_a else 0.0
        financial_ratio_b = financial_count_b / len(evidence_b) if evidence_b else 0.0

        logger.info(f"Financial ratios - A: {financial_ratio_a:.2%} ({financial_count_a}/{len(evidence_a)}), B: {financial_ratio_b:.2%} ({financial_count_b}/{len(evidence_b)})")

        # Build trajectory from CommutatorResult objects with FULL divergence components
        trajectory = []
        final_delta = 0.0
        delta_E = 0.0
        delta_V = 0.0
        delta_A = 0.0
        delta_C = 0.0

        if hasattr(result, 'trajectory') and result.trajectory:
            for hop_result in result.trajectory:
                # CommutatorResult has: delta_E, delta_V, delta_A, delta_C, combined, hop, operator_A_score, operator_B_score
                hop_num = getattr(hop_result, 'hop', len(trajectory) + 1)
                combined = getattr(hop_result, 'combined', 0.0)
                hop_delta_E = getattr(hop_result, 'delta_E', 0.0)
                hop_delta_V = getattr(hop_result, 'delta_V', 0.0)
                hop_delta_A = getattr(hop_result, 'delta_A', 0.0)
                hop_delta_C = getattr(hop_result, 'delta_C', 0.0)

                # Get node counts from operator scores (approximation)
                nodes_a = int(getattr(hop_result, 'operator_A_score', 0) * 100)
                nodes_b = int(getattr(hop_result, 'operator_B_score', 0) * 100)

                trajectory.append(TrajectoryHop(
                    hop=hop_num,
                    delta=combined,
                    delta_E=hop_delta_E,
                    delta_V=hop_delta_V,
                    delta_A=hop_delta_A,
                    delta_C=hop_delta_C,
                    nodesA=nodes_a,
                    nodesB=nodes_b,
                    bridgeSeeds=0,
                ))

            # Get final divergence values from last trajectory item
            last_hop = result.trajectory[-1]
            final_delta = getattr(last_hop, 'combined', 0.0)
            delta_E = getattr(last_hop, 'delta_E', 0.0)
            delta_V = getattr(last_hop, 'delta_V', 0.0)
            delta_A = getattr(last_hop, 'delta_A', 0.0)
            delta_C = getattr(last_hop, 'delta_C', 0.0)

        # Get operator reliability from operator_scores dict
        operator_scores = getattr(result, 'operator_scores', {})
        reliability_A = operator_scores.get('A', operator_scores.get('structure_first', 0.7))
        reliability_B = operator_scores.get('B', operator_scores.get('narrative_first', 0.55))

        # Determine trust decision based on mode and reliability
        mode_value = result.mode.value if hasattr(result.mode, 'value') else str(result.mode)
        if mode_value.lower() == 'exploit':
            trust_decision = 'TRUST_A' if reliability_A > reliability_B else 'TRUST_B'
        elif mode_value.lower() == 'explore':
            trust_decision = 'MERGE_EQUAL'
        else:
            trust_decision = 'MERGE_WEIGHTED'

        # Extract reasoning and parse query type from it
        reasoning = getattr(result, 'reasoning', '')

        # Parse query type from reasoning string (e.g., "Query type: numerical (simple)")
        import re
        query_type = 'descriptive'
        query_complexity = 'medium'
        if reasoning:
            type_match = re.search(r'Query type:\s*(\w+)', reasoning, re.IGNORECASE)
            if type_match:
                query_type = type_match.group(1).lower()
            complexity_match = re.search(r'\((\w+)\)', reasoning)
            if complexity_match:
                query_complexity = complexity_match.group(1).lower()

        # Get individual operator answers
        answer_A = getattr(result, 'answer_A', '')
        answer_B = getattr(result, 'answer_B', '')

        # Get path confidence per operator
        path_confidence_A = getattr(result, 'path_confidence_A', 0.0)
        path_confidence_B = getattr(result, 'path_confidence_B', 0.0)

        # Build response with all metrics from documentation
        response = QueryResponse(
            answer=final_answer,
            mode=mode_value.upper(),
            confidence=final_confidence,
            answer_A=answer_A,
            answer_B=answer_B,
            metrics=QueryMetrics(
                hops_used=getattr(result, 'hops_used', len(trajectory)),
                final_delta=final_delta,
                delta_E=delta_E,
                delta_V=delta_V,
                delta_A=delta_A,
                delta_C=delta_C,
                trust_decision=trust_decision,
                reliability_A=reliability_A,
                reliability_B=reliability_B,
                path_confidence_A=path_confidence_A,
                path_confidence_B=path_confidence_B,
                financial_ratio_A=financial_ratio_a,
                financial_ratio_B=financial_ratio_b,
                query_type=query_type,
                query_complexity=query_complexity,
                evidence_count_A=len(evidence_a),
                evidence_count_B=len(evidence_b),
                trajectory=trajectory,
            ),
            evidence=QueryEvidence(
                evidence_A=evidence_a,
                evidence_B=evidence_b,
            ),
            visualization=QueryVisualization(
                traversal_A={"nodes": [], "edges": []},
                traversal_B={"nodes": [], "edges": []},
                bridge_edges=[],
                final_evidence_nodes=[],
            ),
            reasoning=reasoning + reasoning_suffix,
        )

        # Log detailed response for debugging
        logger.info(f"Query processed successfully. Mode: {response.mode}, Confidence: {response.confidence:.1%}")
        logger.info(f"Query type: {response.metrics.query_type} ({response.metrics.query_complexity})")
        logger.info(f"Metrics - Hops: {response.metrics.hops_used}, Delta: {response.metrics.final_delta:.3f}")
        logger.info(f"Divergence - E: {response.metrics.delta_E:.3f}, V: {response.metrics.delta_V:.3f}, A: {response.metrics.delta_A:.3f}, C: {response.metrics.delta_C:.3f}")
        logger.info(f"Trust: {response.metrics.trust_decision}, Reliability A: {response.metrics.reliability_A:.2f}, B: {response.metrics.reliability_B:.2f}")
        logger.info(f"Path Confidence - A: {response.metrics.path_confidence_A:.2f}, B: {response.metrics.path_confidence_B:.2f}")
        logger.info(f"Financial Ratio - A: {response.metrics.financial_ratio_A:.1%}, B: {response.metrics.financial_ratio_B:.1%}")
        logger.info(f"Evidence A: {len(evidence_a)} items, Evidence B: {len(evidence_b)} items")
        logger.info(f"Trajectory hops: {len(trajectory)}")
        if answer_A:
            logger.info(f"Answer A: {answer_A[:100]}..." if len(answer_A) > 100 else f"Answer A: {answer_A}")
        if answer_B:
            logger.info(f"Answer B: {answer_B[:100]}..." if len(answer_B) > 100 else f"Answer B: {answer_B}")
        logger.info(f"Reasoning: {response.reasoning[:200]}..." if len(response.reasoning) > 200 else f"Reasoning: {response.reasoning}")

        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")
