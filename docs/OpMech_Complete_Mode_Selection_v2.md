# OpMech Complete Mode Selection & Operator Reliability System

## The Core Problem

The system currently has two issues:

### Issue 1: Mode Selection Not Working
- Simple factual queries showing ADAPTIVE instead of EXPLOIT
- Confidence stuck around 60%

### Issue 2: Wrong Answer Merging (More Critical!)
```
Operator A: $383.29B (CORRECT - from XBRL financial data)
Operator B: $394.33B (WRONG - from narrative text, possibly different period)

Current output: "around $390B" (INCORRECT MERGE!)
Correct output: "$383.29B" (trust the authoritative source)
```

**The commutator tells us operators disagree, but doesn't tell us WHO IS RIGHT.**

---

## Root Cause Analysis

### Why Did This Happen?

1. **Operator B found a TEXT_SECTION with "$394.33B"** - This might be:
   - Trailing twelve months (TTM) at a different date
   - A forward-looking projection
   - Cumulative revenue mentioned in context
   - A comparison figure from previous year

2. **System treated both operators equally** - No concept of "authoritative source"

3. **ADAPTIVE mode merged them** - Instead of identifying the correct answer

### The Fundamental Insight

**For factual queries, not all evidence is equal:**

| Source Type | Authoritativeness | Why |
|-------------|-------------------|-----|
| XBRL FINANCIAL_LINE | ⭐⭐⭐⭐⭐ | SEC-mandated, machine-readable, audited |
| TABLE data | ⭐⭐⭐⭐ | Structured, typically from financials |
| MD&A TEXT_SECTION | ⭐⭐⭐ | Context-dependent, may be comparative |
| NOTE | ⭐⭐ | Explanatory, may reference multiple periods |
| General narrative | ⭐ | Could be forward-looking or contextual |

---

## The Complete Solution

We need THREE interconnected systems:

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY PROCESSING                              │
├─────────────────────────────────────────────────────────────────┤
│  1. QUERY CLASSIFIER                                            │
│     - Detect: numerical/causal/opinion/comparison               │
│     - Detect: time period mentioned                             │
│     - Detect: complexity level                                  │
├─────────────────────────────────────────────────────────────────┤
│  2. OPERATOR RELIABILITY SCORER                                 │
│     - Score each operator's evidence quality                    │
│     - Match evidence type to query type                         │
│     - Compute reliability gap                                   │
├─────────────────────────────────────────────────────────────────┤
│  3. MODE SELECTOR                                               │
│     - Use reliability scores + divergence                       │
│     - Determine: EXPLOIT / ADAPTIVE / EXPLORE                   │
│     - Decide: Trust A / Trust B / Merge                         │
├─────────────────────────────────────────────────────────────────┤
│  4. ANSWER GENERATOR                                            │
│     - If reliability gap large: use trusted operator            │
│     - If gap small: merge with attribution                      │
│     - Always show confidence and source                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task 1: Create the Complete Mode Selection System

Create `src/opmech/mode_selection.py`:

