# OpMech-GraphRAG Diagnosis and Fix Prompt v2

## Context

You are working on OpMech-GraphRAG, a system that uses two operators (Structure-First and Narrative-First) to query a knowledge graph built from Apple SEC filings. The system computes divergence between operators to decide whether to EXPLOIT (confident answer) or EXPLORE (hedged answer).

**The system is implemented and running, but producing incorrect results.**

---

## Current System Output (The Problem)

For the query: **"What was Apple's total revenue in FY2023?"**

```
Mode: ADAPTIVE (should be EXPLOIT)
Confidence: 51.9% (should be >75%)

Divergence at hop 1: Δ=0.596 (Δ_E=1.000, Δ_V=1.000, Δ_A=0.038, Δ_C=0.424)
Divergence at hop 2: Δ=0.602 (Δ_E=1.000, Δ_V=1.000, Δ_A=0.051, Δ_C=0.434)

OperatorA: Traversed 31 nodes, 129 edges
OperatorB: Traversed 1134 nodes, 5101 edges  ← 36x MORE!

Answer: Confused, mentioned $212.98B (cost of sales) and $468B (wrong estimate)
Correct Answer: ~$383.3 billion
```

---

## Root Cause Analysis

### The REAL Problem: Not Too Many Nodes, But WRONG Exploration

**IMPORTANT**: We should NOT fix this with hard caps on nodes. That would defeat the entire explore/exploit architecture:

```
EXPLOIT Mode: shallow traversal (2 hops, ~50 nodes)
EXPLORE Mode: deep traversal (6 hops, ~500 nodes)

If we cap at 200 nodes → EXPLORE becomes meaningless!
```

### The Actual Issues:

#### Issue 1: SEMANTICALLY_SIMILAR Causes "Semantic Drift"

```
Current Operator B behavior:
  TEXT_SECTION →[SEMANTICALLY_SIMILAR]→ TEXT_SECTION →[SEMANTICALLY_SIMILAR]→ TEXT_SECTION
                                                     →[SEMANTICALLY_SIMILAR]→ TEXT_SECTION
                                                     →[SEMANTICALLY_SIMILAR]→ TEXT_SECTION
                                                     ... (1000+ nodes, all similar text!)

This is NOT exploration - it's an echo chamber of similar text.
```

#### Issue 2: Operators Have ZERO Shared Edges

```python
# Current edge configuration
OPERATOR_A_EDGES = ["TEMPORAL_NEXT", "EXPLAINS_LINE_ITEM", "REFERS_TO"]
OPERATOR_B_EDGES = ["CAUSED_BY", "DISCUSSES", "MENTIONS_ENTITY", "SEMANTICALLY_SIMILAR"]

# Intersection = {} ← EMPTY! Operators can NEVER find the same paths!
```

#### Issue 3: No Domain Crossing

```
Operator A: Stays in "Financial World"
  FINANCIAL_LINE → FINANCIAL_LINE → FINANCIAL_LINE

Operator B: Stays in "Narrative World"  
  TEXT_SECTION → TEXT_SECTION → TEXT_SECTION

Neither crosses to the other domain!
```

#### Issue 4: No Incentive for Quality Exploration

Currently, all edges are treated equally. There's no reward for:
- Finding nodes that connect financial ↔ narrative
- Discovering nodes that answer the query directly
- Traversing high-confidence paths

And no penalty for:
- Semantic drift (similar → similar → similar)
- Staying in one domain
- Following low-value edges

---

## The Solution: Edge Reward/Penalty System

Instead of capping nodes, implement a **traversal scoring system** that rewards good exploration and penalizes bad exploration.

### Core Philosophy

```
GOOD EXPLORATION = Different perspectives on the SAME entities
BAD EXPLORATION = More nodes from the SAME perspective

We want: Revenue → Explanation → Causes → Risks → Supporting Data (5 perspectives)
Not:     Revenue → Similar text → Similar text → Similar text (1 perspective, 1000 nodes)
```

---

## Task 1: Implement the Reward/Penalty Traversal System

### 1.1 Create the Edge Scoring System

Create `src/opmech/edge_scoring.py`:

