"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models import EdgeType, NodeType


class NodeResponse(BaseModel):
    """Response model for a node."""

    id: str
    type: NodeType
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_dim: int | None = None


class EdgeResponse(BaseModel):
    """Response model for an edge."""

    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    confidence: float
    expert: str
    evidence: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    """Response model for graph data."""

    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
    total_nodes: int
    total_edges: int


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""

    total_nodes: int
    total_edges: int
    nodes_by_type: dict[str, int]
    edges_by_type: dict[str, int]
    edges_by_expert: dict[str, int]
    connected_components: int
    is_connected: bool
    isolated_nodes: int = 0
    average_degree: float = 0.0
    max_degree: int = 0
    min_degree: int = 0
    largest_component_size: int = 0
    bridge_edges: int = 0


class PathResponse(BaseModel):
    """Response model for path queries."""

    path_exists: bool
    path_length: int | None = None
    nodes: list[NodeResponse] = Field(default_factory=list)
    edges: list[EdgeResponse] = Field(default_factory=list)


class FilterRequest(BaseModel):
    """Request model for filtering graph."""

    node_types: list[NodeType] | None = None
    edge_types: list[EdgeType] | None = None
    experts: list[str] | None = None
    min_confidence: float = 0.0
    filing_ids: list[str] | None = None
    periods: list[str] | None = None
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class SearchRequest(BaseModel):
    """Request model for text search."""

    query: str = Field(..., min_length=1, max_length=500)
    node_types: list[NodeType] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    use_embedding: bool = False


class SearchResult(BaseModel):
    """Single search result."""

    node: NodeResponse
    score: float
    highlight: str | None = None


class SearchResponse(BaseModel):
    """Response model for search."""

    query: str
    results: list[SearchResult]
    total: int


class ExpertStatsResponse(BaseModel):
    """Statistics for a single expert."""

    expert_name: str
    total_edges: int
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    edge_type: EdgeType


class ConnectivityResponse(BaseModel):
    """Response model for connectivity status."""

    is_connected: bool
    num_components: int
    largest_component_size: int
    smallest_component_size: int
    bridge_edges_added: int


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    neo4j_connected: bool
    timestamp: datetime
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    detail: str | None = None
    code: str | None = None


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str  # "node_update", "edge_update", "stats_update", "error"
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# OpMech Query Schemas
# ═══════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """Request model for OpMech query."""

    query: str = Field(..., min_length=1, max_length=2000, description="The query to process")
    max_hops: int = Field(default=5, ge=1, le=10, description="Maximum traversal hops")
    tau_low: float = Field(default=0.25, ge=0.0, le=1.0, description="Low divergence threshold")
    tau_high: float = Field(default=0.60, ge=0.0, le=1.0, description="High divergence threshold")


class TrajectoryHop(BaseModel):
    """Single hop in the traversal trajectory with full divergence components."""

    hop: int
    delta: float  # Combined divergence
    # Per-hop divergence components (from CommutatorResult)
    delta_E: float = 0.0  # Evidence divergence
    delta_V: float = 0.0  # Structural divergence
    delta_A: float = 0.0  # Answer divergence
    delta_C: float = 0.0  # Confidence divergence
    # Node counts per operator
    nodes_A: int = Field(alias="nodesA", default=0)
    nodes_B: int = Field(alias="nodesB", default=0)
    bridge_seeds: int = Field(alias="bridgeSeeds", default=0)

    class Config:
        populate_by_name = True


class EvidenceItem(BaseModel):
    """Single evidence item."""

    type: str
    content: str
    score: float = 0.0


class QueryMetrics(BaseModel):
    """Metrics from the query execution."""

    hops_used: int
    final_delta: float
    # Final divergence components
    delta_E: float = 0.0
    delta_V: float = 0.0
    delta_A: float = 0.0
    delta_C: float = 0.0
    # Trust and reliability
    trust_decision: str
    reliability_A: float = 0.0
    reliability_B: float = 0.0
    # Path confidence per operator
    path_confidence_A: float = 0.0
    path_confidence_B: float = 0.0
    # Financial evidence ratio (for numerical queries)
    financial_ratio_A: float = 0.0
    financial_ratio_B: float = 0.0
    # Query classification
    query_type: str
    query_complexity: str = "medium"
    # Evidence counts
    evidence_count_A: int = 0
    evidence_count_B: int = 0
    # Trajectory with full divergence per hop
    trajectory: list[TrajectoryHop] = Field(default_factory=list)


class QueryEvidence(BaseModel):
    """Evidence from both operators."""

    evidence_A: list[EvidenceItem] = Field(default_factory=list)
    evidence_B: list[EvidenceItem] = Field(default_factory=list)


class QueryVisualization(BaseModel):
    """Visualization data for the query."""

    traversal_A: dict[str, Any] = Field(default_factory=dict)
    traversal_B: dict[str, Any] = Field(default_factory=dict)
    bridge_edges: list[str] = Field(default_factory=list)
    final_evidence_nodes: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """Response model for OpMech query."""

    answer: str
    mode: str  # EXPLOIT, ADAPTIVE, EXPLORE
    confidence: float
    # Individual operator answers (for EXPLORE mode comparison)
    answer_A: str = Field(default="", description="Operator A (Structure-First) answer")
    answer_B: str = Field(default="", description="Operator B (Narrative-First) answer")
    metrics: QueryMetrics
    evidence: QueryEvidence = Field(default_factory=QueryEvidence)
    visualization: QueryVisualization = Field(default_factory=QueryVisualization)
    reasoning: str = Field(default="", description="Mode selection reasoning")