```python
"""
OpMech Mode Selection and Operator Reliability System

This module determines:
1. Which mode to use (EXPLOIT/ADAPTIVE/EXPLORE)
2. Which operator to trust when they disagree
3. How confident we are in the final answer

Key insight: The commutator measures DISAGREEMENT, but we also need to 
measure RELIABILITY to determine WHO IS RIGHT when operators disagree.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
import numpy as np
from loguru import logger


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class QueryMode(Enum):
    """Final query mode."""
    EXPLOIT = "EXPLOIT"    # High confidence, clear answer
    ADAPTIVE = "ADAPTIVE"  # Moderate confidence, balanced view
    EXPLORE = "EXPLORE"    # Low confidence, multiple perspectives


class QueryType(Enum):
    """Type of query for reliability matching."""
    NUMERICAL = "numerical"      # "What was revenue?" → Trust XBRL
    TEMPORAL = "temporal"        # "How did X change?" → Trust both
    CAUSAL = "causal"           # "Why did X happen?" → Trust narrative
    DESCRIPTIVE = "descriptive"  # "What are the risk factors?" → Trust narrative
    COMPARATIVE = "comparative"  # "Compare X to Y" → Trust both
    OPINION = "opinion"         # "Is X sustainable?" → Trust narrative, lower confidence


class TrustDecision(Enum):
    """Who to trust when operators disagree."""
    TRUST_A = "trust_operator_a"          # Structure-first is more reliable
    TRUST_B = "trust_operator_b"          # Narrative-first is more reliable  
    MERGE_EQUAL = "merge_equal"           # Both equally reliable
    MERGE_WEIGHTED = "merge_weighted"     # Merge but weight by reliability
    CONFLICT = "conflict"                 # Irreconcilable conflict, present both


@dataclass
class QueryClassification:
    """Complete query classification."""
    query_type: QueryType
    complexity: str              # "simple", "moderate", "complex"
    time_period: Optional[str]   # Extracted time period if any
    numerical_expected: bool     # Expects a specific number?
    entities_mentioned: List[str]
    confidence: float            # How confident in classification


@dataclass 
class OperatorReliability:
    """Reliability assessment for one operator."""
    operator_name: str
    reliability_score: float     # 0-1, higher = more reliable for this query
    evidence_quality: float      # Quality of evidence found
    source_authority: float      # Authority of sources (XBRL > narrative)
    query_fit: float            # How well evidence matches query type
    path_confidence: float       # Path confidence from traversal
    evidence_breakdown: Dict[str, int]  # Count by node type
    reasoning: str


@dataclass
class ModeDecision:
    """Complete mode decision with all context."""
    mode: QueryMode
    confidence: float
    trust_decision: TrustDecision
    operator_A_reliability: OperatorReliability
    operator_B_reliability: OperatorReliability
    reliability_gap: float       # |A - B| reliability difference
    reasoning: str
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# QUERY CLASSIFIER
# =============================================================================

class QueryClassifier:
    """
    Classifies queries to determine what type of evidence is most authoritative.
    """
    
    # Patterns for query type detection
    NUMERICAL_PATTERNS = [
        r"what (was|is|were|are) .*(revenue|income|expense|cost|margin|profit|sales|earnings)",
        r"how much .*(revenue|cost|expense|profit|did .* make|did .* spend)",
        r"total .*(revenue|sales|income|expense|cost|profit)",
        r"(net|gross|operating) (income|profit|margin|revenue)",
        r"what is the (value|amount|total|sum)",
        r"how many (shares|employees|stores|units)",
        r"\b(eps|p/e|roi|roa|roe)\b",
    ]
    
    TEMPORAL_PATTERNS = [
        r"how did .* (change|grow|decline|increase|decrease)",
        r"(change|growth|decline|trend) (from|between|over)",
        r"year.over.year|yoy|quarter.over.quarter|qoq",
        r"compared to (last|previous|prior)",
        r"from fy\d{4} to fy\d{4}",
        r"over the (past|last) \d+ (year|quarter|month)",
    ]
    
    CAUSAL_PATTERNS = [
        r"why did",
        r"what (caused|drove|contributed|led to|resulted in)",
        r"(reason|factor|driver)s? (for|behind|of)",
        r"explain (why|how|the)",
        r"what (is|are) the (cause|reason|factor)",
    ]
    
    DESCRIPTIVE_PATTERNS = [
        r"what (is|are) .*(strategy|approach|policy|plan)",
        r"describe",
        r"(risk|opportunity|threat|strength|weakness) factor",
        r"what does .* (do|make|sell|provide)",
        r"how does .* (work|operate|function)",
    ]
    
    COMPARATIVE_PATTERNS = [
        r"compare|comparison|versus|vs\.?|compared to",
        r"(difference|similarity) between",
        r"(better|worse|higher|lower) than",
        r"relative to",
        r"benchmark|industry average",
    ]
    
    OPINION_PATTERNS = [
        r"(is|are) .* (sustainable|viable|risky|safe|good|bad)",
        r"should .* (invest|buy|sell|increase|decrease)",
        r"(will|would|could|might) .* (grow|decline|succeed|fail)",
        r"(outlook|forecast|prediction|expectation)",
        r"do you (think|believe|recommend)",
    ]
    
    # Time period extraction
    TIME_PATTERNS = [
        r"fy\s*(\d{4})",
        r"fiscal\s*(year\s*)?(\d{4})",
        r"q([1-4])\s*(\d{4})",
        r"(\d{4})\s*(annual|yearly)",
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{4}",
    ]
    
    def classify(self, query: str) -> QueryClassification:
        """Classify a query for reliability matching."""
        query_lower = query.lower()
        
        # Detect query type
        query_type = self._detect_query_type(query_lower)
        
        # Detect complexity
        complexity = self._detect_complexity(query_lower, query_type)
        
        # Extract time period
        time_period = self._extract_time_period(query_lower)
        
        # Check if numerical answer expected
        numerical_expected = self._expects_numerical_answer(query_lower, query_type)
        
        # Extract entities (simplified)
        entities = self._extract_entities(query)
        
        # Confidence in classification
        confidence = self._compute_classification_confidence(query_lower, query_type)
        
        return QueryClassification(
            query_type=query_type,
            complexity=complexity,
            time_period=time_period,
            numerical_expected=numerical_expected,
            entities_mentioned=entities,
            confidence=confidence
        )
    
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the primary query type."""
        scores = {
            QueryType.NUMERICAL: self._pattern_score(query, self.NUMERICAL_PATTERNS),
            QueryType.TEMPORAL: self._pattern_score(query, self.TEMPORAL_PATTERNS),
            QueryType.CAUSAL: self._pattern_score(query, self.CAUSAL_PATTERNS),
            QueryType.DESCRIPTIVE: self._pattern_score(query, self.DESCRIPTIVE_PATTERNS),
            QueryType.COMPARATIVE: self._pattern_score(query, self.COMPARATIVE_PATTERNS),
            QueryType.OPINION: self._pattern_score(query, self.OPINION_PATTERNS),
        }
        
        # Get highest scoring type
        best_type = max(scores, key=scores.get)
        
        # If no strong match, default based on keywords
        if scores[best_type] == 0:
            if any(word in query for word in ["what", "how much", "total"]):
                return QueryType.NUMERICAL
            elif any(word in query for word in ["why", "reason", "cause"]):
                return QueryType.CAUSAL
            else:
                return QueryType.DESCRIPTIVE
        
        return best_type
    
    def _pattern_score(self, query: str, patterns: List[str]) -> int:
        """Count how many patterns match."""
        return sum(1 for p in patterns if re.search(p, query))
    
    def _detect_complexity(self, query: str, query_type: QueryType) -> str:
        """Detect query complexity."""
        # Simple indicators
        simple_indicators = [
            len(query.split()) < 10,
            query_type == QueryType.NUMERICAL,
            "what is" in query or "what was" in query,
            query.count("?") <= 1,
        ]
        
        # Complex indicators
        complex_indicators = [
            len(query.split()) > 20,
            query_type in [QueryType.CAUSAL, QueryType.OPINION],
            " and " in query and " or " in query,
            query.count(",") > 2,
            any(word in query for word in ["analyze", "evaluate", "assess", "compare"]),
        ]
        
        simple_score = sum(simple_indicators)
        complex_score = sum(complex_indicators)
        
        if simple_score >= 3 and complex_score < 2:
            return "simple"
        elif complex_score >= 2:
            return "complex"
        else:
            return "moderate"
    
    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period if mentioned."""
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, query)
            if match:
                return match.group(0)
        return None
    
    def _expects_numerical_answer(self, query: str, query_type: QueryType) -> bool:
        """Check if query expects a specific number."""
        if query_type == QueryType.NUMERICAL:
            return True
        
        numerical_words = ["how much", "how many", "total", "amount", "value", "percentage", "%"]
        return any(word in query for word in numerical_words)
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract mentioned entities (simplified)."""
        # Look for capitalized words that might be entities
        words = query.split()
        entities = []
        for word in words:
            # Skip common words
            if word.lower() in ["what", "how", "why", "the", "a", "an", "is", "was", "were", "are"]:
                continue
            if word[0].isupper() and len(word) > 2:
                entities.append(word)
        return entities
    
    def _compute_classification_confidence(self, query: str, query_type: QueryType) -> float:
        """Compute confidence in the classification."""
        pattern_map = {
            QueryType.NUMERICAL: self.NUMERICAL_PATTERNS,
            QueryType.TEMPORAL: self.TEMPORAL_PATTERNS,
            QueryType.CAUSAL: self.CAUSAL_PATTERNS,
            QueryType.DESCRIPTIVE: self.DESCRIPTIVE_PATTERNS,
            QueryType.COMPARATIVE: self.COMPARATIVE_PATTERNS,
            QueryType.OPINION: self.OPINION_PATTERNS,
        }
        
        matches = self._pattern_score(query, pattern_map.get(query_type, []))
        
        if matches >= 2:
            return 0.95
        elif matches == 1:
            return 0.80
        else:
            return 0.60


# =============================================================================
# OPERATOR RELIABILITY SCORER
# =============================================================================

class OperatorReliabilityScorer:
    """
    Scores how reliable each operator's evidence is for a given query.
    
    Key insight: Different query types need different evidence:
    - Numerical queries → XBRL/financial data is authoritative
    - Causal queries → Narrative/MD&A is authoritative
    - Mixed queries → Both are valuable
    """
    
    # Source authority scores by node type
    SOURCE_AUTHORITY = {
        "FINANCIAL_LINE": 1.0,    # XBRL-tagged, audited
        "TABLE_ROW": 0.9,         # Structured data
        "TABLE": 0.85,            # Structured data
        "TEXT_SECTION": 0.6,      # Narrative, may be contextual
        "NOTE": 0.5,              # Explanatory, may reference multiple periods
        "ENTITY": 0.4,            # Entity mentions, need context
    }
    
    # Query type to preferred evidence mapping
    QUERY_EVIDENCE_FIT = {
        # (query_type, node_type) → fit score
        (QueryType.NUMERICAL, "FINANCIAL_LINE"): 1.0,
        (QueryType.NUMERICAL, "TABLE_ROW"): 0.9,
        (QueryType.NUMERICAL, "TEXT_SECTION"): 0.4,  # Numbers in text may be out of context
        (QueryType.NUMERICAL, "NOTE"): 0.3,
        
        (QueryType.TEMPORAL, "FINANCIAL_LINE"): 0.9,
        (QueryType.TEMPORAL, "TEXT_SECTION"): 0.7,
        (QueryType.TEMPORAL, "NOTE"): 0.6,
        
        (QueryType.CAUSAL, "FINANCIAL_LINE"): 0.4,
        (QueryType.CAUSAL, "TEXT_SECTION"): 1.0,     # MD&A explains causes
        (QueryType.CAUSAL, "NOTE"): 0.8,
        
        (QueryType.DESCRIPTIVE, "TEXT_SECTION"): 1.0,
        (QueryType.DESCRIPTIVE, "NOTE"): 0.9,
        (QueryType.DESCRIPTIVE, "FINANCIAL_LINE"): 0.3,
        
        (QueryType.OPINION, "TEXT_SECTION"): 0.8,
        (QueryType.OPINION, "NOTE"): 0.7,
        (QueryType.OPINION, "FINANCIAL_LINE"): 0.2,
    }
    
    def score_operator(
        self,
        operator_name: str,
        evidence_types: Dict[str, int],
        path_confidence: float,
        query_classification: QueryClassification,
    ) -> OperatorReliability:
        """
        Score how reliable an operator's evidence is for this query.
        """
        
        # Calculate evidence quality (weighted by source authority)
        evidence_quality = self._compute_evidence_quality(evidence_types)
        
        # Calculate source authority (how authoritative are the sources?)
        source_authority = self._compute_source_authority(evidence_types)
        
        # Calculate query fit (how well does evidence match query type?)
        query_fit = self._compute_query_fit(evidence_types, query_classification.query_type)
        
        # Combine into overall reliability
        reliability_score = self._combine_reliability(
            evidence_quality=evidence_quality,
            source_authority=source_authority,
            query_fit=query_fit,
            path_confidence=path_confidence,
            query_classification=query_classification,
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            operator_name, evidence_types, query_classification,
            evidence_quality, source_authority, query_fit, reliability_score
        )
        
        return OperatorReliability(
            operator_name=operator_name,
            reliability_score=reliability_score,
            evidence_quality=evidence_quality,
            source_authority=source_authority,
            query_fit=query_fit,
            path_confidence=path_confidence,
            evidence_breakdown=evidence_types,
            reasoning=reasoning
        )
    
    def _compute_evidence_quality(self, evidence_types: Dict[str, int]) -> float:
        """Compute overall evidence quality."""
        if not evidence_types:
            return 0.0
        
        total = sum(evidence_types.values())
        if total == 0:
            return 0.0
        
        # Weighted sum by source authority
        weighted_sum = sum(
            count * self.SOURCE_AUTHORITY.get(node_type, 0.5)
            for node_type, count in evidence_types.items()
        )
        
        return weighted_sum / total
    
    def _compute_source_authority(self, evidence_types: Dict[str, int]) -> float:
        """Compute authority of sources (higher if more XBRL/structured data)."""
        total = sum(evidence_types.values())
        if total == 0:
            return 0.0
        
        # Proportion of high-authority sources
        high_authority = evidence_types.get("FINANCIAL_LINE", 0) + evidence_types.get("TABLE_ROW", 0)
        
        return high_authority / total
    
    def _compute_query_fit(
        self, 
        evidence_types: Dict[str, int], 
        query_type: QueryType
    ) -> float:
        """Compute how well evidence matches query type."""
        if not evidence_types:
            return 0.0
        
        total = sum(evidence_types.values())
        if total == 0:
            return 0.0
        
        # Weighted sum by query-evidence fit
        weighted_sum = 0.0
        for node_type, count in evidence_types.items():
            fit = self.QUERY_EVIDENCE_FIT.get((query_type, node_type), 0.5)
            weighted_sum += count * fit
        
        return weighted_sum / total
    
    def _combine_reliability(
        self,
        evidence_quality: float,
        source_authority: float,
        query_fit: float,
        path_confidence: float,
        query_classification: QueryClassification,
    ) -> float:
        """Combine factors into overall reliability score."""
        
        # Weights depend on query type
        if query_classification.numerical_expected:
            # For numerical queries, source authority is CRITICAL
            weights = {
                "evidence_quality": 0.15,
                "source_authority": 0.40,  # HIGH weight on XBRL
                "query_fit": 0.30,
                "path_confidence": 0.15,
            }
        elif query_classification.query_type in [QueryType.CAUSAL, QueryType.DESCRIPTIVE]:
            # For narrative queries, query fit matters more
            weights = {
                "evidence_quality": 0.20,
                "source_authority": 0.15,
                "query_fit": 0.45,         # HIGH weight on right evidence type
                "path_confidence": 0.20,
            }
        else:
            # Balanced
            weights = {
                "evidence_quality": 0.25,
                "source_authority": 0.25,
                "query_fit": 0.30,
                "path_confidence": 0.20,
            }
        
        reliability = (
            weights["evidence_quality"] * evidence_quality +
            weights["source_authority"] * source_authority +
            weights["query_fit"] * query_fit +
            weights["path_confidence"] * path_confidence
        )
        
        return min(1.0, max(0.0, reliability))
    
    def _generate_reasoning(
        self,
        operator_name: str,
        evidence_types: Dict[str, int],
        query_classification: QueryClassification,
        evidence_quality: float,
        source_authority: float,
        query_fit: float,
        reliability_score: float,
    ) -> str:
        """Generate human-readable reasoning."""
        
        parts = []
        
        # Evidence breakdown
        total = sum(evidence_types.values())
        financial_pct = evidence_types.get("FINANCIAL_LINE", 0) / total * 100 if total > 0 else 0
        narrative_pct = (evidence_types.get("TEXT_SECTION", 0) + evidence_types.get("NOTE", 0)) / total * 100 if total > 0 else 0
        
        parts.append(f"{operator_name}: {financial_pct:.0f}% financial, {narrative_pct:.0f}% narrative")
        
        # Query fit assessment
        if query_classification.numerical_expected:
            if source_authority > 0.5:
                parts.append("high XBRL coverage for numerical query")
            else:
                parts.append("low XBRL coverage for numerical query (less reliable)")
        
        # Overall assessment
        if reliability_score > 0.75:
            parts.append("HIGH reliability")
        elif reliability_score > 0.5:
            parts.append("MODERATE reliability")
        else:
            parts.append("LOW reliability")
        
        return "; ".join(parts)


# =============================================================================
# MODE SELECTOR
# =============================================================================

class ModeSelector:
    """
    Determines query mode and trust decision.
    
    Combines:
    1. Commutator (divergence between operators)
    2. Operator reliability (who to trust)
    3. Query classification (what type of query)
    4. Trajectory (how divergence changed over hops)
    """
    
    def __init__(self):
        self.query_classifier = QueryClassifier()
        self.reliability_scorer = OperatorReliabilityScorer()
    
    def determine_mode(
        self,
        commutator,
        trajectory: List,
        query: str,
        operator_A_evidence_types: Dict[str, int],
        operator_B_evidence_types: Dict[str, int],
        operator_A_path_confidence: float,
        operator_B_path_confidence: float,
    ) -> ModeDecision:
        """
        Complete mode determination with trust decision.
        """
        
        # Step 1: Classify query
        query_class = self.query_classifier.classify(query)
        logger.debug(f"Query classified as: {query_class.query_type.value}, complexity={query_class.complexity}")
        
        # Step 2: Score operator reliability
        reliability_A = self.reliability_scorer.score_operator(
            "OperatorA",
            operator_A_evidence_types,
            operator_A_path_confidence,
            query_class
        )
        
        reliability_B = self.reliability_scorer.score_operator(
            "OperatorB", 
            operator_B_evidence_types,
            operator_B_path_confidence,
            query_class
        )
        
        logger.debug(f"Reliability A: {reliability_A.reliability_score:.3f}, B: {reliability_B.reliability_score:.3f}")
        
        # Step 3: Compute reliability gap
        reliability_gap = abs(reliability_A.reliability_score - reliability_B.reliability_score)
        
        # Step 4: Determine trust decision
        trust_decision = self._determine_trust(
            commutator, reliability_A, reliability_B, reliability_gap, query_class
        )
        
        # Step 5: Determine mode
        mode, confidence = self._determine_mode_and_confidence(
            commutator, trajectory, query_class,
            reliability_A, reliability_B, trust_decision
        )
        
        # Step 6: Generate warnings if any
        warnings = self._generate_warnings(
            commutator, reliability_A, reliability_B, trust_decision
        )
        
        # Step 7: Generate reasoning
        reasoning = self._generate_reasoning(
            mode, trust_decision, commutator, query_class,
            reliability_A, reliability_B
        )
        
        return ModeDecision(
            mode=mode,
            confidence=confidence,
            trust_decision=trust_decision,
            operator_A_reliability=reliability_A,
            operator_B_reliability=reliability_B,
            reliability_gap=reliability_gap,
            reasoning=reasoning,
            warnings=warnings
        )
    
    def _determine_trust(
        self,
        commutator,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        reliability_gap: float,
        query_class: QueryClassification,
    ) -> TrustDecision:
        """Determine which operator to trust."""
        
        delta_A = commutator.delta_A  # Answer agreement
        
        # If answers agree, no need to choose
        if delta_A < 0.15:
            return TrustDecision.MERGE_EQUAL
        
        # If large reliability gap, trust the more reliable one
        RELIABILITY_GAP_THRESHOLD = 0.25
        
        if reliability_gap > RELIABILITY_GAP_THRESHOLD:
            if reliability_A.reliability_score > reliability_B.reliability_score:
                return TrustDecision.TRUST_A
            else:
                return TrustDecision.TRUST_B
        
        # For numerical queries with answer disagreement, trust higher authority
        if query_class.numerical_expected and delta_A > 0.20:
            if reliability_A.source_authority > reliability_B.source_authority + 0.2:
                return TrustDecision.TRUST_A
            elif reliability_B.source_authority > reliability_A.source_authority + 0.2:
                return TrustDecision.TRUST_B
        
        # Moderate gap - merge but weight by reliability
        if reliability_gap > 0.10:
            return TrustDecision.MERGE_WEIGHTED
        
        # Small gap - merge equally
        return TrustDecision.MERGE_EQUAL
    
    def _determine_mode_and_confidence(
        self,
        commutator,
        trajectory: List,
        query_class: QueryClassification,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trust_decision: TrustDecision,
    ) -> Tuple[QueryMode, float]:
        """Determine mode and confidence."""
        
        delta = commutator.combined
        delta_A = commutator.delta_A
        delta_E = commutator.delta_E
        
        # Analyze trajectory
        trajectory_trend = self._analyze_trajectory(trajectory)
        
        # Base thresholds by complexity
        if query_class.complexity == "simple":
            exploit_threshold = 0.45
            explore_threshold = 0.65
        elif query_class.complexity == "complex":
            exploit_threshold = 0.35
            explore_threshold = 0.55
        else:
            exploit_threshold = 0.40
            explore_threshold = 0.60
        
        # TRUST_A or TRUST_B means we have a clear winner → boost toward EXPLOIT
        if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
            # We know who to trust, so we can be more confident
            trusted_reliability = (
                reliability_A.reliability_score 
                if trust_decision == TrustDecision.TRUST_A 
                else reliability_B.reliability_score
            )
            
            if trusted_reliability > 0.7 and delta_A < 0.40:
                mode = QueryMode.EXPLOIT
                confidence = 0.70 + 0.25 * trusted_reliability
            elif trusted_reliability > 0.5:
                mode = QueryMode.ADAPTIVE
                confidence = 0.55 + 0.20 * trusted_reliability
            else:
                mode = QueryMode.EXPLORE
                confidence = 0.40 + 0.15 * trusted_reliability
        
        # MERGE modes - use combined divergence
        else:
            # Compute mode score
            mode_score = self._compute_mode_score(
                commutator, trajectory_trend, 
                reliability_A, reliability_B, query_class
            )
            
            if mode_score >= exploit_threshold:
                mode = QueryMode.EXPLOIT
            elif mode_score >= explore_threshold:
                mode = QueryMode.ADAPTIVE
            else:
                mode = QueryMode.EXPLORE
            
            # Compute confidence
            confidence = self._compute_confidence(
                mode, commutator, reliability_A, reliability_B, trajectory_trend
            )
        
        # Hard vetoes
        if delta_A > 0.50 and trust_decision not in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
            # Answers really disagree and we don't know who to trust
            mode = QueryMode.EXPLORE
            confidence = min(confidence, 0.50)
        
        if trajectory_trend == "diverging":
            # Things are getting worse
            if mode == QueryMode.EXPLOIT:
                mode = QueryMode.ADAPTIVE
            confidence = min(confidence, 0.60)
        
        return mode, confidence
    
    def _compute_mode_score(
        self,
        commutator,
        trajectory_trend: str,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        query_class: QueryClassification,
    ) -> float:
        """Compute mode score (higher = more toward EXPLOIT)."""
        
        # Answer agreement (40%)
        answer_score = 1 - commutator.delta_A
        
        # Evidence overlap (20%)
        evidence_score = 1 - commutator.delta_E
        
        # Combined divergence (15%)
        combined_score = 1 - commutator.combined
        
        # Trajectory (10%)
        trajectory_score = {
            "converging": 1.0,
            "stable": 0.7,
            "oscillating": 0.4,
            "diverging": 0.1,
        }.get(trajectory_trend, 0.5)
        
        # Average reliability (15%)
        avg_reliability = (reliability_A.reliability_score + reliability_B.reliability_score) / 2
        
        mode_score = (
            0.40 * answer_score +
            0.20 * evidence_score +
            0.15 * combined_score +
            0.10 * trajectory_score +
            0.15 * avg_reliability
        )
        
        return mode_score
    
    def _compute_confidence(
        self,
        mode: QueryMode,
        commutator,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trajectory_trend: str,
    ) -> float:
        """Compute confidence percentage."""
        
        # Base from answer agreement
        if commutator.delta_A < 0.10:
            base = 0.90
        elif commutator.delta_A < 0.20:
            base = 0.80
        elif commutator.delta_A < 0.35:
            base = 0.70
        else:
            base = 0.55
        
        # Adjust by reliability
        avg_reliability = (reliability_A.reliability_score + reliability_B.reliability_score) / 2
        base += (avg_reliability - 0.5) * 0.20
        
        # Adjust by trajectory
        if trajectory_trend == "converging":
            base += 0.05
        elif trajectory_trend == "diverging":
            base -= 0.10
        
        # Mode adjustment
        if mode == QueryMode.EXPLOIT:
            base += 0.05
        elif mode == QueryMode.EXPLORE:
            base -= 0.05
        
        return max(0.30, min(0.95, base))
    
    def _analyze_trajectory(self, trajectory: List) -> str:
        """Analyze trajectory trend."""
        if len(trajectory) < 2:
            return "stable"
        
        deltas = [t.combined for t in trajectory]
        
        improvements = sum(1 for i in range(1, len(deltas)) if deltas[i] < deltas[i-1])
        worsening = sum(1 for i in range(1, len(deltas)) if deltas[i] > deltas[i-1])
        
        if improvements > worsening:
            return "converging"
        elif worsening > improvements:
            return "diverging"
        elif len(trajectory) > 2:
            direction_changes = sum(
                1 for i in range(2, len(deltas))
                if (deltas[i] - deltas[i-1]) * (deltas[i-1] - deltas[i-2]) < 0
            )
            if direction_changes > len(deltas) // 2:
                return "oscillating"
        
        return "stable"
    
    def _generate_warnings(
        self,
        commutator,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trust_decision: TrustDecision,
    ) -> List[str]:
        """Generate warnings for edge cases."""
        warnings = []
        
        # Answer disagreement warning
        if commutator.delta_A > 0.40:
            warnings.append("Significant answer disagreement between operators")
        
        # Low reliability warning
        if reliability_A.reliability_score < 0.4 and reliability_B.reliability_score < 0.4:
            warnings.append("Both operators have low evidence reliability")
        
        # Trust decision with uncertainty
        if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
            trusted = "A" if trust_decision == TrustDecision.TRUST_A else "B"
            other = "B" if trusted == "A" else "A"
            warnings.append(f"Trusting Operator {trusted} over {other} due to higher reliability for this query type")
        
        # Zero evidence overlap
        if commutator.delta_E > 0.90:
            warnings.append("Operators found almost completely different evidence")
        
        return warnings
    
    def _generate_reasoning(
        self,
        mode: QueryMode,
        trust_decision: TrustDecision,
        commutator,
        query_class: QueryClassification,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
    ) -> str:
        """Generate reasoning string."""
        
        parts = [f"Mode: {mode.value}"]
        
        # Query type
        parts.append(f"Query type: {query_class.query_type.value} ({query_class.complexity})")
        
        # Trust decision
        if trust_decision == TrustDecision.TRUST_A:
            parts.append(f"Trusting OperatorA (reliability {reliability_A.reliability_score:.2f} vs {reliability_B.reliability_score:.2f})")
        elif trust_decision == TrustDecision.TRUST_B:
            parts.append(f"Trusting OperatorB (reliability {reliability_B.reliability_score:.2f} vs {reliability_A.reliability_score:.2f})")
        elif trust_decision == TrustDecision.MERGE_WEIGHTED:
            parts.append("Merging with reliability weighting")
        else:
            parts.append("Merging equally")
        
        # Key metrics
        parts.append(f"Δ={commutator.combined:.3f}, Δ_A={commutator.delta_A:.3f}")
        
        return "; ".join(parts)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_mode_selector() -> ModeSelector:
    """Create a configured mode selector."""
    return ModeSelector()
```