```python
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
from typing import Dict, List, Set, Optional, Tuple
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
        """
        w = explore_weight
        
        return cls(
            # Rewards
            domain_crossing=0.20 + 0.10 * w,      # 0.20 → 0.30 (more important when exploring)
            query_relevance=0.35 - 0.10 * w,      # 0.35 → 0.25 (less strict when exploring)
            novelty=0.10 + 0.15 * w,              # 0.10 → 0.25 (much more important when exploring)
            bridge_edge=0.15,                      # constant
            convergence=0.20 - 0.10 * w,          # 0.20 → 0.10 (less important when exploring)
            
            # Penalties
            semantic_drift=0.40 - 0.15 * w,       # 0.40 → 0.25 (relax when exploring)
            domain_isolation=0.25 - 0.10 * w,     # 0.25 → 0.15 (relax when exploring)
            low_confidence=0.20 - 0.10 * w,       # 0.20 → 0.10 (accept lower conf when exploring)
            redundancy=0.25 - 0.05 * w,           # 0.25 → 0.20 (slight relax)
            fanout=0.20 - 0.10 * w,               # 0.20 → 0.10 (allow more fanout when exploring)
        )


class TraversalContext:
    """
    Maintains context during traversal for computing rewards/penalties.
    """
    
    def __init__(
        self,
        query_embedding: np.ndarray,
        embed_fn,
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
    DOMAIN_ISOLATION_LIMIT = 4      # Max nodes in same domain before penalty
    FANOUT_THRESHOLD = 20           # Edges from single node before penalty
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
        else:
            target_emb = self.context.embed_fn(target_node.text[:512])
            self.context.node_embeddings_cache[target_node.id] = target_emb
        
        # Compute similarity to query
        similarity = np.dot(self.context.query_embedding, target_emb)
        
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
        else:
            target_emb = self.context.embed_fn(target_node.text[:512])
            self.context.node_embeddings_cache[target_node.id] = target_emb
        
        # Compare to visited nodes (sample if too many)
        visited_sample = list(self.context.visited_nodes)[:20]
        max_similarity = 0.0
        
        for visited_id in visited_sample:
            if visited_id in self.context.node_embeddings_cache:
                visited_emb = self.context.node_embeddings_cache[visited_id]
                sim = np.dot(target_emb, visited_emb)
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
        else:
            return 0.0  # Can't compute, no penalty
        
        for visited_id in list(self.context.visited_nodes)[:10]:
            if visited_id in self.context.node_embeddings_cache:
                visited_emb = self.context.node_embeddings_cache[visited_id]
                sim = np.dot(target_emb, visited_emb)
                if sim > self.SIMILARITY_THRESHOLD:
                    return 0.8  # Very similar to existing node
        
        return 0.0
    
    def _compute_fanout_penalty(self, source_fanout: int, edge_type: str) -> float:
        """
        Penalty for following edges from high-fanout nodes.
        High-fanout nodes (especially via SEMANTICALLY_SIMILAR) lead to explosion.
        """
        if source_fanout <= self.FANOUT_THRESHOLD:
            return 0.0
        
        # Base penalty for high fanout
        base_penalty = min(1.0, (source_fanout - self.FANOUT_THRESHOLD) / 50)
        
        # Extra penalty for high-fanout edge types
        if edge_type in self.HIGH_FANOUT_EDGES:
            return min(1.0, base_penalty * 1.5)
        
        return base_penalty


def create_scorer(
    query_embedding: np.ndarray,
    embed_fn,
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
```

---

### 1.2 Integrate Scorer into Graph Traversal

Update `src/opmech/graph_interface.py`:

