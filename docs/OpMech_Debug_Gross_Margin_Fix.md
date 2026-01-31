# OpMech-GraphRAG Debug & Fix Prompt: Gross Margin Evidence Retrieval

## Problem Summary

The system correctly selected EXPLORE mode and MERGE_EQUAL trust for an opinion query about gross margin pressure, BUT the answers from both operators **missed the actual gross margin data**:

**Query:** "Is Apple's gross margin pressure cyclical or structural?"

**What went wrong:**
- Operator A said: "without direct information on gross margins" ❌
- Operator B discussed: risk factors and supply chain ⚠️
- Neither mentioned: Actual margin percentages (36.3% products, 74% services, 46.2% total)

**Evidence retrieved:**
- 16 nodes (Operator A) + 13 nodes (Operator B)
- High Δ_E = 0.682 (found different nodes)
- But Δ_A = 0.049 (similar vague conclusions)

---

## Debug Task 1: Check Graph Content

First, verify if gross margin data exists in the knowledge graph.

```bash
# Navigate to project directory
cd /path/to/opmech-graphrag

# Check Neo4j for gross margin related nodes
```

```python
# Run this diagnostic script
from neo4j import GraphDatabase
import os

# Connect to Neo4j
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(uri, auth=(user, password))

def check_gross_margin_nodes():
    """Check if graph contains gross margin data."""
    
    queries = [
        # Check for gross margin in content
        """
        MATCH (n) 
        WHERE toLower(n.content) CONTAINS 'gross margin' 
           OR toLower(n.content) CONTAINS 'gross profit'
           OR toLower(n.content) CONTAINS 'cost of sales'
        RETURN labels(n)[0] as type, n.id as id, 
               substring(n.content, 0, 200) as content_preview
        LIMIT 20
        """,
        
        # Check for XBRL tags related to margins
        """
        MATCH (n:FINANCIAL_LINE)
        WHERE n.xbrl_tag CONTAINS 'Gross' 
           OR n.xbrl_tag CONTAINS 'CostOf'
           OR n.xbrl_tag CONTAINS 'Margin'
        RETURN n.xbrl_tag, n.value, n.period, 
               substring(n.content, 0, 150) as content
        LIMIT 20
        """,
        
        # Check what FINANCIAL_LINE nodes we have
        """
        MATCH (n:FINANCIAL_LINE)
        RETURN DISTINCT n.xbrl_tag as tag, count(*) as count
        ORDER BY count DESC
        LIMIT 30
        """,
        
        # Check for percentage values (margins are usually %)
        """
        MATCH (n)
        WHERE n.content CONTAINS '%' 
          AND (toLower(n.content) CONTAINS 'margin' 
               OR toLower(n.content) CONTAINS 'gross')
        RETURN labels(n)[0] as type, substring(n.content, 0, 200) as content
        LIMIT 20
        """
    ]
    
    with driver.session() as session:
        for i, query in enumerate(queries):
            print(f"\n{'='*60}")
            print(f"Query {i+1}:")
            print(f"{'='*60}")
            result = session.run(query)
            records = list(result)
            if records:
                for r in records:
                    print(dict(r))
            else:
                print("NO RESULTS FOUND")
    
    driver.close()

if __name__ == "__main__":
    check_gross_margin_nodes()
```

**Expected findings:**
- If NO gross margin nodes → Problem is in MoE Graph Builder
- If gross margin nodes EXIST but weren't retrieved → Problem is in Operator traversal

---

## Debug Task 2: Check Operator Seed Selection

Trace what seeds each operator selected for this query.