---

## Task 2: Update System Integration

Update `src/opmech/system.py` to use the new mode selector:

```python
# Add to imports
from .mode_selection import create_mode_selector, ModeDecision, TrustDecision, QueryMode

class OpMechGraphRAG:
    def __init__(self, config):
        # ... existing init ...
        self.mode_selector = create_mode_selector()
    
    def query(self, query_text: str) -> QueryResult:
        # ... existing traversal code ...
        
        # After final hop, get evidence type breakdowns
        evidence_types_A = self._get_evidence_types(belief_A.evidence)
        evidence_types_B = self._get_evidence_types(belief_B.evidence)
        
        # Determine mode with full context
        mode_decision = self.mode_selector.determine_mode(
            commutator=trajectory[-1],
            trajectory=trajectory,
            query=query_text,
            operator_A_evidence_types=evidence_types_A,
            operator_B_evidence_types=evidence_types_B,
            operator_A_path_confidence=belief_A.path_confidence,
            operator_B_path_confidence=belief_B.path_confidence,
        )
        
        logger.info(f"Mode decision: {mode_decision.reasoning}")
        for warning in mode_decision.warnings:
            logger.warning(f"Mode warning: {warning}")
        
        # Generate answer based on trust decision
        answer = self._generate_answer_with_trust(
            query_text, belief_A, belief_B, 
            mode_decision, trajectory
        )
        
        return QueryResult(
            mode=mode_decision.mode.value,
            confidence=mode_decision.confidence,
            answer=answer,
            trajectory=trajectory,
            # ... other fields ...
        )
    
    def _get_evidence_types(self, evidence: List) -> Dict[str, int]:
        """Get breakdown of evidence by node type."""
        types = {}
        for node in evidence:
            node_type = node.type if hasattr(node, 'type') else "UNKNOWN"
            types[node_type] = types.get(node_type, 0) + 1
        return types
    
    def _generate_answer_with_trust(
        self,
        query: str,
        belief_A,
        belief_B,
        mode_decision: ModeDecision,
        trajectory: List,
    ) -> str:
        """Generate answer respecting trust decision."""
        
        trust = mode_decision.trust_decision
        
        if trust == TrustDecision.TRUST_A:
            # Use Operator A's answer as primary
            return self._generate_trusted_answer(
                query, belief_A, belief_B,
                primary="A",
                mode_decision=mode_decision
            )
        
        elif trust == TrustDecision.TRUST_B:
            # Use Operator B's answer as primary
            return self._generate_trusted_answer(
                query, belief_A, belief_B,
                primary="B",
                mode_decision=mode_decision
            )
        
        elif trust == TrustDecision.MERGE_WEIGHTED:
            # Merge but emphasize more reliable operator
            return self._generate_weighted_answer(
                query, belief_A, belief_B,
                mode_decision=mode_decision
            )
        
        else:
            # Equal merge or conflict
            return self._generate_merged_answer(
                query, belief_A, belief_B,
                mode_decision=mode_decision,
                trajectory=trajectory
            )
    
    def _generate_trusted_answer(
        self,
        query: str,
        belief_A,
        belief_B,
        primary: str,
        mode_decision: ModeDecision,
    ) -> str:
        """Generate answer trusting one operator primarily."""
        
        primary_belief = belief_A if primary == "A" else belief_B
        secondary_belief = belief_B if primary == "A" else belief_A
        primary_rel = mode_decision.operator_A_reliability if primary == "A" else mode_decision.operator_B_reliability
        
        # Build prompt that emphasizes the trusted source
        prompt = f"""Answer this question based primarily on the authoritative evidence.

Question: {query}

PRIMARY EVIDENCE (from {'financial/XBRL data' if primary == 'A' else 'narrative analysis'}):
{self._format_evidence(primary_belief.evidence)}

SECONDARY EVIDENCE (for context only - may contain figures from different periods):
{self._format_evidence(secondary_belief.evidence[:5])}  # Limit secondary

INSTRUCTIONS:
1. Base your answer primarily on the PRIMARY EVIDENCE
2. The primary evidence comes from {'XBRL-tagged financial statements (audited, authoritative)' if primary == 'A' else 'narrative sections (MD&A, notes)'}
3. If secondary evidence shows different figures, note this as a potential difference in reporting period or context
4. Provide a clear, direct answer
5. Confidence level: {mode_decision.confidence:.0%}

Answer:"""
        
        return self._call_llm(prompt)
    
    def _generate_weighted_answer(
        self,
        query: str,
        belief_A,
        belief_B,
        mode_decision: ModeDecision,
    ) -> str:
        """Generate answer weighting operators by reliability."""
        
        rel_A = mode_decision.operator_A_reliability.reliability_score
        rel_B = mode_decision.operator_B_reliability.reliability_score
        
        # Determine which to emphasize
        if rel_A > rel_B:
            primary_evidence = belief_A.evidence
            secondary_evidence = belief_B.evidence
            emphasis = "financial/structured data"
        else:
            primary_evidence = belief_B.evidence
            secondary_evidence = belief_A.evidence
            emphasis = "narrative analysis"
        
        prompt = f"""Answer this question, giving more weight to {emphasis}.

Question: {query}

MORE RELIABLE EVIDENCE ({emphasis}):
{self._format_evidence(primary_evidence)}

ADDITIONAL EVIDENCE:
{self._format_evidence(secondary_evidence)}

Provide a balanced answer, but give more weight to the more reliable source.
Confidence level: {mode_decision.confidence:.0%}

Answer:"""
        
        return self._call_llm(prompt)
    
    def _generate_merged_answer(
        self,
        query: str,
        belief_A,
        belief_B,
        mode_decision: ModeDecision,
        trajectory: List,
    ) -> str:
        """Generate standard merged answer."""
        # Existing merge logic...
        pass
```