```python
from .edge_scoring import EdgeScorer, TraversalContext, create_scorer, EdgeScore

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
    min_edge_score: float = 0.3,  # Minimum score to traverse
) -> Tuple[List[TraversedNode], List[Edge], List[EdgeScore]]:
    """
    Score-based graph traversal using reward/penalty system.
    
    Instead of just filtering by confidence, we compute a full score
    for each potential edge and only traverse high-scoring edges.
    """
    import heapq
    
    # Priority queue: (-score, node_id, hop_dist, incoming_edge, path_conf)
    frontier = []
    for seed_id in seed_ids:
        heapq.heappush(frontier, (-1.0, seed_id, 0, None, 1.0))
    
    visited: Dict[str, TraversedNode] = {}
    all_edges: List[Edge] = []
    all_scores: List[EdgeScore] = []  # For diagnostics
    
    with self.driver.session() as session:
        while frontier:
            neg_score, node_id, hop_dist, incoming_edge, path_conf = heapq.heappop(frontier)
            
            if node_id in visited:
                continue
            
            if hop_dist > hops:
                continue
            
            # Get node details
            node = self._get_node(session, node_id)
            if not node:
                continue
            
            # Record visit
            visited[node_id] = TraversedNode(
                node=node,
                path_confidence=path_conf,
                incoming_edge=incoming_edge,
                hop_distance=hop_dist
            )
            
            # Update context
            if incoming_edge:
                context.update_after_traversal(
                    node_id, node.type, incoming_edge.type
                )
            
            # Don't expand beyond max hops
            if hop_dist >= hops:
                continue
            
            # Get outgoing edges
            edge_query = """
                MATCH (source:Node {id: $node_id})-[r]->(target:Node)
                WHERE type(r) IN $edge_types
                AND r.confidence >= $min_conf
                WITH r, target, source
                OPTIONAL MATCH (source)-[all_out]->()
                WITH r, target, count(all_out) AS fanout
                RETURN target.id AS target_id, target.type AS target_type,
                       target.text AS target_text, type(r) AS edge_type,
                       r.confidence AS confidence, fanout
                ORDER BY r.confidence DESC
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
                    text=record["target_text"] or ""
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
                    confidence=record["confidence"]
                )
                all_edges.append(edge)
                
                # Compute new path confidence with decay
                new_path_conf = path_conf * record["confidence"] * confidence_decay
                
                # Add to frontier with score as priority
                heapq.heappush(
                    frontier,
                    (-edge_score.total_score, target_node.id, hop_dist + 1, edge, new_path_conf)
                )
    
    return list(visited.values()), all_edges, all_scores
```

---

### 1.3 Update Operators to Use Scoring

Update `src/opmech/operators.py`:

```python
from .edge_scoring import create_scorer, EdgeScorer, TraversalContext

class OperatorA:
    """Structure-First Operator with reward/penalty scoring."""
    
    def execute(
        self, 
        query: str, 
        strategy: TraversalStrategy,
        other_operator_evidence: Set[str] = None  # For convergence reward
    ) -> BeliefState:
        
        # Create query embedding
        query_embedding = self.embed_fn(query)
        
        # Create scorer with appropriate weights
        scorer, context = create_scorer(
            query_embedding=query_embedding,
            embed_fn=self.embed_fn,
            explore_weight=strategy.explore_weight,
            other_operator_nodes=other_operator_evidence
        )
        
        # Get seeds (unchanged)
        seeds = self._get_seeds(query, strategy)
        seed_ids = [s.id for s in seeds]
        
        # Get edge types based on explore weight
        edge_types = self._get_edge_types(strategy.explore_weight, strategy.max_hops)
        
        # Compute min_edge_score based on explore weight
        # EXPLOIT: require high scores (0.4)
        # EXPLORE: accept lower scores (0.2)
        min_edge_score = 0.4 - 0.2 * strategy.explore_weight
        
        # Traverse with scoring
        traversed, edges, scores = self.graph.traverse_with_scoring(
            seed_ids=seed_ids,
            edge_types=edge_types,
            hops=strategy.max_hops,
            max_per_hop=strategy.nodes_per_hop,
            min_confidence=strategy.min_edge_confidence,
            confidence_decay=strategy.confidence_decay,
            scorer=scorer,
            context=context,
            min_edge_score=min_edge_score
        )
        
        # Log score statistics
        if scores:
            logger.info(f"OperatorA: Scored {len(scores)} edges")
            avg_score = np.mean([s.total_score for s in scores])
            logger.debug(f"OperatorA: Avg edge score = {avg_score:.3f}")
            
            # Log reward/penalty breakdown
            avg_rewards = {
                "domain_crossing": np.mean([s.domain_crossing_reward for s in scores]),
                "query_relevance": np.mean([s.query_relevance_reward for s in scores]),
                "novelty": np.mean([s.novelty_reward for s in scores]),
            }
            avg_penalties = {
                "semantic_drift": np.mean([s.semantic_drift_penalty for s in scores]),
                "domain_isolation": np.mean([s.domain_isolation_penalty for s in scores]),
                "redundancy": np.mean([s.redundancy_penalty for s in scores]),
            }
            logger.debug(f"OperatorA: Avg rewards = {avg_rewards}")
            logger.debug(f"OperatorA: Avg penalties = {avg_penalties}")
        
        # Rest of execute (evidence ranking, etc.)
        ...
    
    def _get_edge_types(self, explore_weight: float, hop: int) -> List[str]:
        """
        Dynamic edge selection based on explore weight.
        
        EXPLOIT (w→0): Focus on structural + bridge edges
        EXPLORE (w→1): Add causal edges, limit semantic
        """
        # Always include bridges (key for domain crossing)
        edges = ["EXPLAINS_LINE_ITEM", "DISCUSSES"]
        
        # Structural edges (Operator A specialty)
        edges += ["TEMPORAL_NEXT", "REFERS_TO"]
        
        # Add causal edges when exploring
        if explore_weight > 0.4:
            edges += ["CAUSED_BY"]
        
        # Entity edges for broader exploration
        if explore_weight > 0.6:
            edges += ["MENTIONS_ENTITY"]
        
        # NOTE: We intentionally exclude SEMANTICALLY_SIMILAR
        # The scoring system will heavily penalize it anyway
        
        return edges


class OperatorB:
    """Narrative-First Operator with reward/penalty scoring."""
    
    def _get_edge_types(self, explore_weight: float, hop: int) -> List[str]:
        """
        Dynamic edge selection for Operator B.
        
        Key difference: Can use SEMANTICALLY_SIMILAR but only on hop 1
        and the scoring system will penalize chains.
        """
        # Always include bridges
        edges = ["EXPLAINS_LINE_ITEM", "DISCUSSES"]
        
        # Narrative operator specialty
        edges += ["CAUSED_BY", "MENTIONS_ENTITY"]
        
        # Add structural edges when exploiting (convergence with Op A)
        if explore_weight < 0.5:
            edges += ["TEMPORAL_NEXT"]
        
        # SEMANTICALLY_SIMILAR: only on hop 1, only when exploring
        # The scoring system will penalize chains anyway
        if explore_weight > 0.6 and hop == 1:
            edges.append("SEMANTICALLY_SIMILAR")
        
        return edges
```