```python
# Add to src/opmech/operators.py or create debug script

def debug_seed_selection(query: str, query_class):
    """Debug what seeds operators select for a query."""
    
    print(f"\n{'='*60}")
    print(f"DEBUGGING SEED SELECTION")
    print(f"Query: {query}")
    print(f"Query Type: {query_class.query_type}")
    print(f"Expects Number: {query_class.expects_number}")
    print(f"Entities: {query_class.entities_mentioned}")
    print(f"{'='*60}")
    
    # Initialize operators
    operator_A = OperatorA(graph, llm)
    operator_B = OperatorB(graph, llm)
    
    # Get seeds for Operator A
    seeds_A = operator_A._get_initial_seeds(query, query_class)
    print(f"\nOPERATOR A SEEDS ({len(seeds_A)} nodes):")
    for i, seed in enumerate(seeds_A):
        print(f"  {i+1}. [{seed.node_type.value}] {seed.content[:100]}...")
        if hasattr(seed, 'metadata'):
            print(f"      Metadata: {seed.metadata}")
    
    # Get seeds for Operator B
    seeds_B = operator_B._get_initial_seeds(query, query_class)
    print(f"\nOPERATOR B SEEDS ({len(seeds_B)} nodes):")
    for i, seed in enumerate(seeds_B):
        print(f"  {i+1}. [{seed.node_type.value}] {seed.content[:100]}...")
    
    # Check if any seeds are FINANCIAL_LINE with margin data
    margin_seeds_A = [s for s in seeds_A if 'margin' in s.content.lower() or 'gross' in s.content.lower()]
    margin_seeds_B = [s for s in seeds_B if 'margin' in s.content.lower() or 'gross' in s.content.lower()]
    
    print(f"\n{'='*60}")
    print(f"MARGIN-RELATED SEEDS:")
    print(f"  Operator A: {len(margin_seeds_A)} nodes")
    print(f"  Operator B: {len(margin_seeds_B)} nodes")
    print(f"{'='*60}")
    
    if len(margin_seeds_A) == 0 and len(margin_seeds_B) == 0:
        print("\n⚠️  WARNING: No margin-related seeds found!")
        print("    This explains why the answers lack margin data.")
    
    return seeds_A, seeds_B

# Run debug
from src.opmech.query_classifier import QueryClassifier
classifier = QueryClassifier()
query = "Is Apple's gross margin pressure cyclical or structural?"
query_class = classifier.classify(query)
debug_seed_selection(query, query_class)
```

---

## Debug Task 3: Check Query Classification

The query has BOTH opinion AND numerical aspects. Check how it's classified:

```python
# Debug query classification
from src.opmech.query_classifier import QueryClassifier

def debug_classification(query: str):
    classifier = QueryClassifier()
    result = classifier.classify(query)
    
    print(f"\n{'='*60}")
    print(f"QUERY CLASSIFICATION DEBUG")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"")
    print(f"Classification:")
    print(f"  Type: {result.query_type.value}")
    print(f"  Complexity: {result.complexity}")
    print(f"  Expects Number: {result.expects_number}")
    print(f"  Time Period: {result.time_period}")
    print(f"  Entities: {result.entities_mentioned}")
    print(f"  Confidence: {result.confidence:.2f}")
    
    # Check what SHOULD have been detected
    print(f"\n{'='*60}")
    print(f"DETECTION ANALYSIS")
    print(f"{'='*60}")
    
    query_lower = query.lower()
    
    # Check for numerical indicators
    numerical_terms = ['margin', 'revenue', 'profit', 'growth', 'percentage', '%']
    found_numerical = [t for t in numerical_terms if t in query_lower]
    print(f"Numerical terms found: {found_numerical}")
    
    # Check for opinion indicators
    opinion_terms = ['cyclical', 'structural', 'sustainable', 'should', 'will', 'outlook']
    found_opinion = [t for t in opinion_terms if t in query_lower]
    print(f"Opinion terms found: {found_opinion}")
    
    # Recommendation
    if found_numerical and found_opinion:
        print(f"\n⚠️  HYBRID QUERY DETECTED!")
        print(f"    Query has BOTH numerical ({found_numerical}) AND opinion ({found_opinion}) aspects.")
        print(f"    Current classification: {result.query_type.value}")
        print(f"    Recommendation: Retrieve FINANCIAL_LINE nodes even for opinion queries")
    
    return result

# Test with the problematic query
debug_classification("Is Apple's gross margin pressure cyclical or structural?")

# Also test related queries
debug_classification("What is Apple's gross margin?")  # Should be NUMERICAL
debug_classification("Why did Apple's margins decline?")  # Should be CAUSAL
```

---

## Fix 1: Enhance Query Classifier for Hybrid Queries