---

## Task 3: Test the Fix

After implementing, run the revenue query again:

```python
# Expected behavior:

# Query: "What was Apple's total revenue in FY2023?"
# 
# Query Classification:
#   - Type: NUMERICAL
#   - Complexity: simple
#   - Numerical expected: True
#
# Operator Reliability:
#   - Operator A: 0.85 (high XBRL coverage, authority=0.8)
#   - Operator B: 0.55 (mostly narrative, authority=0.3)
#   - Gap: 0.30 → TRUST_A
#
# Mode Decision:
#   - Trust: TRUST_A
#   - Mode: EXPLOIT
#   - Confidence: 88%
#
# Answer:
#   "Apple's total revenue for FY2023 was $383.29 billion, 
#    as reported in the company's audited financial statements."
#
#   (NOT: "around $390 billion" with both figures!)
```

---

---

## Task 4: Complete Mode Definitions

The three modes must be clearly distinguished:

### EXPLOIT Mode: "We know the answer"

**Triggers:**
- Operators agree on answer (Δ_A < 0.15) OR
- One operator clearly more reliable (TRUST_A/TRUST_B with reliability > 0.7)
- Trajectory converging or stable
- Query is simple/moderate complexity

**Behavior:**
- Give direct, confident answer
- Don't hedge or present alternatives
- Confidence: 75-95%

