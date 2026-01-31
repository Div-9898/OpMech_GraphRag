"""
Edge Reward/Penalty System for OpMech-GraphRAG

This system scores edges during traversal to encourage:
- Domain crossing (financial ↔ narrative)
- Query relevance (edges leading to answer)
- Path quality (high confidence, diverse perspectives)

And discourage:
- Semantic drift (similar → similar chains)
- Domain isolation (staying in one type)
- Low-value expansion (many edges, no new info)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Callable
from enum import Enum
import numpy as np
from loguru import logger


class NodeDomain(Enum):
    """Domain classification for nodes."""
    FINANCIAL = "financial"      # FINANCIAL_LINE, TABLE_ROW
    NARRATIVE = "narrative"      # TEXT_SECTION, NOTE
    ENTITY = "entity"           # ENTITY
    UNKNOWN = "unknown"


class EdgeCategory(Enum):
    """Categorization of edge types by their exploration value."""
    BRIDGE = "bridge"           # Connects domains (high value)
    STRUCTURAL = "structural"   # Within-domain structure (medium value)
    CAUSAL = "causal"          # Cause-effect relationships (high value)
    SEMANTIC = "semantic"       # Similarity-based (low value, prone to drift)
    ENTITY_LINK = "entity"      # Entity connections (medium value)


@dataclass
class EdgeScore:
    """Complete score breakdown for an edge traversal decision."""
    edge_type: str
    source_id: str
    target_id: str

    # Base scores
    confidence: float              # From MoE expert (0-1)
    path_confidence: float         # Accumulated path confidence (0-1)

    # Reward components
    domain_crossing_reward: float = 0.0    # Crossing financial ↔ narrative
    query_relevance_reward: float = 0.0    # Target node relevant to query
    novelty_reward: float = 0.0            # Target brings new information
    bridge_edge_reward: float = 0.0        # Using a bridge edge type
    convergence_reward: float = 0.0        # Moving toward other operator's territory

    # Penalty components
    semantic_drift_penalty: float = 0.0    # Following similarity chains
    domain_isolation_penalty: float = 0.0  # Staying in same domain too long
    low_confidence_penalty: float = 0.0    # Edge confidence below threshold
    redundancy_penalty: float = 0.0        # Target similar to already-visited nodes
    fanout_penalty: float = 0.0            # Source has too many outgoing edges

    # Final score
    total_score: float = 0.0

    def compute_total(self, weights: 'ScoringWeights') -> float:
        """Compute weighted total score."""
        rewards = (
            weights.domain_crossing * self.domain_crossing_reward +
            weights.query_relevance * self.query_relevance_reward +
            weights.novelty * self.novelty_reward +
            weights.bridge_edge * self.bridge_edge_reward +
            weights.convergence * self.convergence_reward
        )

        penalties = (
            weights.semantic_drift * self.semantic_drift_penalty +
            weights.domain_isolation * self.domain_isolation_penalty +
            weights.low_confidence * self.low_confidence_penalty +
            weights.redundancy * self.redundancy_penalty +
            weights.fanout * self.fanout_penalty
        )

        # Base score from confidence
        base = self.confidence * self.path_confidence

        # Total = base + rewards - penalties, clamped to [0, 1]
        self.total_score = np.clip(base + rewards - penalties, 0.0, 1.0)
        return self.total_score


@dataclass
class ScoringWeights:
    """
    Weights for reward/penalty components.
    These should vary based on explore_weight!
    """
    # Reward weights
    domain_crossing: float = 0.25
    query_relevance: float = 0.30
    novelty: float = 0.15
    bridge_edge: float = 0.15
    convergence: float = 0.15

    # Penalty weights
    semantic_drift: float = 0.30
    domain_isolation: float = 0.20
    low_confidence: float = 0.15
    redundancy: float = 0.20
    fanout: float = 0.15

    @classmethod
    def from_explore_weight(cls, explore_weight: float) -> 'ScoringWeights':
        """
        Create weights based on explore/exploit balance.

        EXPLOIT (w→0): Prioritize confidence, penalize drift heavily
        EXPLORE (w→1): Prioritize novelty, relax drift penalties

        Adjusted: Increased penalty weights to prevent explosion in hop 1.
        """
        w = explore_weight

        return cls(
            # Rewards
            domain_crossing=0.20 + 0.10 * w,      # 0.20 → 0.30 (more important when exploring)
            query_relevance=0.35 - 0.10 * w,      # 0.35 → 0.25 (less strict when exploring)
            novelty=0.10 + 0.15 * w,              # 0.10 → 0.25 (much more important when exploring)
            bridge_edge=0.15,                      # constant
            convergence=0.20 - 0.10 * w,          # 0.20 → 0.10 (less important when exploring)

            # Penalties (increased to prevent explosion)
            semantic_drift=0.50 - 0.15 * w,       # 0.50 → 0.35 (was 0.40 → 0.25)
            domain_isolation=0.40 - 0.10 * w,     # 0.40 → 0.30 (was 0.25 → 0.15)
            low_confidence=0.25 - 0.10 * w,       # 0.25 → 0.15 (was 0.20 → 0.10)
            redundancy=0.30 - 0.05 * w,           # 0.30 → 0.25 (was 0.25 → 0.20)
            fanout=0.35 - 0.10 * w,               # 0.35 → 0.25 (was 0.20 → 0.10)
        )


class TraversalContext:
    """
    Maintains context during traversal for computing rewards/penalties.
    """

    def __init__(
        self,
        query_embedding: np.ndarray,
        embed_fn: Callable[[str], np.ndarray],
        other_operator_nodes: Set[str] = None
    ):
        self.query_embedding = query_embedding
        self.embed_fn = embed_fn
        self.other_operator_nodes = other_operator_nodes or set()

        # Tracking state
        self.visited_nodes: Set[str] = set()
        self.visited_domains: List[NodeDomain] = []
        self.domain_sequence: List[NodeDomain] = []  # Track domain switches
        self.semantic_chain_length: int = 0  # Consecutive SEMANTICALLY_SIMILAR edges
        self.node_embeddings_cache: Dict[str, np.ndarray] = {}
        self.edge_type_counts: Dict[str, int] = {}

    def get_node_domain(self, node_type: str) -> NodeDomain:
        """Classify node into domain."""
        if node_type in ["FINANCIAL_LINE", "TABLE_ROW"]:
            return NodeDomain.FINANCIAL
        elif node_type in ["TEXT_SECTION", "NOTE"]:
            return NodeDomain.NARRATIVE
        elif node_type == "ENTITY":
            return NodeDomain.ENTITY
        return NodeDomain.UNKNOWN

    def get_edge_category(self, edge_type: str) -> EdgeCategory:
        """Classify edge type."""
        if edge_type in ["EXPLAINS_LINE_ITEM", "DISCUSSES"]:
            return EdgeCategory.BRIDGE
        elif edge_type in ["TEMPORAL_NEXT", "REFERS_TO"]:
            return EdgeCategory.STRUCTURAL
        elif edge_type in ["CAUSED_BY", "LEADS_TO"]:
            return EdgeCategory.CAUSAL
        elif edge_type in ["SEMANTICALLY_SIMILAR"]:
            return EdgeCategory.SEMANTIC
        elif edge_type in ["MENTIONS_ENTITY", "ENTITY_RELATED_TO"]:
            return EdgeCategory.ENTITY_LINK
        return EdgeCategory.STRUCTURAL

    def update_after_traversal(
        self,
        node_id: str,
        node_type: str,
        edge_type: str
    ):
        """Update context after traversing to a node."""
        self.visited_nodes.add(node_id)

        domain = self.get_node_domain(node_type)
        self.visited_domains.append(domain)
        self.domain_sequence.append(domain)

        # Track semantic chains
        if edge_type == "SEMANTICALLY_SIMILAR":
            self.semantic_chain_length += 1
        else:
            self.semantic_chain_length = 0

        # Track edge type usage
        self.edge_type_counts[edge_type] = self.edge_type_counts.get(edge_type, 0) + 1


class EdgeScorer:
    """
    Computes reward/penalty scores for edge traversal decisions.
    """

    # Edge type configurations
    BRIDGE_EDGES = {"EXPLAINS_LINE_ITEM", "DISCUSSES"}
    CAUSAL_EDGES = {"CAUSED_BY", "LEADS_TO"}
    SEMANTIC_EDGES = {"SEMANTICALLY_SIMILAR"}
    HIGH_FANOUT_EDGES = {"SEMANTICALLY_SIMILAR", "ENTITY_RELATED_TO"}

    # Thresholds
    SEMANTIC_CHAIN_LIMIT = 2        # Max consecutive semantic edges before heavy penalty
    DOMAIN_ISOLATION_LIMIT = 3      # Max nodes in same domain before penalty (lowered from 4)
    FANOUT_THRESHOLD = 15           # Edges from single node before penalty (lowered from 20)
    CONFIDENCE_THRESHOLD = 0.6      # Below this, apply low confidence penalty
    SIMILARITY_THRESHOLD = 0.85     # Above this, nodes are "redundant"

    def __init__(self, context: TraversalContext, weights: ScoringWeights):
        self.context = context
        self.weights = weights

    def score_edge(
        self,
        edge_type: str,
        edge_confidence: float,
        source_node: 'Node',
        target_node: 'Node',
        path_confidence: float,
        source_fanout: int,  # Number of outgoing edges from source
    ) -> EdgeScore:
        """
        Compute complete score for traversing this edge.
        """
        score = EdgeScore(
            edge_type=edge_type,
            source_id=source_node.id,
            target_id=target_node.id,
            confidence=edge_confidence,
            path_confidence=path_confidence,
        )

        # Compute rewards
        score.domain_crossing_reward = self._compute_domain_crossing_reward(
            source_node, target_node
        )
        score.query_relevance_reward = self._compute_query_relevance_reward(
            target_node
        )
        score.novelty_reward = self._compute_novelty_reward(target_node)
        score.bridge_edge_reward = self._compute_bridge_edge_reward(edge_type)
        score.convergence_reward = self._compute_convergence_reward(target_node)

        # Compute penalties
        score.semantic_drift_penalty = self._compute_semantic_drift_penalty(edge_type)
        score.domain_isolation_penalty = self._compute_domain_isolation_penalty(
            target_node
        )
        score.low_confidence_penalty = self._compute_low_confidence_penalty(
            edge_confidence
        )
        score.redundancy_penalty = self._compute_redundancy_penalty(target_node)
        score.fanout_penalty = self._compute_fanout_penalty(source_fanout, edge_type)

        # Compute total
        score.compute_total(self.weights)

        return score

    # ─────────────────────────────────────────────────────────────────────
    # REWARD COMPUTATIONS
    # ─────────────────────────────────────────────────────────────────────

    def _compute_domain_crossing_reward(
        self,
        source_node: 'Node',
        target_node: 'Node'
    ) -> float:
        """
        Reward for crossing between financial and narrative domains.
        This encourages multi-perspective exploration.
        """
        source_domain = self.context.get_node_domain(source_node.type)
        target_domain = self.context.get_node_domain(target_node.type)

        # Financial ↔ Narrative crossing gets full reward
        if (source_domain == NodeDomain.FINANCIAL and target_domain == NodeDomain.NARRATIVE) or \
           (source_domain == NodeDomain.NARRATIVE and target_domain == NodeDomain.FINANCIAL):
            return 1.0

        # Entity can bridge domains - partial reward
        if source_domain == NodeDomain.ENTITY or target_domain == NodeDomain.ENTITY:
            return 0.5

        return 0.0

    def _compute_query_relevance_reward(self, target_node: 'Node') -> float:
        """
        Reward for edges leading to query-relevant nodes.
        Uses embedding similarity.
        """
        # Get or compute target embedding
        if target_node.id in self.context.node_embeddings_cache:
            target_emb = self.context.node_embeddings_cache[target_node.id]
        elif target_node.embedding is not None:
            target_emb = target_node.embedding
            self.context.node_embeddings_cache[target_node.id] = target_emb
        else:
            # Compute embedding from text
            text = target_node.text[:512] if target_node.text else ""
            if not text:
                return 0.0
            target_emb = self.context.embed_fn(text)
            self.context.node_embeddings_cache[target_node.id] = target_emb

        # Compute similarity to query
        norm_q = np.linalg.norm(self.context.query_embedding)
        norm_t = np.linalg.norm(target_emb)

        if norm_q > 0 and norm_t > 0:
            similarity = np.dot(self.context.query_embedding, target_emb) / (norm_q * norm_t)
        else:
            return 0.0

        # Scale: similarity 0.7+ gets reward
        if similarity > 0.7:
            return (similarity - 0.7) / 0.3  # Scale 0.7-1.0 → 0-1
        return 0.0

    def _compute_novelty_reward(self, target_node: 'Node') -> float:
        """
        Reward for finding genuinely new information.
        Penalizes nodes too similar to already visited nodes.
        """
        if not self.context.visited_nodes:
            return 1.0  # First node is always novel

        # Get target embedding
        if target_node.id in self.context.node_embeddings_cache:
            target_emb = self.context.node_embeddings_cache[target_node.id]
        elif target_node.embedding is not None:
            target_emb = target_node.embedding
            self.context.node_embeddings_cache[target_node.id] = target_emb
        else:
            return 0.5  # Can't compute, assume moderate novelty

        # Compare to visited nodes (sample if too many)
        visited_sample = list(self.context.visited_nodes)[:20]
        max_similarity = 0.0

        for visited_id in visited_sample:
            if visited_id in self.context.node_embeddings_cache:
                visited_emb = self.context.node_embeddings_cache[visited_id]
                norm_t = np.linalg.norm(target_emb)
                norm_v = np.linalg.norm(visited_emb)
                if norm_t > 0 and norm_v > 0:
                    sim = np.dot(target_emb, visited_emb) / (norm_t * norm_v)
                    max_similarity = max(max_similarity, sim)

        # Novelty = inverse of max similarity to visited
        # High similarity (>0.9) → low novelty (0)
        # Low similarity (<0.5) → high novelty (1)
        novelty = 1.0 - np.clip((max_similarity - 0.5) / 0.4, 0, 1)
        return novelty

    def _compute_bridge_edge_reward(self, edge_type: str) -> float:
        """
        Reward for using bridge edges that connect domains.
        """
        if edge_type in self.BRIDGE_EDGES:
            return 1.0
        if edge_type in self.CAUSAL_EDGES:
            return 0.7  # Causal edges also valuable
        return 0.0

    def _compute_convergence_reward(self, target_node: 'Node') -> float:
        """
        Reward for moving toward nodes the other operator found.
        Encourages operators to converge on shared evidence.
        """
        if target_node.id in self.context.other_operator_nodes:
            return 1.0  # Direct hit!

        # Could also check if target is connected to other operator's nodes
        # For now, just direct membership
        return 0.0

    # ─────────────────────────────────────────────────────────────────────
    # PENALTY COMPUTATIONS
    # ─────────────────────────────────────────────────────────────────────

    def _compute_semantic_drift_penalty(self, edge_type: str) -> float:
        """
        Penalty for following chains of SEMANTICALLY_SIMILAR edges.
        This is the main cause of the "echo chamber" problem.
        """
        if edge_type != "SEMANTICALLY_SIMILAR":
            return 0.0

        chain_length = self.context.semantic_chain_length

        # First semantic edge: small penalty
        # Second: medium penalty
        # Third+: heavy penalty (exponential)
        if chain_length == 0:
            return 0.2
        elif chain_length == 1:
            return 0.5
        else:
            # Exponential penalty for long chains
            return min(1.0, 0.5 + 0.25 * (chain_length - 1))

    def _compute_domain_isolation_penalty(self, target_node: 'Node') -> float:
        """
        Penalty for staying in the same domain too long.
        Encourages crossing between financial and narrative.
        """
        if len(self.context.domain_sequence) < 2:
            return 0.0

        target_domain = self.context.get_node_domain(target_node.type)

        # Count consecutive nodes in same domain
        consecutive = 0
        for domain in reversed(self.context.domain_sequence):
            if domain == target_domain:
                consecutive += 1
            else:
                break

        # Penalty increases with consecutive same-domain nodes
        if consecutive >= self.DOMAIN_ISOLATION_LIMIT:
            return min(1.0, 0.3 + 0.15 * (consecutive - self.DOMAIN_ISOLATION_LIMIT))
        elif consecutive >= 2:
            return 0.1 * consecutive

        return 0.0

    def _compute_low_confidence_penalty(self, edge_confidence: float) -> float:
        """
        Penalty for traversing low-confidence edges.
        """
        if edge_confidence >= self.CONFIDENCE_THRESHOLD:
            return 0.0

        # Linear penalty below threshold
        return (self.CONFIDENCE_THRESHOLD - edge_confidence) / self.CONFIDENCE_THRESHOLD

    def _compute_redundancy_penalty(self, target_node: 'Node') -> float:
        """
        Penalty for visiting nodes too similar to already-visited ones.
        Different from novelty_reward - this is a hard penalty.
        """
        if target_node.id in self.context.visited_nodes:
            return 1.0  # Already visited!

        # Check embedding similarity to visited
        if target_node.id in self.context.node_embeddings_cache:
            target_emb = self.context.node_embeddings_cache[target_node.id]
        elif target_node.embedding is not None:
            target_emb = target_node.embedding
        else:
            return 0.0  # Can't compute, no penalty

        for visited_id in list(self.context.visited_nodes)[:10]:
            if visited_id in self.context.node_embeddings_cache:
                visited_emb = self.context.node_embeddings_cache[visited_id]
                norm_t = np.linalg.norm(target_emb)
                norm_v = np.linalg.norm(visited_emb)
                if norm_t > 0 and norm_v > 0:
                    sim = np.dot(target_emb, visited_emb) / (norm_t * norm_v)
                    if sim > self.SIMILARITY_THRESHOLD:
                        return 0.8  # Very similar to existing node

        return 0.0

    def _compute_fanout_penalty(self, source_fanout: int, edge_type: str) -> float:
        """
        Penalty for following edges from high-fanout nodes.
        High-fanout nodes (especially via SEMANTICALLY_SIMILAR) lead to explosion.

        Made more aggressive to prevent explosion from dense edges like DISCUSSES (avg 38).
        """
        if source_fanout <= self.FANOUT_THRESHOLD:
            return 0.0

        # Base penalty for high fanout - more aggressive scaling
        # For fanout=38: (38-15)/25 = 0.92 (was 0.36)
        base_penalty = min(1.0, (source_fanout - self.FANOUT_THRESHOLD) / 25)

        # Extra penalty for high-fanout edge types
        if edge_type in self.HIGH_FANOUT_EDGES:
            return min(1.0, base_penalty * 1.5)

        return base_penalty


def create_scorer(
    query_embedding: np.ndarray,
    embed_fn: Callable[[str], np.ndarray],
    explore_weight: float,
    other_operator_nodes: Set[str] = None
) -> Tuple[EdgeScorer, TraversalContext]:
    """
    Factory function to create scorer with appropriate weights.
    """
    context = TraversalContext(
        query_embedding=query_embedding,
        embed_fn=embed_fn,
        other_operator_nodes=other_operator_nodes
    )

    weights = ScoringWeights.from_explore_weight(explore_weight)
    scorer = EdgeScorer(context, weights)

    return scorer, context