```python
# In src/opmech/query_classifier.py

class QueryClassifier:
    
    # Add new attribute
    NUMERICAL_ASPECT_TERMS = [
        'margin', 'revenue', 'profit', 'income', 'expense', 'cost',
        'growth', 'decline', 'increase', 'decrease', 'percentage', '%',
        'ratio', 'eps', 'earnings', 'sales'
    ]
    
    def classify(self, query: str) -> QueryClassification:
        # ... existing classification logic ...
        
        # NEW: Detect hybrid queries
        has_numerical_aspect = self._has_numerical_aspect(query)
        
        # Store this for operators to use
        result = QueryClassification(
            query_type=best_type,
            complexity=complexity,
            expects_number=expects_number,
            time_period=time_period,
            entities_mentioned=entities,
            confidence=best_score,
            # NEW FIELD:
            has_numerical_aspect=has_numerical_aspect  
        )
        
        return result
    
    def _has_numerical_aspect(self, query: str) -> bool:
        """Check if query has numerical aspects even if not purely numerical."""
        query_lower = query.lower()
        return any(term in query_lower for term in self.NUMERICAL_ASPECT_TERMS)
```

---

## Fix 2: Update Operator A Seed Selection

```python
# In src/opmech/operators.py - OperatorA class

class OperatorA(BaseOperator):
    """Structure-First Operator"""
    
    def _get_initial_seeds(
        self, 
        query: str, 
        query_class: QueryClassification
    ) -> List[GraphNode]:
        """Start from XBRL/financial nodes."""
        seeds = []
        
        # 1. ALWAYS search for FINANCIAL_LINE nodes matching query terms
        # Extract key financial terms from query
        financial_terms = self._extract_financial_terms(query)
        
        for term in financial_terms:
            financial_nodes = self.graph.search_by_type(
                NodeType.FINANCIAL_LINE,
                query=term,
                limit=5
            )
            seeds.extend(financial_nodes)
        
        # 2. Also do semantic search on FINANCIAL_LINE for the full query
        semantic_financial = self.graph.semantic_search(
            query,
            node_types=[NodeType.FINANCIAL_LINE],
            limit=5
        )
        seeds.extend(semantic_financial)
        
        # 3. Add exact entity matches (existing logic)
        for entity in query_class.entities_mentioned:
            entity_nodes = self.graph.search_by_content(
                entity,
                node_types=[NodeType.ENTITY, NodeType.FINANCIAL_LINE],
                limit=3
            )
            seeds.extend(entity_nodes)
        
        # 4. If time period mentioned, add temporal seeds (existing logic)
        if query_class.time_period:
            temporal_nodes = self.graph.search_by_metadata(
                "period", query_class.time_period,
                limit=5
            )
            seeds.extend(temporal_nodes)
        
        # 5. NEW: For queries with numerical aspects (even if OPINION type),
        #    ensure we have FINANCIAL_LINE seeds
        if hasattr(query_class, 'has_numerical_aspect') and query_class.has_numerical_aspect:
            if not any(s.node_type == NodeType.FINANCIAL_LINE for s in seeds):
                # Force add some financial nodes
                fallback_financial = self.graph.search_by_type(
                    NodeType.FINANCIAL_LINE,
                    query=query,
                    limit=5
                )
                seeds.extend(fallback_financial)
        
        return list(set(seeds))[:15]  # Dedupe and limit
    
    def _extract_financial_terms(self, query: str) -> List[str]:
        """Extract financial terms from query for targeted search."""
        query_lower = query.lower()
        
        # Map common terms to XBRL-friendly search terms
        term_mappings = {
            'gross margin': ['gross margin', 'gross profit', 'cost of sales', 'GrossProfit'],
            'margin': ['margin', 'profit margin', 'gross profit'],
            'revenue': ['revenue', 'net sales', 'total revenue', 'Revenues'],
            'profit': ['profit', 'net income', 'operating income', 'NetIncome'],
            'cost': ['cost', 'expenses', 'cost of sales', 'operating expenses'],
            'earnings': ['earnings', 'eps', 'net income', 'EarningsPerShare'],
        }
        
        found_terms = []
        for key, variations in term_mappings.items():
            if key in query_lower:
                found_terms.extend(variations)
        
        # Also add the raw query terms
        found_terms.append(query)
        
        return list(set(found_terms))
```

---

## Fix 3: Enhance Graph Search for XBRL Tags