---

### 1.4 Two-Phase Traversal with Convergence Sharing

Update the main query loop in `src/opmech/system.py`:

```python
def query(self, query_text: str) -> QueryResult:
    """
    Main query method with two-phase operator execution.
    
    Phase 1: Independent exploration
    Phase 2: Share evidence, re-explore with convergence rewards
    """
    logger.info(f"Processing query: {query_text}...")
    
    trajectory = []
    hop = 1
    max_hops = self.config.initial_max_hops
    
    # Initialize beliefs
    belief_A = None
    belief_B = None
    
    while hop <= max_hops:
        logger.info(f"Hop {hop}/{max_hops}")
        
        # Compute strategy
        if trajectory:
            strategy = self.controller.compute_strategy(
                trajectory[-1].combined, trajectory
            )
        else:
            strategy = self.controller.get_initial_strategy()
        
        # ─────────────────────────────────────────────────────────
        # PHASE 1: Independent exploration (no convergence sharing)
        # ─────────────────────────────────────────────────────────
        if hop == 1:
            belief_A = self.operator_A.execute(
                query_text, 
                strategy,
                other_operator_evidence=None  # No sharing yet
            )
            belief_B = self.operator_B.execute(
                query_text, 
                strategy,
                other_operator_evidence=None
            )
        
        # ─────────────────────────────────────────────────────────
        # PHASE 2: Convergence-aware re-exploration
        # ─────────────────────────────────────────────────────────
        else:
            # Share evidence from previous hop
            evidence_A_ids = {n.id for n in belief_A.evidence}
            evidence_B_ids = {n.id for n in belief_B.evidence}
            
            # Re-run with convergence rewards enabled
            belief_A = self.operator_A.execute(
                query_text,
                strategy,
                other_operator_evidence=evidence_B_ids  # Share B's evidence
            )
            belief_B = self.operator_B.execute(
                query_text,
                strategy,
                other_operator_evidence=evidence_A_ids  # Share A's evidence
            )
        
        # Compute divergence
        commutator = self.compute_commutator(belief_A, belief_B, query_text)
        trajectory.append(commutator)
        
        logger.info(
            f"Divergence at hop {hop}: Δ={commutator.combined:.3f} "
            f"(Δ_E={commutator.delta_E:.3f}, Δ_V={commutator.delta_V:.3f}, "
            f"Δ_A={commutator.delta_A:.3f}, Δ_C={commutator.delta_C:.3f})"
        )
        
        # Check stopping conditions
        stop, reason = self._check_stopping_conditions(commutator, trajectory, hop)
        if stop:
            logger.info(f"Stopping: {reason}")
            break
        
        # Update max_hops based on trajectory
        max_hops = self._update_max_hops(strategy.explore_weight, trajectory)
        hop += 1
    
    # Generate final answer
    return self._generate_answer(query_text, belief_A, belief_B, trajectory)
```

