# OpMech-GraphRAG Diagnosis and Fix Prompt

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

## Critical Issues Identified

### Issue 1: Δ_E = 1.000 (ZERO Evidence Overlap)

The two operators found **completely different evidence nodes**. For a simple factual query, they should converge on the same FINANCIAL_LINE nodes containing revenue data.

### Issue 2: Operator B Traversal Explosion

Operator B traversed **1134 nodes and 5101 edges** while Operator A only traversed **31 nodes and 129 edges**. This 36x difference suggests:
- SEMANTICALLY_SIMILAR edges are too dense
- No cap on maximum traversal
- min_edge_confidence threshold too permissive

### Issue 3: Wrong Answer Despite Correct Graph

The graph contains the correct revenue data (we built it with MoE experts), but the operators aren't surfacing it to the LLM.

### Issue 4: Mode Mismatch

Simple factual queries should result in EXPLOIT mode (low divergence), not ADAPTIVE mode (medium-high divergence).

---

## Your Tasks

### Task 1: Diagnostic Analysis

First, diagnose the root causes by examining the actual data flow:

```bash
# 1. Check what nodes Operator A is finding as seeds
# Query Neo4j to see FINANCIAL_LINE nodes with revenue-related XBRL tags

# 2. Check what nodes Operator B is finding as seeds  
# What TEXT_SECTION nodes are most similar to "What was Apple's total revenue in FY2023?"

# 3. Trace the traversal paths
# For each operator, what edges are being followed and why?

# 4. Examine the final evidence sets
# What nodes end up in evidence_A vs evidence_B?
# Why is there zero overlap?

# 5. Check if the correct revenue node exists in the graph
# Find nodes with XBRL tags containing "Revenue" and period FY2023
```

Create a diagnostic script `src/opmech/diagnostics.py`:

```python
"""
Diagnostic script to understand why operators are diverging on simple queries.
"""

from loguru import logger
import numpy as np
from neo4j import GraphDatabase
from typing import List, Dict, Set
import json

class OpMechDiagnostics:
    """Diagnose issues with operator divergence."""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    def diagnose_query(self, query: str, evidence_A: List[str], evidence_B: List[str]):
        """
        Full diagnostic for a query that showed high divergence.
        """
        print("=" * 80)
        print(f"DIAGNOSTIC REPORT: {query}")
        print("=" * 80)
        
        # 1. Check evidence overlap
        self._analyze_evidence_overlap(evidence_A, evidence_B)
        
        # 2. Find what revenue nodes exist
        self._find_revenue_nodes()
        
        # 3. Check if revenue nodes are in either evidence set
        self._check_revenue_in_evidence(evidence_A, evidence_B)
        
        # 4. Analyze why operators diverged
        self._analyze_divergence_causes(evidence_A, evidence_B)
        
        # 5. Check edge density for different edge types
        self._analyze_edge_density()
    
    def _analyze_evidence_overlap(self, evidence_A: List[str], evidence_B: List[str]):
        """Compute and explain evidence overlap."""
        set_A = set(evidence_A)
        set_B = set(evidence_B)
        
        intersection = set_A & set_B
        union = set_A | set_B
        only_A = set_A - set_B
        only_B = set_B - set_A
        
        print("\n--- EVIDENCE OVERLAP ANALYSIS ---")
        print(f"Operator A evidence: {len(set_A)} nodes")
        print(f"Operator B evidence: {len(set_B)} nodes")
        print(f"Intersection: {len(intersection)} nodes")
        print(f"Union: {len(union)} nodes")
        print(f"Jaccard similarity: {len(intersection) / len(union) if union else 0:.3f}")
        print(f"Δ_E (Jaccard distance): {1 - len(intersection) / len(union) if union else 1:.3f}")
        
        if intersection:
            print(f"\nShared nodes: {list(intersection)[:10]}")
        else:
            print("\n⚠️  NO OVERLAP - Operators found completely different evidence!")
        
        print(f"\nOnly in Operator A: {list(only_A)[:5]}")
        print(f"Only in Operator B: {list(only_B)[:5]}")
    
    def _find_revenue_nodes(self):
        """Find all nodes that should contain revenue information."""
        print("\n--- REVENUE NODES IN GRAPH ---")
        
        with self.driver.session() as session:
            # Find FINANCIAL_LINE nodes with revenue XBRL tags
            result = session.run("""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND (
                    toLower(n.xbrl_tag) CONTAINS 'revenue'
                    OR toLower(n.xbrl_tag) CONTAINS 'sales'
                    OR toLower(n.text) CONTAINS 'total net sales'
                )
                RETURN n.id AS id, n.xbrl_tag AS xbrl_tag, n.value AS value, 
                       n.period AS period, n.text AS text
                ORDER BY n.period DESC
                LIMIT 20
            """)
            
            revenue_nodes = list(result)
            print(f"Found {len(revenue_nodes)} revenue-related FINANCIAL_LINE nodes:")
            for node in revenue_nodes:
                print(f"  - {node['id']}: {node['xbrl_tag']} = {node['value']} ({node['period']})")
            
            # Find TEXT_SECTION nodes mentioning revenue
            result2 = session.run("""
                MATCH (n:Node)
                WHERE n.type = 'TEXT_SECTION'
                AND toLower(n.text) CONTAINS 'total net sales'
                RETURN n.id AS id, n.section AS section, 
                       substring(n.text, 0, 200) AS text_preview
                LIMIT 10
            """)
            
            text_nodes = list(result2)
            print(f"\nFound {len(text_nodes)} TEXT_SECTION nodes mentioning revenue:")
            for node in text_nodes:
                print(f"  - {node['id']} ({node['section']}): {node['text_preview'][:100]}...")
    
    def _check_revenue_in_evidence(self, evidence_A: List[str], evidence_B: List[str]):
        """Check if the correct revenue nodes are in the evidence sets."""
        print("\n--- REVENUE NODES IN EVIDENCE ---")
        
        with self.driver.session() as session:
            # Get IDs of revenue nodes
            result = session.run("""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND (
                    toLower(n.xbrl_tag) CONTAINS 'revenue'
                    OR toLower(n.xbrl_tag) CONTAINS 'sales'
                )
                RETURN n.id AS id
            """)
            revenue_ids = {r['id'] for r in result}
        
        revenue_in_A = set(evidence_A) & revenue_ids
        revenue_in_B = set(evidence_B) & revenue_ids
        
        print(f"Revenue nodes in Operator A evidence: {len(revenue_in_A)}")
        if revenue_in_A:
            print(f"  IDs: {list(revenue_in_A)[:5]}")
        else:
            print("  ⚠️  NO REVENUE NODES IN OPERATOR A EVIDENCE!")
        
        print(f"Revenue nodes in Operator B evidence: {len(revenue_in_B)}")
        if revenue_in_B:
            print(f"  IDs: {list(revenue_in_B)[:5]}")
        else:
            print("  ⚠️  NO REVENUE NODES IN OPERATOR B EVIDENCE!")
    
    def _analyze_divergence_causes(self, evidence_A: List[str], evidence_B: List[str]):
        """Analyze why the operators diverged."""
        print("\n--- DIVERGENCE CAUSE ANALYSIS ---")
        
        with self.driver.session() as session:
            # Get node types in each evidence set
            for name, evidence in [("A", evidence_A), ("B", evidence_B)]:
                if not evidence:
                    continue
                    
                result = session.run("""
                    MATCH (n:Node)
                    WHERE n.id IN $ids
                    RETURN n.type AS type, count(*) AS count
                    ORDER BY count DESC
                """, ids=evidence)
                
                print(f"\nOperator {name} evidence composition:")
                for row in result:
                    print(f"  {row['type']}: {row['count']} nodes")
            
            # Get sections represented in each evidence set
            for name, evidence in [("A", evidence_A), ("B", evidence_B)]:
                if not evidence:
                    continue
                    
                result = session.run("""
                    MATCH (n:Node)
                    WHERE n.id IN $ids
                    RETURN DISTINCT n.section AS section
                """, ids=evidence)
                
                sections = [r['section'] for r in result if r['section']]
                print(f"\nOperator {name} sections: {sections[:10]}")
    
    def _analyze_edge_density(self):
        """Analyze edge density to understand traversal explosion."""
        print("\n--- EDGE DENSITY ANALYSIS ---")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS edge_type, 
                       count(*) AS count,
                       avg(r.confidence) AS avg_confidence,
                       min(r.confidence) AS min_confidence,
                       max(r.confidence) AS max_confidence
                ORDER BY count DESC
            """)
            
            print("\nEdge type statistics:")
            print(f"{'Edge Type':<30} {'Count':>8} {'Avg Conf':>10} {'Min':>8} {'Max':>8}")
            print("-" * 70)
            for row in result:
                print(f"{row['edge_type']:<30} {row['count']:>8} {row['avg_confidence']:>10.3f} {row['min_confidence']:>8.3f} {row['max_confidence']:>8.3f}")
            
            # Check average out-degree per edge type
            result2 = session.run("""
                MATCH (n:Node)-[r]->()
                WITH n, type(r) AS edge_type, count(*) AS out_degree
                RETURN edge_type, avg(out_degree) AS avg_out_degree, max(out_degree) AS max_out_degree
                ORDER BY avg_out_degree DESC
            """)
            
            print("\nAverage out-degree per edge type:")
            for row in result2:
                print(f"  {row['edge_type']}: avg={row['avg_out_degree']:.1f}, max={row['max_out_degree']}")
    
    def trace_operator_path(self, operator_name: str, seed_ids: List[str], 
                           edge_types: List[str], max_hops: int = 2):
        """Trace exactly what path an operator takes."""
        print(f"\n--- TRACING {operator_name} PATH ---")
        print(f"Seeds: {seed_ids[:5]}...")
        print(f"Edge types: {edge_types}")
        print(f"Max hops: {max_hops}")
        
        with self.driver.session() as session:
            current_frontier = set(seed_ids)
            visited = set(seed_ids)
            
            for hop in range(1, max_hops + 1):
                # Find neighbors
                edge_pattern = "|".join(edge_types)
                result = session.run(f"""
                    MATCH (source:Node)-[r:{edge_pattern}]->(target:Node)
                    WHERE source.id IN $frontier
                    RETURN source.id AS source, target.id AS target, 
                           type(r) AS edge_type, r.confidence AS confidence
                    ORDER BY r.confidence DESC
                    LIMIT 1000
                """, frontier=list(current_frontier))
                
                edges = list(result)
                new_nodes = {e['target'] for e in edges if e['target'] not in visited}
                
                print(f"\nHop {hop}:")
                print(f"  Frontier size: {len(current_frontier)}")
                print(f"  Edges found: {len(edges)}")
                print(f"  New nodes: {len(new_nodes)}")
                
                # Edge type breakdown
                edge_counts = {}
                for e in edges:
                    edge_counts[e['edge_type']] = edge_counts.get(e['edge_type'], 0) + 1
                print(f"  Edge breakdown: {edge_counts}")
                
                visited.update(new_nodes)
                current_frontier = new_nodes
                
                if not new_nodes:
                    print("  No new nodes - stopping")
                    break
            
            print(f"\nTotal visited: {len(visited)} nodes")
    
    def close(self):
        self.driver.close()


def run_diagnostics():
    """Run full diagnostics on the problematic query."""
    diag = OpMechDiagnostics(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j", 
        neo4j_password="password123"
    )
    
    # The query that failed
    query = "What was Apple's total revenue in FY2023?"
    
    # TODO: Get actual evidence IDs from your last run
    # For now, we'll just run the graph analysis
    evidence_A = []  # Fill from logs
    evidence_B = []  # Fill from logs
    
    diag.diagnose_query(query, evidence_A, evidence_B)
    
    # Trace what Operator A would do
    diag.trace_operator_path(
        "OperatorA",
        seed_ids=["financial_line_revenue_2023"],  # Replace with actual seeds
        edge_types=["TEMPORAL_NEXT", "EXPLAINS_LINE_ITEM", "REFERS_TO"],
        max_hops=2
    )
    
    # Trace what Operator B would do
    diag.trace_operator_path(
        "OperatorB", 
        seed_ids=["text_section_mda_2023"],  # Replace with actual seeds
        edge_types=["CAUSED_BY", "DISCUSSES", "MENTIONS_ENTITY", "SEMANTICALLY_SIMILAR"],
        max_hops=2
    )
    
    diag.close()


if __name__ == "__main__":
    run_diagnostics()
```