**Example queries that SHOULD be EXPLOIT:**
```
"What was Apple's total revenue in FY2023?" → $383.29B
"What is Apple's ticker symbol?" → AAPL
"Who is Apple's CEO?" → Tim Cook
```

### ADAPTIVE Mode: "We have a good answer but with nuance"

**Triggers:**
- Operators partially agree (0.15 < Δ_A < 0.40)
- Both operators have moderate reliability (0.5-0.7)
- Question has inherent complexity
- Multiple valid perspectives exist

**Behavior:**
- Give primary answer with context
- Acknowledge nuance or alternative views
- Confidence: 55-75%

**Example queries that SHOULD be ADAPTIVE:**
```
"How did R&D expenses change from FY2022 to FY2023?" 
  → Primary trend + context about what drove it

"What factors contributed to Services revenue growth?"
  → List factors with relative importance

"What are Apple's main product segments?"
  → Segments + brief context on each
```

### EXPLORE Mode: "This is genuinely uncertain"

**Triggers:**
- Operators strongly disagree (Δ_A > 0.40) AND no clear reliability winner
- Trajectory diverging (getting worse over hops)
- Query is inherently opinion-based or speculative
- Both operators have low reliability (< 0.5)
- Question asks for prediction or judgment

**Behavior:**
- Present multiple perspectives explicitly
- Acknowledge uncertainty
- Don't pick a winner arbitrarily
- Confidence: 35-55%