```python
# In src/opmech/graph_interface.py

class GraphInterface:
    
    def search_by_type(
        self, 
        node_type: NodeType, 
        query: str, 
        limit: int = 10
    ) -> List[GraphNode]:
        """Search nodes by type with enhanced XBRL matching."""
        
        # For FINANCIAL_LINE, also search XBRL tags
        if node_type == NodeType.FINANCIAL_LINE:
            cypher = """
            MATCH (n:FINANCIAL_LINE)
            WHERE toLower(n.content) CONTAINS toLower($query)
               OR toLower(n.xbrl_tag) CONTAINS toLower($query)
               OR toLower(n.label) CONTAINS toLower($query)
            RETURN n
            ORDER BY 
                CASE 
                    WHEN toLower(n.xbrl_tag) CONTAINS toLower($query) THEN 0
                    WHEN toLower(n.label) CONTAINS toLower($query) THEN 1
                    ELSE 2
                END
            LIMIT $limit
            """
        else:
            cypher = """
            MATCH (n)
            WHERE $node_type IN labels(n)
              AND toLower(n.content) CONTAINS toLower($query)
            RETURN n
            LIMIT $limit
            """
        
        with self.driver.session() as session:
            result = session.run(cypher, {
                "node_type": node_type.value,
                "query": query,
                "limit": limit
            })
            return [self._node_from_record(r["n"]) for r in result]
    
    def search_financial_by_concept(
        self, 
        concepts: List[str], 
        limit: int = 10
    ) -> List[GraphNode]:
        """Search FINANCIAL_LINE nodes by XBRL concept names."""
        
        cypher = """
        MATCH (n:FINANCIAL_LINE)
        WHERE any(concept IN $concepts WHERE 
            toLower(n.xbrl_tag) CONTAINS toLower(concept)
            OR toLower(n.label) CONTAINS toLower(concept)
        )
        RETURN n
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, {"concepts": concepts, "limit": limit})
            return [self._node_from_record(r["n"]) for r in result]
```

---

## Fix 4: Add Margin-Specific XBRL Concepts

```python
# In src/opmech/constants.py (create if doesn't exist)

# XBRL concepts related to margins
MARGIN_XBRL_CONCEPTS = [
    # Gross Margin / Gross Profit
    "GrossProfit",
    "CostOfGoodsSold",
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    
    # Operating Margin
    "OperatingIncome",
    "OperatingExpenses",
    "OperatingIncomeLoss",
    
    # Net Margin
    "NetIncome",
    "NetIncomeLoss",
    "ProfitLoss",
    
    # Revenue (for calculating margins)
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    
    # Segment margins (Apple specific)
    "RevenueFromContractWithCustomerByProduct",
    "GrossMarginPercentage",
]

# Query term to XBRL concept mapping
QUERY_TO_XBRL_MAP = {
    "gross margin": ["GrossProfit", "CostOfGoodsSold", "CostOfRevenue"],
    "operating margin": ["OperatingIncome", "OperatingExpenses"],
    "net margin": ["NetIncome", "NetIncomeLoss"],
    "profit margin": ["GrossProfit", "OperatingIncome", "NetIncome"],
    "margin": ["GrossProfit", "OperatingIncome", "NetIncome", "CostOfGoodsSold"],
    "revenue": ["Revenues", "SalesRevenueNet"],
    "cost": ["CostOfGoodsSold", "CostOfRevenue", "OperatingExpenses"],
}
```

---

## Fix 5: Update Operator A to Use XBRL Concepts

```python
# In src/opmech/operators.py

from .constants import QUERY_TO_XBRL_MAP, MARGIN_XBRL_CONCEPTS

class OperatorA(BaseOperator):
    
    def _get_initial_seeds(self, query: str, query_class: QueryClassification) -> List[GraphNode]:
        seeds = []
        query_lower = query.lower()
        
        # 1. Find relevant XBRL concepts for this query
        relevant_concepts = []
        for term, concepts in QUERY_TO_XBRL_MAP.items():
            if term in query_lower:
                relevant_concepts.extend(concepts)
        
        # 2. Search by XBRL concepts
        if relevant_concepts:
            concept_nodes = self.graph.search_financial_by_concept(
                list(set(relevant_concepts)),
                limit=10
            )
            seeds.extend(concept_nodes)
            print(f"[DEBUG] Found {len(concept_nodes)} nodes from XBRL concepts: {relevant_concepts[:3]}...")
        
        # 3. Fallback to text search if no concept matches
        if not seeds:
            text_nodes = self.graph.search_by_type(
                NodeType.FINANCIAL_LINE,
                query=query,
                limit=10
            )
            seeds.extend(text_nodes)
        
        # ... rest of existing logic ...
        
        return list(set(seeds))[:15]
```

---

## Debug Task 4: Test the Fixes

After implementing fixes, run this test:

```python
# test_margin_query.py

from src.opmech.system import OpMechGraphRAG
from src.opmech.query_classifier import QueryClassifier

def test_gross_margin_query():
    """Test that gross margin query now retrieves actual margin data."""
    
    system = OpMechGraphRAG(graph, llm, config)
    
    query = "Is Apple's gross margin pressure cyclical or structural?"
    result = system.query(query)
    
    print(f"\n{'='*60}")
    print(f"TEST: Gross Margin Query")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Mode: {result.mode.value}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Hops: {result.hops_used}")
    
    # Check if we got FINANCIAL_LINE nodes
    financial_A = [n for n in result.evidence_A if n.node_type.value == "FINANCIAL_LINE"]
    financial_B = [n for n in result.evidence_B if n.node_type.value == "FINANCIAL_LINE"]
    
    print(f"\nEvidence Analysis:")
    print(f"  Operator A: {len(result.evidence_A)} total, {len(financial_A)} FINANCIAL_LINE")
    print(f"  Operator B: {len(result.evidence_B)} total, {len(financial_B)} FINANCIAL_LINE")
    
    # Check if any evidence mentions actual margin percentages
    margin_evidence = []
    for node in result.evidence_A + result.evidence_B:
        if any(x in node.content.lower() for x in ['%', 'percent', '36', '44', '46', '74']):
            if 'margin' in node.content.lower() or 'gross' in node.content.lower():
                margin_evidence.append(node)
    
    print(f"  Margin-related evidence: {len(margin_evidence)} nodes")
    
    if margin_evidence:
        print(f"\nMargin Evidence Found:")
        for node in margin_evidence[:5]:
            print(f"  [{node.node_type.value}] {node.content[:150]}...")
    else:
        print(f"\n⚠️  WARNING: No margin percentage data found in evidence!")
    
    # Check the answer
    print(f"\nAnswer Preview:")
    print(f"{result.answer[:500]}...")
    
    # Validate answer mentions actual figures
    answer_lower = result.answer.lower()
    has_percentages = '%' in result.answer or 'percent' in answer_lower
    has_specific_figures = any(fig in answer_lower for fig in ['36', '44', '46', '74'])
    
    print(f"\nAnswer Quality Check:")
    print(f"  Contains percentages: {'✅' if has_percentages else '❌'}")
    print(f"  Contains specific figures: {'✅' if has_specific_figures else '❌'}")
    
    # Final verdict
    if len(financial_A) > 0 and has_percentages:
        print(f"\n✅ FIX SUCCESSFUL: Margin data is now being retrieved!")
    else:
        print(f"\n❌ FIX INCOMPLETE: Still missing margin data")
        print(f"   - Check if graph has margin nodes")
        print(f"   - Check seed selection logic")
        print(f"   - Check XBRL concept mapping")

if __name__ == "__main__":
    test_gross_margin_query()
```

---

## Summary of Fixes

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Missing gross margin data | Query classified as OPINION, skipped FINANCIAL_LINE | Add `has_numerical_aspect` flag to hybrid queries |
| Operator A missed margin nodes | Seed selection didn't search XBRL concepts | Add XBRL concept mapping and search |
| Generic risk factor answers | Only TEXT_SECTION and NOTE nodes retrieved | Force FINANCIAL_LINE retrieval for margin-related queries |
| No actual percentages in answer | Evidence didn't include margin data | Enhanced graph search with XBRL tag matching |

---

## Validation Checklist

After implementing fixes, verify:

- [ ] `debug_classification()` shows `has_numerical_aspect=True` for margin queries
- [ ] `debug_seed_selection()` shows FINANCIAL_LINE nodes with margin data
- [ ] Graph query confirms margin nodes exist
- [ ] Test query returns evidence with actual margin percentages
- [ ] Final answer mentions specific figures (36%, 44%, 46%, 74%)

---

## Expected Outcome

After fixes, the query "Is Apple's gross margin pressure cyclical or structural?" should:

1. **Still select EXPLORE mode** (correct for opinion)
2. **Still use MERGE_EQUAL trust** (correct for opinion)
3. **BUT NOW include evidence like:**
   - "Gross margin was 46.2% in FY2024, up from 44.1% in FY2023"
   - "Products gross margin: 36.3%, Services gross margin: 74.0%"
4. **Answer should reference actual figures** when discussing trends

Good luck debugging! 🔍