---

### Task 2: Implement Fixes

Based on the diagnosis, implement the following fixes:

#### Fix 2.1: Add Traversal Caps

In `src/opmech/graph_interface.py`, add hard caps to prevent explosion:

```python
def traverse_with_confidence(
    self,
    seed_ids: List[str],
    edge_types: List[str],
    hops: int,
    max_per_hop: int,
    min_confidence: float,
    confidence_decay: float = 0.9,
    max_nodes_total: int = 200,      # NEW: Hard cap on total nodes
    max_edges_total: int = 500,       # NEW: Hard cap on total edges
) -> tuple[List[TraversedNode], List[Edge]]:
    """
    CONFIDENCE-WEIGHTED multi-hop graph traversal with CAPS.
    """
    import heapq
    
    frontier = []
    for seed_id in seed_ids:
        heapq.heappush(frontier, (-1.0, seed_id, 0, None))
    
    visited = {}
    all_edges = []
    
    with self.driver.session() as session:
        while frontier:
            # CHECK CAPS
            if len(visited) >= max_nodes_total:
                logger.warning(f"Hit max_nodes_total cap ({max_nodes_total})")
                break
            if len(all_edges) >= max_edges_total:
                logger.warning(f"Hit max_edges_total cap ({max_edges_total})")
                break
            
            neg_conf, node_id, hop_dist, incoming_edge = heapq.heappop(frontier)
            path_conf = -neg_conf
            
            # ... rest of traversal logic
```