**Example queries that SHOULD be EXPLORE:**
```
"Is Apple's margin pressure cyclical or structural?"
  → Present arguments for both, acknowledge uncertainty

"Will Apple's services revenue continue to grow?"
  → Discuss factors for/against, no definitive prediction

"Should Apple increase R&D spending?"
  → Present trade-offs, not a recommendation

"How does Apple's strategy compare to Microsoft's?"
  → Multiple dimensions, no single answer
```

---

## Task 5: Implement Clear Mode Boundaries

Update the `_determine_mode_and_confidence` method with explicit rules:

```python
def _determine_mode_and_confidence(
    self,
    commutator,
    trajectory: List,
    query_class: QueryClassification,
    reliability_A: OperatorReliability,
    reliability_B: OperatorReliability,
    trust_decision: TrustDecision,
) -> Tuple[QueryMode, float]:
    """
    Determine mode with clear boundaries for each mode.
    
    EXPLOIT: We know the answer
    ADAPTIVE: Good answer with nuance
    EXPLORE: Genuinely uncertain
    """
    
    delta = commutator.combined
    delta_A = commutator.delta_A
    delta_E = commutator.delta_E
    
    trajectory_trend = self._analyze_trajectory(trajectory)
    
    # =========================================================================
    # EXPLOIT CONDITIONS
    # =========================================================================
    
    exploit_conditions = []
    
    # Condition 1: Strong answer agreement
    if delta_A < 0.15:
        exploit_conditions.append("strong_answer_agreement")
    
    # Condition 2: Clear reliability winner
    if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
        trusted_reliability = (
            reliability_A.reliability_score 
            if trust_decision == TrustDecision.TRUST_A 
            else reliability_B.reliability_score
        )
        if trusted_reliability > 0.70:
            exploit_conditions.append("clear_reliable_source")
    
    # Condition 3: Good overall convergence
    if delta < 0.35 and trajectory_trend in ["converging", "stable"]:
        exploit_conditions.append("good_convergence")
    
    # Condition 4: Simple query with moderate agreement
    if query_class.complexity == "simple" and delta_A < 0.25:
        exploit_conditions.append("simple_query_agreement")
    
    # =========================================================================
    # EXPLORE CONDITIONS (Hard triggers)
    # =========================================================================
    
    explore_conditions = []
    
    # Condition 1: Strong answer disagreement with no clear winner
    if delta_A > 0.40 and trust_decision in [TrustDecision.MERGE_EQUAL, TrustDecision.CONFLICT]:
        explore_conditions.append("answer_disagreement_no_winner")
    
    # Condition 2: Diverging trajectory
    if trajectory_trend == "diverging":
        explore_conditions.append("diverging_trajectory")
    
    # Condition 3: Opinion/speculative query
    if query_class.query_type == QueryType.OPINION:
        explore_conditions.append("opinion_query")
    
    # Condition 4: Both operators unreliable
    if reliability_A.reliability_score < 0.45 and reliability_B.reliability_score < 0.45:
        explore_conditions.append("both_unreliable")
    
    # Condition 5: Very high overall divergence
    if delta > 0.60 and delta_E > 0.80:
        explore_conditions.append("high_divergence")
    
    # =========================================================================
    # MODE DECISION LOGIC
    # =========================================================================
    
    # EXPLORE takes priority if any hard trigger
    if len(explore_conditions) >= 1:
        mode = QueryMode.EXPLORE
        confidence = self._compute_explore_confidence(
            commutator, explore_conditions, reliability_A, reliability_B
        )
        logger.info(f"EXPLORE triggered by: {explore_conditions}")
    
    # EXPLOIT if multiple conditions met
    elif len(exploit_conditions) >= 2:
        mode = QueryMode.EXPLOIT
        confidence = self._compute_exploit_confidence(
            commutator, exploit_conditions, reliability_A, reliability_B, trust_decision
        )
        logger.info(f"EXPLOIT triggered by: {exploit_conditions}")
    
    # Otherwise ADAPTIVE
    else:
        mode = QueryMode.ADAPTIVE
        confidence = self._compute_adaptive_confidence(
            commutator, reliability_A, reliability_B, trajectory_trend
        )
        logger.info(f"ADAPTIVE: exploit_conditions={exploit_conditions}, explore_conditions={explore_conditions}")
    
    return mode, confidence


def _compute_exploit_confidence(
    self,
    commutator,
    conditions: List[str],
    reliability_A: OperatorReliability,
    reliability_B: OperatorReliability,
    trust_decision: TrustDecision,
) -> float:
    """Compute confidence for EXPLOIT mode."""
    
    # Base confidence
    base = 0.75
    
    # Boost for strong answer agreement
    if "strong_answer_agreement" in conditions:
        base += 0.10
    
    # Boost for clear reliable source
    if "clear_reliable_source" in conditions:
        trusted_rel = max(reliability_A.reliability_score, reliability_B.reliability_score)
        base += 0.10 * trusted_rel
    
    # Boost for good convergence
    if "good_convergence" in conditions:
        base += 0.05
    
    # Adjust by answer agreement
    base -= commutator.delta_A * 0.2
    
    return max(0.70, min(0.95, base))


def _compute_adaptive_confidence(
    self,
    commutator,
    reliability_A: OperatorReliability,
    reliability_B: OperatorReliability,
    trajectory_trend: str,
) -> float:
    """Compute confidence for ADAPTIVE mode."""
    
    # Base confidence
    base = 0.60
    
    # Adjust by answer agreement
    if commutator.delta_A < 0.20:
        base += 0.10
    elif commutator.delta_A > 0.35:
        base -= 0.10
    
    # Adjust by average reliability
    avg_rel = (reliability_A.reliability_score + reliability_B.reliability_score) / 2
    base += (avg_rel - 0.5) * 0.15
    
    # Adjust by trajectory
    if trajectory_trend == "converging":
        base += 0.05
    elif trajectory_trend == "oscillating":
        base -= 0.05
    
    return max(0.50, min(0.75, base))


def _compute_explore_confidence(
    self,
    commutator,
    conditions: List[str],
    reliability_A: OperatorReliability,
    reliability_B: OperatorReliability,
) -> float:
    """Compute confidence for EXPLORE mode."""
    
    # Base confidence (lower for EXPLORE)
    base = 0.45
    
    # Further reduce for multiple explore triggers
    base -= 0.05 * (len(conditions) - 1)
    
    # Adjust by how bad the disagreement is
    base -= commutator.delta_A * 0.15
    
    # If both unreliable, reduce further
    if "both_unreliable" in conditions:
        base -= 0.10
    
    return max(0.30, min(0.55, base))
```

