"""Data models for MoE Graph Builder."""

from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    FINANCIAL_LINE = "FINANCIAL_LINE"
    TEXT_SECTION = "TEXT_SECTION"
    NOTE = "NOTE"
    TABLE_ROW = "TABLE_ROW"
    ENTITY = "ENTITY"


class EdgeType(str, Enum):
    """Types of edges in the knowledge graph."""

    EXPLAINS = "EXPLAINS"
    REFERS_TO = "REFERS_TO"
    CAUSED_BY = "CAUSED_BY"
    LEADS_TO = "LEADS_TO"
    TEMPORAL_NEXT = "TEMPORAL_NEXT"
    EXPLAINS_LINE_ITEM = "EXPLAINS_LINE_ITEM"
    DISCUSSES = "DISCUSSES"
    SEMANTICALLY_SIMILAR = "SEMANTICALLY_SIMILAR"
    BRIDGE = "BRIDGE"
    # Entity relationships
    MENTIONS_ENTITY = "MENTIONS_ENTITY"
    ENTITY_RELATED_TO = "ENTITY_RELATED_TO"


class NodeMetadata(BaseModel):
    """Metadata associated with a node."""

    filing_id: str = Field(..., description="Which filing this belongs to (e.g., AAPL-10K-2024)")
    period: str = Field(..., description="Fiscal period (e.g., FY2024, Q1-2024)")
    section: str | None = Field(default=None, description="Section identifier (e.g., Item 1, Note 3)")
    xbrl_tag: str | None = Field(default=None, description="XBRL tag if applicable")
    value: float | None = Field(default=None, description="Numeric value if applicable")
    unit: str | None = Field(default=None, description="Unit of value (e.g., USD, shares)")
    source_file: str | None = Field(default=None, description="Original source filename")
    char_offset: int | None = Field(default=None, description="Character offset in source document")
    table_id: str | None = Field(default=None, description="Table identifier for TABLE_ROW nodes")
    row_index: int | None = Field(default=None, description="Row index for TABLE_ROW nodes")
    note_number: int | None = Field(default=None, description="Note number for NOTE nodes")
    entity_type: str | None = Field(default=None, description="Entity type for ENTITY nodes")


class Node(BaseModel):
    """A node in the knowledge graph."""

    id: str = Field(..., description="Unique identifier (format: {filing_id}_{type}_{index})")
    type: NodeType = Field(..., description="Type of node")
    text: str = Field(..., description="Raw text content (max 2000 chars)")
    metadata: NodeMetadata = Field(..., description="Node metadata")

    # Embedding is stored separately due to size
    # embedding: np.ndarray  # 768-dim FinBERT embedding

    class Config:
        use_enum_values = True


class EdgeMetadata(BaseModel):
    """Metadata associated with an edge."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    filing_id: str | None = Field(default=None, description="Filing where relationship was found")
    algorithm: str | None = Field(default=None, description="Algorithm used (e.g., regex_pattern_v1)")
    score_breakdown: dict[str, float] | None = Field(default=None, description="Component scores")
    forced: bool = Field(default=False, description="Whether this is a forced bridge edge")


class Edge(BaseModel):
    """An edge in the knowledge graph."""

    id: str = Field(..., description="Unique identifier (format: {source_id}__{edge_type}__{target_id})")
    source_id: str = Field(..., description="Node ID of source")
    target_id: str = Field(..., description="Node ID of target")
    edge_type: EdgeType = Field(..., description="Type of edge")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    expert: str = Field(..., description="Which expert created this edge")
    evidence: str = Field(..., description="Text snippet supporting this edge (max 500 chars)")
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata)

    class Config:
        use_enum_values = True

    @classmethod
    def create_id(cls, source_id: str, edge_type: EdgeType, target_id: str) -> str:
        """Create a unique edge ID."""
        return f"{source_id}__{edge_type.value}__{target_id}"


class Filing(BaseModel):
    """Represents an SEC filing."""

    accession_number: str = Field(..., description="SEC accession number")
    filing_type: str = Field(..., description="10-K or 10-Q")
    filing_date: str = Field(..., description="Filing date")
    period: str = Field(..., description="Fiscal period")
    cik: str = Field(..., description="Company CIK (10-digit format)")
    company_name: str = Field(default="", description="Company name")
    document_url: str | None = Field(default=None, description="Primary document URL")
    xbrl_url: str | None = Field(default=None, description="XBRL document URL")


class Metrics(BaseModel):
    """Evaluation metrics for an expert."""

    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1: float = Field(..., ge=0.0, le=1.0)
    true_positives: int = Field(..., ge=0)
    false_positives: int = Field(..., ge=0)
    false_negatives: int = Field(..., ge=0)
    confidence_calibration: float | None = Field(default=None)

    @classmethod
    def calculate(cls, tp: int, fp: int, fn: int) -> "Metrics":
        """Calculate metrics from counts."""
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return cls(
            precision=precision,
            recall=recall,
            f1=f1,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
        )


class GraphStats(BaseModel):
    """Statistics about the knowledge graph."""

    connected_components: int
    is_connected: bool
    total_nodes: int
    total_edges: int
    isolated_nodes: int
    average_degree: float
    max_degree: int
    min_degree: int
    largest_component_size: int
    bridge_edges: int
    nodes_by_type: dict[str, int]
    edges_by_expert: dict[str, int]
    edges_by_type: dict[str, int]
