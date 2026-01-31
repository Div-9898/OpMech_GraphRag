"""Data classes for OpMech-GraphRAG system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class OutputMode(Enum):
    """Output mode based on divergence level."""
    EXPLOIT = "exploit"       # Single confident answer
    ADAPTIVE = "adaptive"     # Merged answer with caveats
    EXPLORE = "explore"       # Dual hypothesis with uncertainty


@dataclass
class Node:
    """Graph node representation."""
    id: str
    type: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None


@dataclass
class Edge:
    """Graph edge representation."""
    source_id: str
    target_id: str
    type: str
    confidence: float       # FROM MoE Graph Builder (0.0 - 1.0)
    expert: str             # Which expert created this edge
    evidence: str = ""


@dataclass
class TraversedNode:
    """Node with path confidence from traversal."""
    node: Node
    path_confidence: float      # Product of edge confidences along path (with decay)
    incoming_edge: Optional[Edge]
    hop_distance: int


@dataclass
class BeliefState:
    """State after running an operator."""
    evidence: List[Node]
    answer: str

    # Edge confidence fields
    edge_confidences: List[float]           # All edge confidences from traversal (for delta_C)
    evidence_confidences: List[float]       # Per-evidence path confidence (for ranking)
    mean_path_confidence: float             # Aggregate path confidence (for operator scoring)

    operator_path: str  # "structure_first" or "narrative_first"
    hops_used: int
    seeds_used: List[str]
    edges_traversed: List[Edge]


@dataclass
class TraversalStrategy:
    """Parameters controlling graph traversal."""

    # Depth control
    max_hops: int           # Maximum traversal depth (1-6)
    current_hop: int        # Current hop in iteration

    # Width control
    seeds_per_operator: int  # Initial seed nodes (3-10)
    nodes_per_hop: int       # Max nodes to expand per hop (5-20)

    # Edge selection
    edge_types_A: List[str]  # Edge types for operator A
    edge_types_B: List[str]  # Edge types for operator B

    # Pruning control
    min_edge_confidence: float  # Minimum edge confidence to traverse (0.3-0.8)
    top_k_evidence: int         # Final evidence selection (10-30)

    # Confidence weighting parameters
    confidence_decay: float     # Decay factor per hop (0.85-0.95)
    relevance_weight: float     # Weight for query-embedding similarity (0.4-0.7)
    confidence_weight: float    # Weight for path confidence (0.3-0.6)

    # Output control
    output_mode: str         # "exploit", "adaptive", "explore"

    # Thresholds (for reference)
    tau_low: float           # Below this: exploit
    tau_high: float          # Above this: explore

    # Explore weight (for scoring system)
    explore_weight: float = 0.5  # 0.0 = exploit, 1.0 = explore


@dataclass
class CommutatorResult:
    """Complete commutator computation result."""

    # Individual divergence components
    delta_E: float  # Evidence divergence
    delta_V: float  # Structural divergence
    delta_A: float  # Answer divergence
    delta_C: float  # Confidence divergence

    # Combined score
    combined: float

    # Metadata
    weights: Dict[str, float]
    hop: int

    # Operator scores (for diagnostics)
    operator_A_score: float  # Overall quality score for operator A
    operator_B_score: float  # Overall quality score for operator B


@dataclass
class QueryResult:
    """Final output of the system."""
    answer: str
    confidence: float
    mode: OutputMode
    hops_used: int
    trajectory: List[CommutatorResult]
    evidence_A: List[Node]
    evidence_B: List[Node]
    answer_A: str
    answer_B: str
    reasoning: str
    operator_scores: Dict[str, float]

    # Confidence diagnostics
    path_confidence_A: float = 0.0
    path_confidence_B: float = 0.0
    edge_conf_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