---

## Task 6: Update Answer Generation for Each Mode

```python
def _generate_answer_with_trust(
    self,
    query: str,
    belief_A,
    belief_B,
    mode_decision: ModeDecision,
    trajectory: List,
) -> str:
    """Generate answer based on mode and trust decision."""
    
    mode = mode_decision.mode
    trust = mode_decision.trust_decision
    
    # =========================================================================
    # EXPLOIT MODE: Direct, confident answer
    # =========================================================================
    if mode == QueryMode.EXPLOIT:
        if trust == TrustDecision.TRUST_A:
            return self._generate_exploit_answer(
                query, belief_A.evidence, 
                source_type="financial/XBRL data",
                confidence=mode_decision.confidence
            )
        elif trust == TrustDecision.TRUST_B:
            return self._generate_exploit_answer(
                query, belief_B.evidence,
                source_type="narrative analysis",
                confidence=mode_decision.confidence
            )
        else:
            # Both agree - use combined evidence
            combined_evidence = belief_A.evidence + belief_B.evidence
            return self._generate_exploit_answer(
                query, combined_evidence,
                source_type="combined sources",
                confidence=mode_decision.confidence
            )
    
    # =========================================================================
    # ADAPTIVE MODE: Primary answer with nuance
    # =========================================================================
    elif mode == QueryMode.ADAPTIVE:
        return self._generate_adaptive_answer(
            query, belief_A, belief_B,
            mode_decision=mode_decision,
            trajectory=trajectory
        )
    
    # =========================================================================
    # EXPLORE MODE: Multiple perspectives, explicit uncertainty
    # =========================================================================
    else:  # EXPLORE
        return self._generate_explore_answer(
            query, belief_A, belief_B,
            mode_decision=mode_decision,
            trajectory=trajectory
        )


def _generate_exploit_answer(
    self,
    query: str,
    evidence: List,
    source_type: str,
    confidence: float,
) -> str:
    """Generate direct, confident answer for EXPLOIT mode."""
    
    prompt = f"""Answer this question directly and confidently.

Question: {query}

Evidence (from {source_type}):
{self._format_evidence(evidence)}

INSTRUCTIONS:
1. Give a direct, clear answer
2. Do NOT hedge or present alternatives
3. Do NOT say "approximately" or "around" - give the exact figure if available
4. Be concise
5. Confidence: {confidence:.0%}

Answer:"""
    
    return self._call_llm(prompt)


def _generate_adaptive_answer(
    self,
    query: str,
    belief_A,
    belief_B,
    mode_decision: ModeDecision,
    trajectory: List,
) -> str:
    """Generate balanced answer with nuance for ADAPTIVE mode."""
    
    # Determine which to emphasize
    if mode_decision.operator_A_reliability.reliability_score > mode_decision.operator_B_reliability.reliability_score:
        primary_evidence = belief_A.evidence
        secondary_evidence = belief_B.evidence
        primary_source = "financial data"
        secondary_source = "narrative context"
    else:
        primary_evidence = belief_B.evidence
        secondary_evidence = belief_A.evidence
        primary_source = "narrative analysis"
        secondary_source = "financial data"
    
    prompt = f"""Answer this question with appropriate nuance.

Question: {query}

Primary Evidence ({primary_source}):
{self._format_evidence(primary_evidence)}

Additional Context ({secondary_source}):
{self._format_evidence(secondary_evidence[:5])}

INSTRUCTIONS:
1. Provide the main answer based on primary evidence
2. Add relevant context or nuance from additional evidence
3. If there are different figures, explain possible reasons (different periods, methodologies)
4. Be informative but not overly hedged
5. Confidence: {mode_decision.confidence:.0%}

Answer:"""
    
    return self._call_llm(prompt)


def _generate_explore_answer(
    self,
    query: str,
    belief_A,
    belief_B,
    mode_decision: ModeDecision,
    trajectory: List,
) -> str:
    """Generate multi-perspective answer for EXPLORE mode."""
    
    prompt = f"""This question has genuine uncertainty. Present multiple perspectives.

Question: {query}

Perspective A (Quantitative/Financial):
{self._format_evidence(belief_A.evidence)}

Perspective B (Qualitative/Narrative):
{self._format_evidence(belief_B.evidence)}

INSTRUCTIONS:
1. Acknowledge that this question has multiple valid viewpoints
2. Present the key perspectives clearly
3. Do NOT pick a winner arbitrarily
4. Explain what would be needed to resolve the uncertainty
5. Be honest about the limitations of available data
6. Confidence: {mode_decision.confidence:.0%} (lower confidence is appropriate here)

Answer:"""
    
    return self._call_llm(prompt)
```