#### Fix 2.2: Edge-Type Specific Confidence Thresholds

SEMANTICALLY_SIMILAR edges are too dense. Add edge-type-specific thresholds:

```python
# In config.py or as class attribute
EDGE_CONFIDENCE_OVERRIDES = {
    "SEMANTICALLY_SIMILAR": 0.85,    # Require high confidence
    "ENTITY_RELATED_TO": 0.80,       # Require high confidence  
    "TEMPORAL_NEXT": 0.60,           # Can be lower (XBRL-derived)
    "EXPLAINS_LINE_ITEM": 0.65,
    "CAUSED_BY": 0.70,
    "DISCUSSES": 0.70,
    "REFERS_TO": 0.65,
}

def get_effective_min_confidence(self, edge_type: str, base_min_confidence: float) -> float:
    """Get effective confidence threshold for an edge type."""
    override = self.EDGE_CONFIDENCE_OVERRIDES.get(edge_type)
    if override:
        return max(base_min_confidence, override)
    return base_min_confidence
```

Then in the Cypher query:

```python
# Instead of single min_confidence, use per-type thresholds
edge_result = session.run("""
    MATCH (source:Node {id: $node_id})-[r]->(target:Node)
    WHERE type(r) IN $edge_types
    AND (
        (type(r) = 'SEMANTICALLY_SIMILAR' AND r.confidence >= 0.85)
        OR (type(r) = 'ENTITY_RELATED_TO' AND r.confidence >= 0.80)
        OR (type(r) NOT IN ['SEMANTICALLY_SIMILAR', 'ENTITY_RELATED_TO'] AND r.confidence >= $min_conf)
    )
    RETURN ...
    ORDER BY r.confidence DESC
    LIMIT $limit
""", ...)
```