---

## Task 2: Diagnostic Tools

Create `src/opmech/diagnostics.py` to understand scoring behavior:

```python
"""
Diagnostic tools for analyzing reward/penalty scoring.
"""

from typing import List, Dict
from .edge_scoring import EdgeScore
import numpy as np
from loguru import logger


class ScoringDiagnostics:
    """Analyze edge scoring patterns to understand traversal behavior."""
    
    def __init__(self, scores: List[EdgeScore]):
        self.scores = scores
    
    def summarize(self) -> Dict:
        """Generate summary statistics."""
        if not self.scores:
            return {"error": "No scores to analyze"}
        
        # Basic stats
        total_scores = [s.total_score for s in self.scores]
        
        # Reward breakdown
        rewards = {
            "domain_crossing": [s.domain_crossing_reward for s in self.scores],
            "query_relevance": [s.query_relevance_reward for s in self.scores],
            "novelty": [s.novelty_reward for s in self.scores],
            "bridge_edge": [s.bridge_edge_reward for s in self.scores],
            "convergence": [s.convergence_reward for s in self.scores],
        }
        
        # Penalty breakdown
        penalties = {
            "semantic_drift": [s.semantic_drift_penalty for s in self.scores],
            "domain_isolation": [s.domain_isolation_penalty for s in self.scores],
            "low_confidence": [s.low_confidence_penalty for s in self.scores],
            "redundancy": [s.redundancy_penalty for s in self.scores],
            "fanout": [s.fanout_penalty for s in self.scores],
        }
        
        # Edge type distribution
        edge_types = {}
        for s in self.scores:
            edge_types[s.edge_type] = edge_types.get(s.edge_type, 0) + 1
        
        return {
            "total_edges_scored": len(self.scores),
            "score_stats": {
                "mean": np.mean(total_scores),
                "std": np.std(total_scores),
                "min": np.min(total_scores),
                "max": np.max(total_scores),
                "median": np.median(total_scores),
            },
            "reward_means": {k: np.mean(v) for k, v in rewards.items()},
            "penalty_means": {k: np.mean(v) for k, v in penalties.items()},
            "edge_type_counts": edge_types,
            "edges_above_threshold": sum(1 for s in total_scores if s >= 0.3),
            "edges_below_threshold": sum(1 for s in total_scores if s < 0.3),
        }
    
    def find_problematic_patterns(self) -> List[str]:
        """Identify issues with scoring patterns."""
        issues = []
        summary = self.summarize()
        
        # Check for semantic drift dominance
        if summary["penalty_means"]["semantic_drift"] > 0.3:
            issues.append(
                f"HIGH SEMANTIC DRIFT PENALTY: {summary['penalty_means']['semantic_drift']:.3f} "
                f"- Too many SEMANTICALLY_SIMILAR chains"
            )
        
        # Check for domain isolation
        if summary["penalty_means"]["domain_isolation"] > 0.2:
            issues.append(
                f"HIGH DOMAIN ISOLATION: {summary['penalty_means']['domain_isolation']:.3f} "
                f"- Operators not crossing domains"
            )
        
        # Check for low domain crossing rewards
        if summary["reward_means"]["domain_crossing"] < 0.1:
            issues.append(
                f"LOW DOMAIN CROSSING: {summary['reward_means']['domain_crossing']:.3f} "
                f"- Operators staying in their silos"
            )
        
        # Check for low convergence
        if summary["reward_means"]["convergence"] < 0.05:
            issues.append(
                f"LOW CONVERGENCE: {summary['reward_means']['convergence']:.3f} "
                f"- Operators not finding shared evidence"
            )
        
        # Check for too many low-score edges
        pct_below = summary["edges_below_threshold"] / summary["total_edges_scored"]
        if pct_below > 0.7:
            issues.append(
                f"HIGH REJECTION RATE: {pct_below*100:.1f}% edges below threshold "
                f"- May need to relax penalties"
            )
        
        return issues
    
    def print_report(self):
        """Print human-readable diagnostic report."""
        summary = self.summarize()
        issues = self.find_problematic_patterns()
        
        print("\n" + "=" * 60)
        print("EDGE SCORING DIAGNOSTIC REPORT")
        print("=" * 60)
        
        print(f"\nTotal edges scored: {summary['total_edges_scored']}")
        print(f"Edges above threshold (≥0.3): {summary['edges_above_threshold']}")
        print(f"Edges below threshold (<0.3): {summary['edges_below_threshold']}")
        
        print("\n--- Score Statistics ---")
        stats = summary["score_stats"]
        print(f"Mean: {stats['mean']:.3f}, Std: {stats['std']:.3f}")
        print(f"Min: {stats['min']:.3f}, Max: {stats['max']:.3f}")
        
        print("\n--- Reward Means ---")
        for k, v in summary["reward_means"].items():
            bar = "█" * int(v * 20)
            print(f"  {k:<20}: {v:.3f} {bar}")
        
        print("\n--- Penalty Means ---")
        for k, v in summary["penalty_means"].items():
            bar = "▓" * int(v * 20)
            print(f"  {k:<20}: {v:.3f} {bar}")
        
        print("\n--- Edge Type Distribution ---")
        for edge_type, count in sorted(summary["edge_type_counts"].items(), 
                                       key=lambda x: -x[1]):
            print(f"  {edge_type:<25}: {count}")
        
        if issues:
            print("\n--- ISSUES DETECTED ---")
            for issue in issues:
                print(f"  ⚠️  {issue}")
        else:
            print("\n✅ No major issues detected")
        
        print("\n" + "=" * 60)
```