---

## Task 7: Complete Test Matrix

Test all three modes with appropriate queries:

```python
TEST_QUERIES = {
    # EXPLOIT: Clear answers expected
    "exploit_simple": [
        ("What was Apple's total revenue in FY2023?", "EXPLOIT", ">0.80"),
        ("What is Apple's fiscal year end?", "EXPLOIT", ">0.85"),
        ("How many employees does Apple have?", "EXPLOIT", ">0.75"),
    ],
    
    # ADAPTIVE: Nuanced answers expected
    "adaptive_moderate": [
        ("How did iPhone revenue change from FY2022 to FY2023?", "ADAPTIVE", "0.60-0.75"),
        ("What are the main factors driving Services growth?", "ADAPTIVE", "0.55-0.70"),
        ("What does Apple's R&D spending look like?", "ADAPTIVE", "0.60-0.75"),
    ],
    
    # EXPLORE: Uncertain/multi-perspective expected
    "explore_complex": [
        ("Is Apple's margin pressure cyclical or structural?", "EXPLORE", "0.35-0.55"),
        ("Should Apple increase its dividend?", "EXPLORE", "0.35-0.50"),
        ("Will Apple's services business continue to outpace products?", "EXPLORE", "0.40-0.55"),
        ("How does Apple's innovation compare to its competitors?", "EXPLORE", "0.35-0.50"),
    ],
}

def test_all_modes():
    """Test that each query type gets the correct mode."""
    system = OpMechGraphRAG(config)
    
    results = []
    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*60}")
        print(f"Testing: {category}")
        print('='*60)
        
        for query, expected_mode, expected_confidence in queries:
            result = system.query(query)
            
            mode_correct = result.mode == expected_mode
            
            # Parse confidence range
            if "-" in expected_confidence:
                low, high = map(float, expected_confidence.split("-"))
                conf_correct = low <= result.confidence <= high
            elif expected_confidence.startswith(">"):
                conf_correct = result.confidence > float(expected_confidence[1:])
            else:
                conf_correct = result.confidence == float(expected_confidence)
            
            status = "✓" if mode_correct and conf_correct else "✗"
            
            print(f"{status} {query[:50]}...")
            print(f"   Expected: {expected_mode}, Conf: {expected_confidence}")
            print(f"   Got:      {result.mode}, Conf: {result.confidence:.2f}")
            
            if not mode_correct:
                print(f"   ⚠️  Mode mismatch!")
            
            results.append({
                "query": query,
                "expected_mode": expected_mode,
                "actual_mode": result.mode,
                "mode_correct": mode_correct,
                "conf_correct": conf_correct,
            })
    
    # Summary
    correct = sum(1 for r in results if r["mode_correct"])
    print(f"\n{'='*60}")
    print(f"Mode accuracy: {correct}/{len(results)} ({correct/len(results)*100:.0f}%)")
    
    return results
```

---

## Summary

### The Root Cause Fix

| Before | After |
|--------|-------|
| Commutator measures disagreement only | Commutator + Reliability scoring |
| Equal trust in both operators | Trust based on query-evidence fit |
| Merge conflicting figures | Trust authoritative source |
| $390B (wrong average) | $383.29B (correct XBRL value) |

### Mode Selection Summary

| Mode | When | Confidence | Answer Style |
|------|------|------------|--------------|
| **EXPLOIT** | Agreement OR clear reliable source | 75-95% | Direct, no hedging |
| **ADAPTIVE** | Partial agreement, inherent nuance | 55-75% | Primary + context |
| **EXPLORE** | Disagreement + no clear winner, opinion queries | 35-55% | Multiple perspectives |

### Key Insight

**For numerical/factual queries, XBRL data is authoritative.**

The system now:
1. Classifies the query type
2. Scores operator reliability based on evidence-query fit
3. Determines who to trust when they disagree
4. Selects appropriate mode (EXPLOIT/ADAPTIVE/EXPLORE)
5. Generates answer matching the mode's style

This fixes both problems:
- **Wrong merging**: Trust the authoritative source
- **Wrong mode**: Clear triggers for each mode