#### Fix 2.3: Add Convergence Pressure (Bridge Detection)

If operators are diverging (Δ_E > 0.8), force them to share information:

```python
# In src/opmech/system.py, in the query loop

def _apply_convergence_pressure(
    self,
    belief_A: BeliefState,
    belief_B: BeliefState,
    delta_E: float,
    hop: int
) -> tuple[List[str], List[str]]:
    """
    When operators diverge too much, share top nodes between them.
    This creates "bridge" nodes that both operators will explore.
    
    Returns additional seed IDs for each operator.
    """
    if hop == 1:
        # Don't apply on first hop - let them explore naturally
        return [], []
    
    if delta_E < 0.8:
        # Operators are converging - no pressure needed
        return [], []
    
    logger.info(f"Applying convergence pressure (Δ_E={delta_E:.3f})")
    
    # Get top nodes from each operator by combined score
    top_A = sorted(
        belief_A.evidence,
        key=lambda n: self._get_node_score(n),
        reverse=True
    )[:3]
    
    top_B = sorted(
        belief_B.evidence,
        key=lambda n: self._get_node_score(n),
        reverse=True
    )[:3]
    
    # Give Operator A some of B's top nodes, and vice versa
    additional_seeds_A = [n.id for n in top_B]
    additional_seeds_B = [n.id for n in top_A]
    
    return additional_seeds_A, additional_seeds_B
```

Then in the main loop:

```python
# After computing commutator
if hop > 1 and commutator.delta_E > 0.8:
    additional_A, additional_B = self._apply_convergence_pressure(
        belief_A, belief_B, commutator.delta_E, hop
    )
    # Add to next iteration's seeds
    self.operator_A.add_bridge_seeds(additional_A)
    self.operator_B.add_bridge_seeds(additional_B)
```

#### Fix 2.4: Improve Seed Selection for Operator A

Operator A should prioritize FINANCIAL_LINE nodes that **actually contain revenue values**:

```python
# In src/opmech/operators.py, OperatorA.execute()

def _find_revenue_seeds(self, query: str) -> List[Node]:
    """
    For revenue queries, directly find FINANCIAL_LINE nodes with revenue data.
    """
    # Detect if this is a revenue query
    revenue_keywords = ["revenue", "sales", "net sales", "total revenue"]
    is_revenue_query = any(kw in query.lower() for kw in revenue_keywords)
    
    if not is_revenue_query:
        return []
    
    # Extract fiscal year if mentioned
    import re
    fy_match = re.search(r'FY\s*(\d{4})|fiscal\s*(?:year\s*)?(\d{4})', query, re.IGNORECASE)
    year_filter = ""
    if fy_match:
        year = fy_match.group(1) or fy_match.group(2)
        year_filter = f"AND n.period CONTAINS '{year}'"
    
    with self.graph.driver.session() as session:
        result = session.run(f"""
            MATCH (n:Node)
            WHERE n.type = 'FINANCIAL_LINE'
            AND (
                toLower(n.xbrl_tag) CONTAINS 'revenue'
                OR toLower(n.xbrl_tag) CONTAINS 'sales'
            )
            {year_filter}
            AND n.value IS NOT NULL
            RETURN n.id AS id, n.type AS type, n.text AS text,
                   n.xbrl_tag AS xbrl_tag, n.value AS value, n.period AS period
            ORDER BY n.value DESC
            LIMIT 5
        """)
        
        nodes = []
        for r in result:
            nodes.append(Node(
                id=r['id'],
                type=r['type'],
                text=r['text'],
                metadata={
                    'xbrl_tag': r['xbrl_tag'],
                    'value': r['value'],
                    'period': r['period']
                }
            ))
        
        if nodes:
            logger.info(f"Found {len(nodes)} direct revenue seeds")
        
        return nodes
```