---

## Task 3: Updated Test Suite

Create `tests/test_scoring_system.py`:

```python
"""
Tests for the reward/penalty scoring system.
"""

import pytest
import numpy as np
from src.opmech.edge_scoring import (
    EdgeScorer, TraversalContext, ScoringWeights,
    EdgeScore, NodeDomain, EdgeCategory
)


class TestScoringWeights:
    """Test that weights adapt to explore_weight correctly."""
    
    def test_exploit_weights(self):
        """EXPLOIT mode should have high penalties, moderate rewards."""
        weights = ScoringWeights.from_explore_weight(0.0)
        
        # High penalties for drift
        assert weights.semantic_drift >= 0.35
        assert weights.domain_isolation >= 0.20
        
        # Moderate rewards
        assert weights.query_relevance >= 0.30
    
    def test_explore_weights(self):
        """EXPLORE mode should relax penalties, increase novelty reward."""
        weights = ScoringWeights.from_explore_weight(1.0)
        
        # Relaxed penalties
        assert weights.semantic_drift <= 0.30
        assert weights.domain_isolation <= 0.20
        
        # High novelty reward
        assert weights.novelty >= 0.20
    
    def test_weights_interpolate(self):
        """Weights should interpolate smoothly."""
        w0 = ScoringWeights.from_explore_weight(0.0)
        w05 = ScoringWeights.from_explore_weight(0.5)
        w1 = ScoringWeights.from_explore_weight(1.0)
        
        # Mid-point should be between extremes
        assert w0.semantic_drift > w05.semantic_drift > w1.semantic_drift
        assert w0.novelty < w05.novelty < w1.novelty


class TestDomainCrossingReward:
    """Test domain crossing rewards."""
    
    @pytest.fixture
    def scorer(self):
        context = TraversalContext(
            query_embedding=np.random.randn(768),
            embed_fn=lambda x: np.random.randn(768)
        )
        weights = ScoringWeights.from_explore_weight(0.5)
        return EdgeScorer(context, weights)
    
    def test_financial_to_narrative_reward(self, scorer):
        """Crossing financial → narrative should get full reward."""
        from unittest.mock import Mock
        
        source = Mock()
        source.type = "FINANCIAL_LINE"
        target = Mock()
        target.type = "TEXT_SECTION"
        
        reward = scorer._compute_domain_crossing_reward(source, target)
        assert reward == 1.0
    
    def test_same_domain_no_reward(self, scorer):
        """Staying in same domain should get no reward."""
        from unittest.mock import Mock
        
        source = Mock()
        source.type = "TEXT_SECTION"
        target = Mock()
        target.type = "TEXT_SECTION"
        
        reward = scorer._compute_domain_crossing_reward(source, target)
        assert reward == 0.0


class TestSemanticDriftPenalty:
    """Test semantic drift penalty."""
    
    def test_first_semantic_edge_low_penalty(self):
        """First SEMANTICALLY_SIMILAR edge should have low penalty."""
        context = TraversalContext(
            query_embedding=np.random.randn(768),
            embed_fn=lambda x: np.random.randn(768)
        )
        context.semantic_chain_length = 0
        
        weights = ScoringWeights.from_explore_weight(0.5)
        scorer = EdgeScorer(context, weights)
        
        penalty = scorer._compute_semantic_drift_penalty("SEMANTICALLY_SIMILAR")
        assert penalty <= 0.3
    
    def test_chain_semantic_edge_high_penalty(self):
        """Chain of SEMANTICALLY_SIMILAR edges should have high penalty."""
        context = TraversalContext(
            query_embedding=np.random.randn(768),
            embed_fn=lambda x: np.random.randn(768)
        )
        context.semantic_chain_length = 3  # Already in a chain
        
        weights = ScoringWeights.from_explore_weight(0.5)
        scorer = EdgeScorer(context, weights)
        
        penalty = scorer._compute_semantic_drift_penalty("SEMANTICALLY_SIMILAR")
        assert penalty >= 0.7
    
    def test_non_semantic_edge_no_penalty(self):
        """Non-semantic edges should have no drift penalty."""
        context = TraversalContext(
            query_embedding=np.random.randn(768),
            embed_fn=lambda x: np.random.randn(768)
        )
        context.semantic_chain_length = 5  # Even with high chain length
        
        weights = ScoringWeights.from_explore_weight(0.5)
        scorer = EdgeScorer(context, weights)
        
        penalty = scorer._compute_semantic_drift_penalty("EXPLAINS_LINE_ITEM")
        assert penalty == 0.0


class TestEndToEndScoring:
    """Integration tests for the full scoring system."""
    
    def test_bridge_edge_preferred_over_semantic(self):
        """Bridge edges should score higher than semantic edges."""
        context = TraversalContext(
            query_embedding=np.random.randn(768),
            embed_fn=lambda x: np.random.randn(768)
        )
        weights = ScoringWeights.from_explore_weight(0.3)
        scorer = EdgeScorer(context, weights)
        
        from unittest.mock import Mock
        
        source = Mock()
        source.id = "source_1"
        source.type = "TEXT_SECTION"
        source.text = "Some text"
        
        target_bridge = Mock()
        target_bridge.id = "target_bridge"
        target_bridge.type = "FINANCIAL_LINE"
        target_bridge.text = "Revenue data"
        
        target_semantic = Mock()
        target_semantic.id = "target_semantic"
        target_semantic.type = "TEXT_SECTION"
        target_semantic.text = "Similar text"
        
        # Score bridge edge (EXPLAINS_LINE_ITEM)
        score_bridge = scorer.score_edge(
            edge_type="EXPLAINS_LINE_ITEM",
            edge_confidence=0.8,
            source_node=source,
            target_node=target_bridge,
            path_confidence=0.9,
            source_fanout=5
        )
        
        # Score semantic edge
        score_semantic = scorer.score_edge(
            edge_type="SEMANTICALLY_SIMILAR",
            edge_confidence=0.8,
            source_node=source,
            target_node=target_semantic,
            path_confidence=0.9,
            source_fanout=50  # High fanout (typical for semantic)
        )
        
        # Bridge should score higher
        assert score_bridge.total_score > score_semantic.total_score
```