Then modify the execute method:

```python
def execute(self, query: str, strategy: TraversalStrategy) -> BeliefState:
    # Try direct revenue seed first
    direct_seeds = self._find_revenue_seeds(query)
    
    if direct_seeds:
        # Use direct seeds as primary
        seeds = direct_seeds
    else:
        # Fall back to embedding-based search
        query_embedding = self.embed_fn(query)
        seeds = self.graph.search_by_type(...)
    
    # ... rest of execute
```

#### Fix 2.5: Balance Evidence Selection

After traversal, ensure both operators include some FINANCIAL_LINE nodes:

```python
def _balance_evidence(
    self,
    evidence: List[Node],
    top_k: int,
    min_financial_nodes: int = 3
) -> List[Node]:
    """
    Ensure evidence includes both narrative and financial nodes.
    """
    financial_nodes = [n for n in evidence if n.type == "FINANCIAL_LINE"]
    other_nodes = [n for n in evidence if n.type != "FINANCIAL_LINE"]
    
    # Ensure minimum financial nodes
    n_financial = min(len(financial_nodes), max(min_financial_nodes, top_k // 4))
    n_other = top_k - n_financial
    
    balanced = financial_nodes[:n_financial] + other_nodes[:n_other]
    
    # Re-sort by score
    balanced.sort(key=lambda n: self._get_node_score(n), reverse=True)
    
    return balanced[:top_k]
```

---

### Task 3: Add Logging and Observability

Add detailed logging to understand what's happening:

```python
# In src/opmech/operators.py

def execute(self, query: str, strategy: TraversalStrategy) -> BeliefState:
    logger.info(f"{self.name}: Starting execution")
    logger.debug(f"{self.name}: Strategy = {strategy}")
    
    # Seed selection
    seeds = self._get_seeds(query, strategy)
    logger.info(f"{self.name}: Found {len(seeds)} seed nodes")
    logger.debug(f"{self.name}: Seed types = {[s.type for s in seeds]}")
    logger.debug(f"{self.name}: Seed IDs = {[s.id for s in seeds[:5]]}")
    
    # Traversal
    traversed, edges = self.graph.traverse_with_confidence(...)
    logger.info(f"{self.name}: Traversed {len(traversed)} nodes, {len(edges)} edges")
    
    # Log node type distribution
    type_counts = {}
    for tn in traversed:
        t = tn.node.type
        type_counts[t] = type_counts.get(t, 0) + 1
    logger.debug(f"{self.name}: Node types = {type_counts}")
    
    # Log edge type distribution
    edge_counts = {}
    for e in edges:
        edge_counts[e.type] = edge_counts.get(e.type, 0) + 1
    logger.debug(f"{self.name}: Edge types = {edge_counts}")
    
    # Evidence selection
    evidence, confidences = self._rank_evidence_with_confidence(...)
    logger.info(f"{self.name}: Selected {len(evidence)} evidence nodes")
    
    # Log evidence composition
    ev_types = {}
    for n in evidence:
        ev_types[n.type] = ev_types.get(n.type, 0) + 1
    logger.debug(f"{self.name}: Evidence types = {ev_types}")
    
    # Log top evidence
    for i, n in enumerate(evidence[:3]):
        logger.debug(f"{self.name}: Evidence {i+1}: {n.id} ({n.type}) - {n.text[:100]}")
    
    return BeliefState(...)
```

---

### Task 4: Unit Tests for Fixes

Create tests to verify the fixes work:

```python
# tests/test_fixes.py

import pytest
from src.opmech.system import OpMechGraphRAG
from src.opmech.config import OpMechConfig

@pytest.fixture
def system():
    config = OpMechConfig()
    return OpMechGraphRAG(config)

class TestTraversalCaps:
    """Test that traversal caps prevent explosion."""
    
    def test_max_nodes_cap(self, system):
        """Operator B should not exceed max_nodes_total."""
        result = system.query("What was Apple's total revenue in FY2023?")
        
        # Check that Operator B didn't explode
        # (We'd need to expose this metric)
        assert result.diagnostics['operator_B_nodes'] <= 200
    
    def test_max_edges_cap(self, system):
        """Should not traverse more than max_edges_total."""
        result = system.query("What was Apple's total revenue in FY2023?")
        assert result.diagnostics['operator_B_edges'] <= 500

class TestEvidenceOverlap:
    """Test that operators converge on simple queries."""
    
    def test_simple_factual_query_convergence(self, system):
        """Simple factual queries should have evidence overlap."""
        result = system.query("What was Apple's total revenue in FY2023?")
        
        # Δ_E should be < 0.8 for simple queries
        assert result.trajectory[-1].delta_E < 0.8, \
            f"Evidence divergence too high: {result.trajectory[-1].delta_E}"
    
    def test_revenue_nodes_in_evidence(self, system):
        """Revenue query should include revenue nodes in evidence."""
        result = system.query("What was Apple's total revenue in FY2023?")
        
        # Check that at least one evidence node has revenue XBRL tag
        evidence_xbrl_tags = [
            n.metadata.get('xbrl_tag', '') 
            for n in result.evidence_A + result.evidence_B
        ]
        has_revenue = any('revenue' in tag.lower() or 'sales' in tag.lower() 
                         for tag in evidence_xbrl_tags)
        
        assert has_revenue, "No revenue nodes in evidence!"

class TestModeSelection:
    """Test that query complexity maps to correct mode."""
    
    def test_simple_query_exploit_mode(self, system):
        """Simple factual query should result in EXPLOIT mode."""
        result = system.query("What was Apple's total revenue in FY2023?")
        
        # Should be EXPLOIT or at least high confidence ADAPTIVE
        assert result.mode in ["EXPLOIT", "ADAPTIVE"]
        if result.mode == "ADAPTIVE":
            assert result.confidence > 0.6, \
                f"ADAPTIVE mode but low confidence: {result.confidence}"
    
    def test_complex_query_explore_mode(self, system):
        """Complex analytical query should result in EXPLORE mode."""
        result = system.query("Is Apple's margin pressure cyclical or structural?")
        
        # Should be EXPLORE or ADAPTIVE
        assert result.mode in ["EXPLORE", "ADAPTIVE"]

class TestConvergencePressure:
    """Test that convergence pressure reduces divergence."""
    
    def test_convergence_pressure_reduces_delta_E(self, system):
        """When applied, convergence pressure should reduce Δ_E."""
        # Run with convergence pressure disabled
        system.config.enable_convergence_pressure = False
        result_without = system.query("What are Apple's main risk factors?")
        
        # Run with convergence pressure enabled
        system.config.enable_convergence_pressure = True
        result_with = system.query("What are Apple's main risk factors?")
        
        # Δ_E should be lower with convergence pressure
        assert result_with.trajectory[-1].delta_E <= result_without.trajectory[-1].delta_E
```

---

### Task 5: Verify Fixes with Test Queries

After implementing fixes, run these test queries and verify expected behavior:

```python
# tests/test_query_suite.py

TEST_QUERIES = [
    {
        "query": "What was Apple's total revenue in FY2023?",
        "expected_mode": "EXPLOIT",
        "expected_confidence_min": 0.70,
        "expected_delta_E_max": 0.5,
        "expected_answer_contains": ["383", "billion"],
    },
    {
        "query": "How did R&D expenses change from FY2022 to FY2023?",
        "expected_mode": "EXPLOIT",
        "expected_confidence_min": 0.65,
        "expected_delta_E_max": 0.6,
    },
    {
        "query": "Is Apple's margin pressure cyclical or structural?",
        "expected_mode": "EXPLORE",
        "expected_confidence_max": 0.5,
        "expected_delta_E_min": 0.5,
    },
    {
        "query": "What is Apple's revenue recognition policy?",
        "expected_mode": "EXPLOIT",
        "expected_confidence_min": 0.60,
    },
    {
        "query": "What factors contributed to Services revenue growth?",
        "expected_mode": "ADAPTIVE",
        "expected_confidence_min": 0.50,
    },
]

def test_all_queries(system):
    for tc in TEST_QUERIES:
        result = system.query(tc["query"])
        
        print(f"\nQuery: {tc['query']}")
        print(f"  Mode: {result.mode} (expected: {tc['expected_mode']})")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Δ_E: {result.trajectory[-1].delta_E:.3f}")
        
        # Verify expectations
        if "expected_mode" in tc:
            assert result.mode == tc["expected_mode"], \
                f"Mode mismatch: {result.mode} != {tc['expected_mode']}"
        
        if "expected_confidence_min" in tc:
            assert result.confidence >= tc["expected_confidence_min"], \
                f"Confidence too low: {result.confidence} < {tc['expected_confidence_min']}"
        
        if "expected_delta_E_max" in tc:
            assert result.trajectory[-1].delta_E <= tc["expected_delta_E_max"], \
                f"Δ_E too high: {result.trajectory[-1].delta_E} > {tc['expected_delta_E_max']}"
```

---

## Summary of Changes Needed

### Files to Modify:

1. **`src/opmech/graph_interface.py`**
   - Add `max_nodes_total` and `max_edges_total` caps
   - Add edge-type-specific confidence thresholds
   - Add logging for traversal statistics

2. **`src/opmech/operators.py`**
   - Add `_find_revenue_seeds()` for direct XBRL matching
   - Add `_balance_evidence()` to ensure mixed evidence types
   - Add `add_bridge_seeds()` method for convergence pressure
   - Add detailed logging

3. **`src/opmech/system.py`**
   - Add `_apply_convergence_pressure()` method
   - Call convergence pressure in main loop when Δ_E > 0.8
   - Add diagnostics to QueryResult

4. **`src/opmech/config.py`**
   - Add `max_nodes_total: int = 200`
   - Add `max_edges_total: int = 500`
   - Add `EDGE_CONFIDENCE_OVERRIDES` dict
   - Add `enable_convergence_pressure: bool = True`

### New Files to Create:

1. **`src/opmech/diagnostics.py`** - Diagnostic tooling
2. **`tests/test_fixes.py`** - Tests for the fixes
3. **`tests/test_query_suite.py`** - End-to-end query tests

---

## Expected Results After Fixes

For "What was Apple's total revenue in FY2023?":

```
Mode: EXPLOIT (was ADAPTIVE)
Confidence: 78% (was 52%)

Divergence at hop 1: Δ=0.35 (was 0.596)
  Δ_E=0.40 (was 1.000)  ← Evidence overlap!
  Δ_V=0.30 (was 1.000)  ← Structural overlap!
  Δ_A=0.04 (was 0.038)  ← Similar answers
  Δ_C=0.35 (was 0.424)  ← Similar confidence

OperatorA: Traversed 45 nodes, 180 edges (was 31/129)
OperatorB: Traversed 120 nodes, 350 edges (was 1134/5101) ← CAPPED!

Answer: Apple's total net sales for FY2023 were $383.3 billion...
```

---

## Execution Order

1. Run diagnostics first to understand current state
2. Implement traversal caps (quickest fix)
3. Implement edge-type thresholds
4. Implement direct revenue seed finding
5. Implement convergence pressure
6. Add tests and verify
7. Re-run test queries and compare

Good luck! Report back with diagnostic results before implementing fixes.