---

## Task 4: Run Diagnostics and Verify

After implementing, run this verification:

```python
# verify_scoring.py

from src.opmech.system import OpMechGraphRAG
from src.opmech.config import OpMechConfig
from src.opmech.diagnostics import ScoringDiagnostics

def verify_scoring_system():
    """Verify the scoring system fixes the issues."""
    
    config = OpMechConfig()
    system = OpMechGraphRAG(config)
    
    # Test query that was problematic
    query = "What was Apple's total revenue in FY2023?"
    
    print(f"\nTesting: {query}")
    print("=" * 60)
    
    result = system.query(query)
    
    # Check mode
    print(f"\nMode: {result.mode}")
    assert result.mode in ["EXPLOIT", "ADAPTIVE"], f"Expected EXPLOIT/ADAPTIVE, got {result.mode}"
    
    # Check divergence
    final_delta_E = result.trajectory[-1].delta_E
    print(f"Final Δ_E: {final_delta_E:.3f}")
    assert final_delta_E < 0.8, f"Δ_E too high: {final_delta_E}"
    
    # Check confidence
    print(f"Confidence: {result.confidence:.1%}")
    assert result.confidence > 0.6, f"Confidence too low: {result.confidence}"
    
    # Check traversal sizes
    print(f"\nOperator A: {result.diagnostics['operator_A_nodes']} nodes")
    print(f"Operator B: {result.diagnostics['operator_B_nodes']} nodes")
    
    ratio = result.diagnostics['operator_B_nodes'] / max(1, result.diagnostics['operator_A_nodes'])
    print(f"Ratio (B/A): {ratio:.1f}x")
    assert ratio < 10, f"Operator B still exploding: {ratio}x more nodes"
    
    # Analyze scoring
    if hasattr(result, 'edge_scores_A'):
        print("\n--- Operator A Scoring ---")
        diag_A = ScoringDiagnostics(result.edge_scores_A)
        diag_A.print_report()
    
    if hasattr(result, 'edge_scores_B'):
        print("\n--- Operator B Scoring ---")
        diag_B = ScoringDiagnostics(result.edge_scores_B)
        diag_B.print_report()
    
    # Check answer quality
    print(f"\nAnswer preview: {result.answer[:200]}...")
    
    # Should mention actual revenue
    assert "383" in result.answer or "billion" in result.answer.lower(), \
        "Answer doesn't contain expected revenue figure"
    
    print("\n✅ All checks passed!")
    system.close()


if __name__ == "__main__":
    verify_scoring_system()
```

---

## Summary: Reward/Penalty System

### Rewards (Encourage Good Exploration)

| Reward | Trigger | Value | Purpose |
|--------|---------|-------|---------|
| **Domain Crossing** | FINANCIAL → NARRATIVE or vice versa | +1.0 | Multi-perspective |
| **Query Relevance** | Target node similar to query | +0-1.0 | Stay on topic |
| **Novelty** | Target unlike visited nodes | +0-1.0 | New information |
| **Bridge Edge** | Using EXPLAINS/DISCUSSES | +1.0 | Connect domains |
| **Convergence** | Target in other operator's set | +1.0 | Operators agree |

### Penalties (Discourage Bad Exploration)

| Penalty | Trigger | Value | Purpose |
|---------|---------|-------|---------|
| **Semantic Drift** | Chain of SEMANTICALLY_SIMILAR | -0.2 to -1.0 | Stop echo chambers |
| **Domain Isolation** | 4+ nodes in same domain | -0.1 to -1.0 | Force crossing |
| **Low Confidence** | Edge confidence < 0.6 | -0 to -1.0 | Quality paths |
| **Redundancy** | Target similar to visited | -0.8 | No duplicates |
| **High Fanout** | Source has 20+ edges | -0 to -1.0 | Avoid hubs |

### Dynamic Weights

```
EXPLOIT (w=0): High penalties, moderate rewards
  → Strict quality control, convergence priority

EXPLORE (w=1): Relaxed penalties, high novelty reward  
  → Accept more edges, prioritize new information
```

---

## Expected Results After Implementation

For "What was Apple's total revenue in FY2023?":

```
BEFORE (broken):
  Mode: ADAPTIVE
  Δ_E: 1.000 (zero overlap)
  Op B: 1134 nodes (explosion)
  Answer: Wrong

AFTER (fixed):
  Mode: EXPLOIT
  Δ_E: ~0.35 (good overlap)
  Op B: ~80 nodes (controlled)
  Answer: $383.3 billion ✓

Scoring diagnostics:
  Domain crossing reward: 0.45 (operators crossing domains!)
  Semantic drift penalty: 0.08 (chains broken!)
  Convergence reward: 0.25 (operators finding shared evidence!)
```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/opmech/edge_scoring.py` | **CREATE** | Reward/penalty system |
| `src/opmech/graph_interface.py` | MODIFY | Integrate scoring into traversal |
| `src/opmech/operators.py` | MODIFY | Use scoring, dynamic edges |
| `src/opmech/system.py` | MODIFY | Two-phase execution, share evidence |
| `src/opmech/diagnostics.py` | **CREATE** | Scoring analysis tools |
| `tests/test_scoring_system.py` | **CREATE** | Unit tests for scoring |
| `verify_scoring.py` | **CREATE** | Integration verification |

Good luck! The reward/penalty system is the key architectural change that preserves explore/exploit while fixing the traversal quality issues.
