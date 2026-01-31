# OpMech Hybrid Query Classification System

## Problem Statement

The current pattern-matching approach is brittle:
- Priority order (OPINION > CAUSAL > NUMERICAL) is too rigid
- Patterns overlap (e.g., "margin" appears in both numerical and opinion queries)
- Novel queries not covered by patterns fail silently
- Hardcoded complexity overrides don't generalize

## Solution: Hybrid Multi-Signal Classification

A robust system that:
1. **Scores all patterns** (not priority-based)
2. **Applies context rules** to disambiguate
3. **Falls back to LLM** for ambiguous cases
4. **Validates classification** against query structure

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY CLASSIFICATION                          │
├─────────────────────────────────────────────────────────────────┤
│  Stage 1: PATTERN SCORING                                       │
│    - Score query against ALL pattern sets                       │
│    - No priority order - just raw match counts                  │
├─────────────────────────────────────────────────────────────────┤
│  Stage 2: CONTEXT RULES                                         │
│    - Apply linguistic rules to boost/penalize scores            │
│    - Handle common ambiguities                                  │
├─────────────────────────────────────────────────────────────────┤
│  Stage 3: CONFIDENCE CHECK                                      │
│    - If clear winner → use pattern result                       │
│    - If ambiguous → proceed to Stage 4                          │
├─────────────────────────────────────────────────────────────────┤
│  Stage 4: LLM FALLBACK (if needed)                              │
│    - Use LLM to classify ambiguous queries                      │
│    - Cache results for similar queries                          │
├─────────────────────────────────────────────────────────────────┤
│  Stage 5: COMPLEXITY DETERMINATION                              │
│    - Based on query type + linguistic features                  │
│    - Not hardcoded overrides                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task 1: Implement the Hybrid Query Classifier

Create/update `src/opmech/query_classifier.py`:

```python
"""
Hybrid Query Classification System

Uses multi-stage classification:
1. Pattern scoring (all patterns scored, not priority)
2. Context rules (linguistic disambiguation)
3. Confidence check (clear winner vs ambiguous)
4. LLM fallback (for ambiguous cases)
5. Complexity determination (based on multiple signals)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
from loguru import logger


class QueryType(Enum):
    """Query type categories."""
    NUMERICAL = "numerical"      # Asks for specific number/amount
    TEMPORAL = "temporal"        # Asks about changes over time
    CAUSAL = "causal"           # Asks why/what caused
    DESCRIPTIVE = "descriptive"  # Asks to describe/explain
    COMPARATIVE = "comparative"  # Asks to compare things
    OPINION = "opinion"         # Asks for judgment/speculation


@dataclass
class QueryClassification:
    """Complete query classification result."""
    query_type: QueryType
    complexity: str                    # "simple", "moderate", "complex"
    confidence: float                  # 0-1, how confident in classification
    expects_number: bool               # Does query expect numeric answer?
    classification_method: str         # "pattern", "context_rule", "llm_fallback"
    reasoning: str                     # Human-readable explanation
    pattern_scores: Dict[str, float]   # Raw pattern scores for debugging


class HybridQueryClassifier:
    """
    Robust query classifier using multiple signals.
    
    Key design principles:
    1. No hardcoded priority order - use weighted scoring
    2. Context rules handle common ambiguities
    3. LLM fallback for truly ambiguous cases
    4. Complexity is derived, not hardcoded per type
    """
    
    # =========================================================================
    # PATTERN DEFINITIONS
    # =========================================================================
    
    # NUMERICAL: Asking for specific numbers
    # Note: Made more specific to avoid false matches
    NUMERICAL_PATTERNS = [
        # Direct "what was X" questions asking for amounts
        r"^what (was|is|were|are) .*(total |annual )?(revenue|income|sales|earnings|eps)\b",
        r"^what (was|is|were|are) the (total |annual )?(revenue|income|sales|earnings)\b",
        r"^how much .*(revenue|income|sales|profit|expense|cost)\b",
        r"^how much did .* (make|earn|spend|cost)\b",
        r"^what is the (value|amount|total|sum|number)\b",
        r"^how many (shares|employees|stores|units|customers)\b",
        # Specific metrics
        r"\b(eps|p/e ratio|roe|roa|roi)\b.*\?",
        # Questions ending with fiscal year (strong signal)
        r"(revenue|income|expense|sales|earnings|profit).*(in |for )(fy|fiscal year)?\s*\d{4}\s*\??$",
    ]
    
    # OPINION: Asking for judgment/speculation
    OPINION_PATTERNS = [
        # Is/Are + judgment adjective
        r"^(is|are|does|do) .*(sustainable|viable|risky|safe|healthy|strong|weak)\b",
        r"^(is|are) .*(cyclical|structural|temporary|permanent|improving|worsening)\b",
        r"^(is|are) .* pressure .*(cyclical|structural)\b",
        # Should/Would/Will (speculation)
        r"^(should|would|will|could|might) .*(invest|buy|sell|increase|decrease|grow|decline)\b",
        # Binary judgment questions
        r"cyclical or structural",
        r"structural or cyclical",
        r"sustainable or unsustainable",
        r"temporary or permanent",
        # Outlook/prediction
        r"\b(outlook|forecast|prediction|expectation|prognosis)\b",
        # Evaluation requests
        r"^(rate|evaluate|assess|judge) ",
        r"(good|bad|better|worse|concerning|worrying|promising)\s*\??$",
        # "Do you think" style
        r"do you (think|believe|expect)\b",
    ]
    
    # CAUSAL: Asking why/what caused
    CAUSAL_PATTERNS = [
        # Direct why questions
        r"^why (did|does|is|are|was|were)\b",
        # What caused/drove/led to
        r"what (caused|drove|led to|contributed to|resulted in)\b",
        r"what (factors?|reasons?|drivers?) (caused|drove|led|contributed|explain)\b",
        r"(factors?|reasons?|drivers?) (for|behind|of|driving|causing)\b",
        # Explain why
        r"explain (why|how|what caused)\b",
        # Due to / because of (asking for cause)
        r"(due to|because of|as a result of) what\b",
        # What's behind
        r"what('s| is| was) behind\b",
    ]
    
    # TEMPORAL: Asking about changes over time
    TEMPORAL_PATTERNS = [
        # How did X change
        r"how (did|has|have) .*(change|grow|decline|increase|decrease|evolve|trend)\b",
        r"(change|growth|decline|trend|evolution) (from|between|over|since)\b",
        # Year over year
        r"(year.over.year|yoy|quarter.over.quarter|qoq|month.over.month)\b",
        # Compared to previous period
        r"compared to (last|previous|prior|earlier)\b",
        r"(from|between) (fy|fiscal year)?\s*\d{4} (to|and|through) (fy|fiscal year)?\s*\d{4}",
        # Over time expressions
        r"over the (past|last|previous) \d+ (years?|quarters?|months?)\b",
        r"(historical|history|over time|time series)\b",
    ]
    
    # DESCRIPTIVE: Asking to describe/explain (not why)
    DESCRIPTIVE_PATTERNS = [
        # What is/are (not followed by number words)
        r"^what (is|are) .*(strategy|approach|policy|plan|model|structure)\b",
        r"^what (is|are) the .*(strategy|approach|policy|plan|business)\b",
        # Describe/explain
        r"^(describe|explain|outline|summarize|overview)\b",
        # List/name
        r"^(list|name|identify|enumerate) .*(factors?|risks?|products?|segments?)\b",
        # Risk factors, products, segments
        r"(risk factors?|main products?|business segments?|revenue (streams?|sources?))\b",
        # How does X work
        r"how does .* (work|operate|function)\b",
    ]
    
    # COMPARATIVE: Asking to compare
    COMPARATIVE_PATTERNS = [
        # Compare/comparison
        r"\b(compare|comparison|versus|vs\.?)\b",
        r"(difference|differences|similarity|similarities) between\b",
        # Better/worse than
        r"(better|worse|higher|lower|more|less|stronger|weaker) than\b",
        # Relative to
        r"(relative to|compared to|against|benchmarked)\b",
        # Industry/competitor comparison
        r"(industry average|competitors?|peers?|benchmark)\b",
    ]
    
    # =========================================================================
    # CONTEXT RULES
    # =========================================================================
    
    # Rules that boost/penalize scores based on query structure
    CONTEXT_RULES = [
        {
            "name": "is_are_judgment",
            "description": "Questions starting with Is/Are + judgment word → OPINION",
            "pattern": r"^(is|are|does|do|will|would|should|could)\b",
            "judgment_words": ["sustainable", "cyclical", "structural", "risky", 
                             "safe", "good", "bad", "healthy", "concerning",
                             "temporary", "permanent", "improving", "worsening"],
            "boost": {QueryType.OPINION: 5},
            "penalize": {QueryType.NUMERICAL: 3},
        },
        {
            "name": "what_was_amount",
            "description": "What was/is + financial term at end → NUMERICAL",
            "pattern": r"^what (was|is|were|are)\b",
            "end_words": ["revenue", "income", "sales", "expense", "profit", 
                         "margin", "earnings", "eps", "cost"],
            "check_ending": True,
            "boost": {QueryType.NUMERICAL: 4},
            "penalize": {QueryType.OPINION: 2},
        },
        {
            "name": "why_what_caused",
            "description": "Why/What caused/drove → CAUSAL",
            "pattern": r"(^why\b|what (caused|drove|factors))",
            "boost": {QueryType.CAUSAL: 5},
            "penalize": {QueryType.NUMERICAL: 3, QueryType.OPINION: 2},
        },
        {
            "name": "or_judgment",
            "description": "X or Y where both are judgment terms → OPINION",
            "pattern": r"\b(\w+)\s+or\s+(\w+)\b",
            "judgment_pairs": [
                ("cyclical", "structural"), ("structural", "cyclical"),
                ("temporary", "permanent"), ("permanent", "temporary"),
                ("sustainable", "unsustainable"), ("improving", "worsening"),
            ],
            "boost": {QueryType.OPINION: 6},
            "penalize": {QueryType.NUMERICAL: 4},
        },
        {
            "name": "fiscal_year_ending",
            "description": "Ends with fiscal year reference → likely NUMERICAL",
            "pattern": r"(in |for )(fy|fiscal year)?\s*\d{4}\s*\??$",
            "boost": {QueryType.NUMERICAL: 3, QueryType.TEMPORAL: 2},
            "penalize": {},
        },
        {
            "name": "how_did_change",
            "description": "How did X change → TEMPORAL",
            "pattern": r"^how (did|has|have)\b.*\b(change|grow|decline|increase|decrease)",
            "boost": {QueryType.TEMPORAL: 4},
            "penalize": {QueryType.NUMERICAL: 2},
        },
        {
            "name": "factors_drove",
            "description": "What factors drove/caused → CAUSAL not NUMERICAL",
            "pattern": r"(what |which )(factors?|reasons?|drivers?)\b",
            "boost": {QueryType.CAUSAL: 5},
            "penalize": {QueryType.NUMERICAL: 4},
        },
    ]
    
    # =========================================================================
    # CLASSIFICATION METHODS
    # =========================================================================
    
    def __init__(self, llm_interface=None, enable_llm_fallback: bool = True):
        """
        Initialize classifier.
        
        Args:
            llm_interface: Optional LLM interface for fallback classification
            enable_llm_fallback: Whether to use LLM for ambiguous cases
        """
        self.llm = llm_interface
        self.enable_llm_fallback = enable_llm_fallback and llm_interface is not None
        self._classification_cache = {}  # Cache LLM classifications
    
    def classify(self, query: str) -> QueryClassification:
        """
        Classify a query using hybrid multi-stage approach.
        
        Stages:
        1. Pattern scoring
        2. Context rule application
        3. Confidence check
        4. LLM fallback (if needed)
        5. Complexity determination
        """
        query_lower = query.lower().strip()
        
        # Stage 1: Pattern scoring
        pattern_scores = self._compute_pattern_scores(query_lower)
        logger.debug(f"Pattern scores: {pattern_scores}")
        
        # Stage 2: Apply context rules
        adjusted_scores, rules_applied = self._apply_context_rules(query_lower, pattern_scores.copy())
        logger.debug(f"Adjusted scores: {adjusted_scores}, rules: {rules_applied}")
        
        # Stage 3: Confidence check
        query_type, confidence, method = self._determine_type_with_confidence(
            query_lower, adjusted_scores, rules_applied
        )
        
        # Stage 4: LLM fallback if needed
        if confidence < 0.6 and self.enable_llm_fallback:
            llm_result = self._classify_with_llm(query)
            if llm_result:
                query_type = llm_result["type"]
                confidence = llm_result["confidence"]
                method = "llm_fallback"
                logger.info(f"LLM fallback used: {query_type.value}")
        
        # Stage 5: Complexity determination
        complexity = self._determine_complexity(query_lower, query_type, adjusted_scores)
        
        # Determine if numeric answer expected
        expects_number = self._expects_numeric_answer(query_lower, query_type)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            query_type, complexity, method, rules_applied, adjusted_scores
        )
        
        return QueryClassification(
            query_type=query_type,
            complexity=complexity,
            confidence=confidence,
            expects_number=expects_number,
            classification_method=method,
            reasoning=reasoning,
            pattern_scores={k.value: v for k, v in adjusted_scores.items()}
        )
    
    def _compute_pattern_scores(self, query: str) -> Dict[QueryType, float]:
        """Compute raw pattern match scores for all query types."""
        
        scores = {}
        
        pattern_sets = {
            QueryType.NUMERICAL: self.NUMERICAL_PATTERNS,
            QueryType.OPINION: self.OPINION_PATTERNS,
            QueryType.CAUSAL: self.CAUSAL_PATTERNS,
            QueryType.TEMPORAL: self.TEMPORAL_PATTERNS,
            QueryType.DESCRIPTIVE: self.DESCRIPTIVE_PATTERNS,
            QueryType.COMPARATIVE: self.COMPARATIVE_PATTERNS,
        }
        
        for query_type, patterns in pattern_sets.items():
            score = 0
            for pattern in patterns:
                try:
                    if re.search(pattern, query, re.IGNORECASE):
                        score += 1
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pattern}")
            scores[query_type] = score
        
        return scores
    
    def _apply_context_rules(
        self, 
        query: str, 
        scores: Dict[QueryType, float]
    ) -> Tuple[Dict[QueryType, float], List[str]]:
        """Apply context rules to adjust scores."""
        
        rules_applied = []
        
        for rule in self.CONTEXT_RULES:
            try:
                # Check if main pattern matches
                if not re.search(rule["pattern"], query, re.IGNORECASE):
                    continue
                
                # Additional checks based on rule type
                should_apply = True
                
                # Check for judgment words
                if "judgment_words" in rule:
                    should_apply = any(word in query for word in rule["judgment_words"])
                
                # Check for ending words
                if rule.get("check_ending"):
                    words = query.rstrip("?").split()
                    if words:
                        last_word = words[-1].lower()
                        should_apply = any(
                            last_word == end_word or last_word.endswith(end_word)
                            for end_word in rule.get("end_words", [])
                        )
                
                # Check for judgment pairs (for "or" rule)
                if "judgment_pairs" in rule:
                    match = re.search(rule["pattern"], query, re.IGNORECASE)
                    if match:
                        word1, word2 = match.groups()
                        should_apply = any(
                            (word1.lower() in pair[0] and word2.lower() in pair[1]) or
                            (word1.lower() in pair[1] and word2.lower() in pair[0])
                            for pair in rule["judgment_pairs"]
                        )
                    else:
                        should_apply = False
                
                # Apply boosts and penalties
                if should_apply:
                    rules_applied.append(rule["name"])
                    
                    for query_type, boost in rule.get("boost", {}).items():
                        scores[query_type] = scores.get(query_type, 0) + boost
                    
                    for query_type, penalty in rule.get("penalize", {}).items():
                        scores[query_type] = max(0, scores.get(query_type, 0) - penalty)
                        
            except Exception as e:
                logger.warning(f"Error applying rule {rule['name']}: {e}")
        
        return scores, rules_applied
    
    def _determine_type_with_confidence(
        self,
        query: str,
        scores: Dict[QueryType, float],
        rules_applied: List[str]
    ) -> Tuple[QueryType, float, str]:
        """
        Determine query type and confidence level.
        
        Returns:
            (query_type, confidence, classification_method)
        """
        
        # Sort scores
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Handle no matches
        if all(score == 0 for _, score in sorted_scores):
            # Default to DESCRIPTIVE with low confidence
            return QueryType.DESCRIPTIVE, 0.3, "default"
        
        top_type, top_score = sorted_scores[0]
        second_type, second_score = sorted_scores[1] if len(sorted_scores) > 1 else (None, 0)
        
        # Calculate confidence based on score margin
        if second_score == 0:
            # Only one type matched
            confidence = min(0.95, 0.7 + top_score * 0.05)
            method = "pattern_clear"
        elif top_score >= second_score * 2:
            # Clear winner (2x margin)
            confidence = min(0.95, 0.75 + (top_score - second_score) * 0.03)
            method = "pattern_dominant"
        elif top_score > second_score:
            # Marginal winner
            margin_ratio = (top_score - second_score) / top_score
            confidence = 0.5 + margin_ratio * 0.3
            method = "pattern_marginal"
        else:
            # Tie or very close
            confidence = 0.4
            method = "pattern_ambiguous"
        
        # Boost confidence if context rules applied
        if rules_applied:
            confidence = min(0.95, confidence + 0.1 * len(rules_applied))
            if "pattern" in method:
                method = "context_rule"
        
        return top_type, confidence, method
    
    def _classify_with_llm(self, query: str) -> Optional[Dict]:
        """
        Use LLM to classify ambiguous queries.
        
        Returns dict with 'type' and 'confidence' or None if failed.
        """
        
        # Check cache
        cache_key = query.lower().strip()
        if cache_key in self._classification_cache:
            return self._classification_cache[cache_key]
        
        if not self.llm:
            return None
        
        prompt = f"""Classify this query into exactly ONE category.

Query: "{query}"

Categories:
- NUMERICAL: Asks for a specific number, dollar amount, or percentage (e.g., "What was revenue?")
- CAUSAL: Asks WHY something happened or what FACTORS caused it (e.g., "Why did margin decline?")
- OPINION: Asks for JUDGMENT, evaluation, or speculation (e.g., "Is growth sustainable?")
- TEMPORAL: Asks about CHANGES over time or TRENDS (e.g., "How did revenue change?")
- COMPARATIVE: Asks to COMPARE two or more things (e.g., "How does X compare to Y?")
- DESCRIPTIVE: Asks to DESCRIBE or EXPLAIN something (e.g., "What is Apple's strategy?")

Key distinctions:
- "What was revenue?" → NUMERICAL (asking for a number)
- "Why did revenue decline?" → CAUSAL (asking for reasons)
- "Is the decline temporary?" → OPINION (asking for judgment)
- "How did revenue change over time?" → TEMPORAL (asking about trend)
- "What factors drove revenue?" → CAUSAL (asking for causes, not a number)

Respond with ONLY a JSON object:
{{"type": "NUMERICAL|CAUSAL|OPINION|TEMPORAL|COMPARATIVE|DESCRIPTIVE", "confidence": 0.0-1.0}}

JSON:"""
        
        try:
            response = self.llm.generate(prompt, max_tokens=50, temperature=0)
            
            # Parse response
            import json
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                query_type = QueryType(result["type"].lower())
                confidence = float(result.get("confidence", 0.7))
                
                # Cache result
                self._classification_cache[cache_key] = {
                    "type": query_type,
                    "confidence": confidence
                }
                
                return self._classification_cache[cache_key]
                
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
        
        return None
    
    def _determine_complexity(
        self,
        query: str,
        query_type: QueryType,
        scores: Dict[QueryType, float]
    ) -> str:
        """
        Determine query complexity based on multiple signals.
        
        NOT hardcoded by query type - uses actual query features.
        """
        
        complexity_score = 0  # Higher = more complex
        
        # ----- Query type baseline -----
        type_complexity = {
            QueryType.NUMERICAL: 0,      # Often simple lookups
            QueryType.DESCRIPTIVE: 1,    # Requires explanation
            QueryType.TEMPORAL: 2,       # Requires analysis
            QueryType.COMPARATIVE: 2,    # Requires multiple items
            QueryType.CAUSAL: 3,         # Requires reasoning
            QueryType.OPINION: 3,        # Requires judgment
        }
        complexity_score += type_complexity.get(query_type, 1)
        
        # ----- Linguistic features -----
        
        # Query length
        word_count = len(query.split())
        if word_count > 15:
            complexity_score += 2
        elif word_count > 10:
            complexity_score += 1
        elif word_count < 6:
            complexity_score -= 1
        
        # Multiple clauses (contains "and", "or", "but", commas)
        if query.count(",") > 1:
            complexity_score += 1
        if " and " in query and " or " in query:
            complexity_score += 1
        
        # Question complexity indicators
        complex_words = ["analyze", "evaluate", "assess", "explain why", 
                        "compare", "contrast", "implications", "impact"]
        if any(word in query.lower() for word in complex_words):
            complexity_score += 2
        
        # Simple question indicators
        simple_patterns = [
            r"^what (is|was|are|were) the\b",
            r"^how (much|many)\b",
            r"^who (is|was)\b",
        ]
        if any(re.search(p, query.lower()) for p in simple_patterns):
            complexity_score -= 1
        
        # Time period specificity (specific = simpler)
        if re.search(r"(in |for )(fy|fiscal year)?\s*\d{4}", query.lower()):
            complexity_score -= 1
        
        # Multiple entities/concepts
        financial_terms = ["revenue", "income", "expense", "margin", "profit", 
                         "growth", "decline", "cost", "sales"]
        term_count = sum(1 for term in financial_terms if term in query.lower())
        if term_count > 2:
            complexity_score += 1
        
        # ----- Determine complexity level -----
        if complexity_score <= 1:
            return "simple"
        elif complexity_score <= 4:
            return "moderate"
        else:
            return "complex"
    
    def _expects_numeric_answer(self, query: str, query_type: QueryType) -> bool:
        """Determine if query expects a numeric answer."""
        
        # NUMERICAL type usually expects numbers
        if query_type == QueryType.NUMERICAL:
            return True
        
        # Explicit number requests
        number_patterns = [
            r"how (much|many)",
            r"what (is|was|are|were) the (total|amount|value|number)",
            r"(percentage|percent|%|ratio|rate)",
            r"\$|dollars?|billion|million",
        ]
        
        return any(re.search(p, query.lower()) for p in number_patterns)
    
    def _generate_reasoning(
        self,
        query_type: QueryType,
        complexity: str,
        method: str,
        rules_applied: List[str],
        scores: Dict[QueryType, float]
    ) -> str:
        """Generate human-readable reasoning for classification."""
        
        parts = [
            f"Type: {query_type.value}",
            f"Complexity: {complexity}",
            f"Method: {method}",
        ]
        
        if rules_applied:
            parts.append(f"Rules: {', '.join(rules_applied)}")
        
        # Top 3 scores
        top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        score_str = ", ".join(f"{t.value}={s:.1f}" for t, s in top_scores if s > 0)
        if score_str:
            parts.append(f"Scores: {score_str}")
        
        return "; ".join(parts)


# =============================================================================
# INTEGRATION WITH MODE SELECTOR
# =============================================================================

def update_mode_selector_integration():
    """
    Instructions for integrating HybridQueryClassifier with ModeSelector.
    """
    
    integration_code = '''
# In mode_selection.py, update ModeSelector.__init__:

class ModeSelector:
    def __init__(self, llm_interface=None):
        self.query_classifier = HybridQueryClassifier(
            llm_interface=llm_interface,
            enable_llm_fallback=True
        )
        self.reliability_scorer = OperatorReliabilityScorer()

# Update determine_mode to use new classifier:

def determine_mode(self, ...):
    # Step 1: Classify query with hybrid system
    query_class = self.query_classifier.classify(query)
    
    logger.info(f"Query classification: {query_class.reasoning}")
    
    # Step 2: Check for EXPLORE triggers based on classification
    explore_triggers = []
    
    # Opinion queries with low reliability → EXPLORE
    if query_class.query_type == QueryType.OPINION:
        if query_class.complexity == "complex":
            explore_triggers.append("opinion_complex_query")
    
    # Step 3: Check for EXPLOIT triggers
    exploit_triggers = []
    
    # Simple numerical query with high answer agreement
    if query_class.query_type == QueryType.NUMERICAL:
        if query_class.complexity == "simple" and commutator.delta_A < 0.15:
            exploit_triggers.append("simple_numerical_agreement")
    
    # ... rest of mode determination logic
'''
    
    return integration_code
```

---

## Task 2: Update Mode Selection Logic

Update `src/opmech/mode_selection.py` to use the hybrid classifier:

```python
# Replace QueryClassifier with HybridQueryClassifier

from .query_classifier import HybridQueryClassifier, QueryClassification, QueryType

class ModeSelector:
    """
    Updated mode selector using hybrid query classification.
    """
    
    def __init__(self, llm_interface=None):
        self.query_classifier = HybridQueryClassifier(
            llm_interface=llm_interface,
            enable_llm_fallback=True
        )
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
        Determine mode with hybrid query classification.
        """
        
        # Step 1: Classify query
        query_class = self.query_classifier.classify(query)
        logger.info(f"Query classification: {query_class.reasoning}")
        
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
        
        # Step 3: Compute reliability gap
        reliability_gap = abs(reliability_A.reliability_score - reliability_B.reliability_score)
        
        # Step 4: Determine trust decision
        trust_decision = self._determine_trust(
            commutator, reliability_A, reliability_B, reliability_gap, query_class
        )
        
        # Step 5: Determine mode with NEW logic based on query classification
        mode, confidence = self._determine_mode_and_confidence_v2(
            commutator, trajectory, query_class,
            reliability_A, reliability_B, trust_decision
        )
        
        # ... rest of method
    
    def _determine_mode_and_confidence_v2(
        self,
        commutator,
        trajectory: List,
        query_class: QueryClassification,
        reliability_A,
        reliability_B,
        trust_decision,
    ) -> Tuple[QueryMode, float]:
        """
        Improved mode determination using hybrid classification.
        """
        
        delta = commutator.combined
        delta_A = commutator.delta_A
        delta_E = commutator.delta_E
        
        trajectory_trend = self._analyze_trajectory(trajectory)
        
        # =====================================================================
        # EXPLORE TRIGGERS (checked first)
        # =====================================================================
        
        explore_triggers = []
        
        # Trigger 1: Opinion query that's complex
        if query_class.query_type == QueryType.OPINION and query_class.complexity == "complex":
            explore_triggers.append("opinion_complex")
        
        # Trigger 2: High answer disagreement with no clear reliability winner
        if delta_A > 0.40 and trust_decision in [TrustDecision.MERGE_EQUAL, TrustDecision.CONFLICT]:
            explore_triggers.append("answer_disagreement_no_winner")
        
        # Trigger 3: Diverging trajectory
        if trajectory_trend == "diverging":
            explore_triggers.append("diverging_trajectory")
        
        # Trigger 4: Low confidence classification + high divergence
        if query_class.confidence < 0.5 and delta > 0.50:
            explore_triggers.append("uncertain_classification_high_divergence")
        
        # Trigger 5: Both operators unreliable
        if reliability_A.reliability_score < 0.45 and reliability_B.reliability_score < 0.45:
            explore_triggers.append("both_unreliable")
        
        # =====================================================================
        # EXPLOIT TRIGGERS (checked if no EXPLORE triggers)
        # =====================================================================
        
        exploit_triggers = []
        
        if not explore_triggers:
            # Trigger 1: Simple numerical query with answer agreement
            if (query_class.query_type == QueryType.NUMERICAL and 
                query_class.complexity == "simple" and 
                delta_A < 0.15):
                exploit_triggers.append("simple_numerical_agreement")
            
            # Trigger 2: Clear reliability winner
            if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
                trusted_rel = max(reliability_A.reliability_score, reliability_B.reliability_score)
                if trusted_rel > 0.70:
                    exploit_triggers.append("clear_reliable_source")
            
            # Trigger 3: Strong answer agreement (any query type)
            if delta_A < 0.10:
                exploit_triggers.append("very_strong_answer_agreement")
            
            # Trigger 4: Good convergence on factual query
            if (query_class.query_type in [QueryType.NUMERICAL, QueryType.DESCRIPTIVE] and
                delta < 0.35 and trajectory_trend in ["converging", "stable"]):
                exploit_triggers.append("factual_convergence")
        
        # =====================================================================
        # MODE DECISION
        # =====================================================================
        
        if explore_triggers:
            mode = QueryMode.EXPLORE
            # Lower confidence for EXPLORE
            base_confidence = 0.45 - 0.05 * (len(explore_triggers) - 1)
            base_confidence -= delta_A * 0.15
            confidence = max(0.30, min(0.55, base_confidence))
            logger.info(f"EXPLORE triggered by: {explore_triggers}")
        
        elif len(exploit_triggers) >= 2:
            mode = QueryMode.EXPLOIT
            # Higher confidence for EXPLOIT
            base_confidence = 0.75 + 0.05 * (len(exploit_triggers) - 2)
            base_confidence += (1 - delta_A) * 0.10
            if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
                base_confidence += 0.05
            confidence = max(0.70, min(0.95, base_confidence))
            logger.info(f"EXPLOIT triggered by: {exploit_triggers}")
        
        else:
            mode = QueryMode.ADAPTIVE
            # Moderate confidence for ADAPTIVE
            base_confidence = 0.60
            base_confidence += (1 - delta_A) * 0.10
            base_confidence += (1 - delta) * 0.05
            if trajectory_trend == "converging":
                base_confidence += 0.05
            confidence = max(0.50, min(0.75, base_confidence))
            logger.info(f"ADAPTIVE: exploit_triggers={exploit_triggers}, explore_triggers={explore_triggers}")
        
        return mode, confidence
```

---

## Task 3: Comprehensive Test Suite

Create `tests/test_hybrid_classifier.py`:

```python
"""
Test suite for HybridQueryClassifier

Tests:
1. Pattern matching accuracy
2. Context rule application
3. Ambiguous query handling
4. LLM fallback
5. Complexity determination
6. Integration with mode selection
"""

import pytest
from src.opmech.query_classifier import HybridQueryClassifier, QueryType, QueryClassification


class TestPatternMatching:
    """Test basic pattern matching."""
    
    @pytest.fixture
    def classifier(self):
        return HybridQueryClassifier(llm_interface=None, enable_llm_fallback=False)
    
    # ----- NUMERICAL queries -----
    
    @pytest.mark.parametrize("query", [
        "What was Apple's total revenue in FY2023?",
        "What is the annual revenue?",
        "How much did Apple make in 2023?",
        "What was the EPS for fiscal year 2023?",
        "How many employees does Apple have?",
    ])
    def test_numerical_queries(self, classifier, query):
        result = classifier.classify(query)
        assert result.query_type == QueryType.NUMERICAL, f"Expected NUMERICAL for: {query}"
        assert result.expects_number == True
    
    # ----- OPINION queries -----
    
    @pytest.mark.parametrize("query", [
        "Is Apple's gross margin pressure cyclical or structural?",
        "Is the revenue decline sustainable?",
        "Should Apple increase R&D spending?",
        "Will iPhone sales continue to grow?",
        "Is Apple's growth sustainable?",
        "Are the margins improving or worsening?",
    ])
    def test_opinion_queries(self, classifier, query):
        result = classifier.classify(query)
        assert result.query_type == QueryType.OPINION, f"Expected OPINION for: {query}"
    
    # ----- CAUSAL queries -----
    
    @pytest.mark.parametrize("query", [
        "What factors drove iPhone revenue changes in FY2023?",
        "Why did Apple's margin decline?",
        "What caused the revenue drop?",
        "What led to the increase in services revenue?",
        "What are the reasons for the profit decline?",
        "What's behind the margin compression?",
    ])
    def test_causal_queries(self, classifier, query):
        result = classifier.classify(query)
        assert result.query_type == QueryType.CAUSAL, f"Expected CAUSAL for: {query}"
    
    # ----- TEMPORAL queries -----
    
    @pytest.mark.parametrize("query", [
        "How did revenue change from FY2022 to FY2023?",
        "What's the year-over-year growth rate?",
        "How has margin trended over the past 3 years?",
        "Show the revenue trend since 2020",
    ])
    def test_temporal_queries(self, classifier, query):
        result = classifier.classify(query)
        assert result.query_type == QueryType.TEMPORAL, f"Expected TEMPORAL for: {query}"
    
    # ----- COMPARATIVE queries -----
    
    @pytest.mark.parametrize("query", [
        "How does Apple's margin compare to Microsoft?",
        "Compare iPhone and Services revenue",
        "What's the difference between gross and net margin?",
    ])
    def test_comparative_queries(self, classifier, query):
        result = classifier.classify(query)
        assert result.query_type == QueryType.COMPARATIVE, f"Expected COMPARATIVE for: {query}"


class TestContextRules:
    """Test context rule application for ambiguous cases."""
    
    @pytest.fixture
    def classifier(self):
        return HybridQueryClassifier(llm_interface=None, enable_llm_fallback=False)
    
    def test_margin_numerical_vs_opinion(self, classifier):
        """'Margin' appears in both NUMERICAL and OPINION patterns."""
        
        # Should be NUMERICAL - asking for a value
        result1 = classifier.classify("What was Apple's gross margin in FY2023?")
        assert result1.query_type == QueryType.NUMERICAL
        
        # Should be OPINION - asking for judgment
        result2 = classifier.classify("Is Apple's gross margin sustainable?")
        assert result2.query_type == QueryType.OPINION
    
    def test_revenue_numerical_vs_causal(self, classifier):
        """'Revenue' appears in both NUMERICAL and CAUSAL contexts."""
        
        # Should be NUMERICAL
        result1 = classifier.classify("What was the total revenue?")
        assert result1.query_type == QueryType.NUMERICAL
        
        # Should be CAUSAL
        result2 = classifier.classify("What factors drove revenue growth?")
        assert result2.query_type == QueryType.CAUSAL
    
    def test_growth_numerical_vs_opinion(self, classifier):
        """'Growth' can be numerical or opinion."""
        
        # Should be NUMERICAL
        result1 = classifier.classify("What was the revenue growth rate?")
        assert result1.query_type in [QueryType.NUMERICAL, QueryType.TEMPORAL]
        
        # Should be OPINION
        result2 = classifier.classify("Is the growth sustainable?")
        assert result2.query_type == QueryType.OPINION


class TestComplexity:
    """Test complexity determination."""
    
    @pytest.fixture
    def classifier(self):
        return HybridQueryClassifier(llm_interface=None, enable_llm_fallback=False)
    
    def test_simple_queries(self, classifier):
        simple_queries = [
            "What was Apple's revenue?",
            "How many employees?",
            "What is the ticker symbol?",
        ]
        for query in simple_queries:
            result = classifier.classify(query)
            assert result.complexity == "simple", f"Expected simple for: {query}"
    
    def test_complex_queries(self, classifier):
        complex_queries = [
            "Is Apple's margin pressure cyclical or structural given the current macroeconomic environment?",
            "Analyze the factors that contributed to the decline in iPhone revenue and evaluate their long-term implications",
        ]
        for query in complex_queries:
            result = classifier.classify(query)
            assert result.complexity == "complex", f"Expected complex for: {query}"
    
    def test_opinion_never_simple(self, classifier):
        """Opinion queries should never be 'simple'."""
        result = classifier.classify("Is the growth sustainable?")
        assert result.query_type == QueryType.OPINION
        assert result.complexity in ["moderate", "complex"]


class TestConfidence:
    """Test classification confidence."""
    
    @pytest.fixture
    def classifier(self):
        return HybridQueryClassifier(llm_interface=None, enable_llm_fallback=False)
    
    def test_clear_query_high_confidence(self, classifier):
        # Very clear numerical query
        result = classifier.classify("What was Apple's total revenue in FY2023?")
        assert result.confidence > 0.7
    
    def test_ambiguous_query_lower_confidence(self, classifier):
        # Ambiguous query
        result = classifier.classify("What about Apple's margin?")
        assert result.confidence < 0.8


class TestModeIntegration:
    """Test that classification leads to correct mode."""
    
    # These are integration tests - would need full system
    
    def test_numerical_simple_should_allow_exploit(self):
        """Numerical + simple + agreement → EXPLOIT possible"""
        pass  # Integration test
    
    def test_opinion_complex_should_trigger_explore(self):
        """Opinion + complex → EXPLORE likely"""
        pass  # Integration test
    
    def test_causal_should_allow_adaptive(self):
        """Causal + moderate → ADAPTIVE likely"""
        pass  # Integration test
```

---

## Task 4: Run Verification

After implementing, run the same three test queries:

```python
TEST_QUERIES = [
    {
        "query": "What was Apple's total revenue in FY2023?",
        "expected_type": "NUMERICAL",
        "expected_complexity": "simple",
        "expected_mode": "EXPLOIT",
    },
    {
        "query": "Is Apple's gross margin pressure cyclical or structural?",
        "expected_type": "OPINION",
        "expected_complexity": "complex",
        "expected_mode": "EXPLORE",
    },
    {
        "query": "What factors drove iPhone revenue changes in FY2023?",
        "expected_type": "CAUSAL",
        "expected_complexity": "moderate",
        "expected_mode": "ADAPTIVE",
    },
]
```

Expected output:

```
TEST 1: Revenue Query
  Classification: NUMERICAL (simple), confidence=0.85
  Mode: EXPLOIT ✓
  Confidence: 88%

TEST 2: Margin Pressure Query
  Classification: OPINION (complex), confidence=0.90
  Mode: EXPLORE ✓
  Confidence: 45%

TEST 3: iPhone Factors Query
  Classification: CAUSAL (moderate), confidence=0.85
  Mode: ADAPTIVE ✓
  Confidence: 65%
```

---

## Task 5: Fix Revenue Trust Decision (CRITICAL)

The mode selection is working, but the revenue answer is still wrong:

```
Current:  $394.33B (WRONG - from narrative text)
Expected: $383.29B (CORRECT - from XBRL data)
```

**Root Cause**: Trust decision is "Merging equally" instead of "TRUST_A" for numerical queries.

### The Problem

```python
Evidence A types: {'FINANCIAL_LINE': 8, 'NOTE': 3, 'TEXT_SECTION': 2}
Evidence B types: {'NOTE': 7, 'TEXT_SECTION': 1, 'FINANCIAL_LINE': 5}

# Both have FINANCIAL_LINE, so reliability gap isn't large enough
# But Operator A has MORE FINANCIAL_LINE (8 vs 5)
# For numerical queries, this should matter!
```

### The Fix: Enhanced Trust Decision for Numerical Queries

Update `_determine_trust` in `mode_selection.py`:

```python
def _determine_trust(
    self,
    commutator,
    reliability_A: OperatorReliability,
    reliability_B: OperatorReliability,
    reliability_gap: float,
    query_class: QueryClassification,
) -> TrustDecision:
    """
    Determine which operator to trust.
    
    CRITICAL: For numerical queries expecting specific figures,
    we MUST trust the operator with more XBRL/financial evidence.
    """
    
    delta_A = commutator.delta_A  # Answer agreement
    
    # =========================================================================
    # SPECIAL CASE: Numerical queries with answer discrepancy
    # =========================================================================
    
    if query_class.expects_number and query_class.query_type == QueryType.NUMERICAL:
        # Get FINANCIAL_LINE counts
        financial_A = reliability_A.evidence_breakdown.get("FINANCIAL_LINE", 0)
        financial_B = reliability_B.evidence_breakdown.get("FINANCIAL_LINE", 0)
        
        # Calculate financial evidence ratio
        total_financial = financial_A + financial_B
        if total_financial > 0:
            financial_ratio_A = financial_A / total_financial
            financial_ratio_B = financial_B / total_financial
        else:
            financial_ratio_A = financial_ratio_B = 0.5
        
        # For numerical queries, if one operator has significantly more XBRL data, trust it
        FINANCIAL_DOMINANCE_THRESHOLD = 0.55  # 55% or more of financial evidence
        
        if financial_ratio_A >= FINANCIAL_DOMINANCE_THRESHOLD:
            logger.info(f"TRUST_A: Operator A has {financial_ratio_A:.0%} of FINANCIAL_LINE evidence for numerical query")
            return TrustDecision.TRUST_A
        
        if financial_ratio_B >= FINANCIAL_DOMINANCE_THRESHOLD:
            logger.info(f"TRUST_B: Operator B has {financial_ratio_B:.0%} of FINANCIAL_LINE evidence for numerical query")
            return TrustDecision.TRUST_B
        
        # If close to 50/50 but there's answer disagreement, check source authority
        if delta_A > 0.05:  # Answers differ slightly
            # Prefer operator with higher source authority score
            if reliability_A.source_authority > reliability_B.source_authority + 0.1:
                logger.info(f"TRUST_A: Higher source authority ({reliability_A.source_authority:.2f} vs {reliability_B.source_authority:.2f}) for numerical query with answer discrepancy")
                return TrustDecision.TRUST_A
            elif reliability_B.source_authority > reliability_A.source_authority + 0.1:
                logger.info(f"TRUST_B: Higher source authority ({reliability_B.source_authority:.2f} vs {reliability_A.source_authority:.2f}) for numerical query with answer discrepancy")
                return TrustDecision.TRUST_B
    
    # =========================================================================
    # STANDARD TRUST DECISION LOGIC
    # =========================================================================
    
    # If answers agree closely, no need to choose
    if delta_A < 0.10:
        return TrustDecision.MERGE_EQUAL
    
    # If large reliability gap, trust the more reliable one
    RELIABILITY_GAP_THRESHOLD = 0.25
    
    if reliability_gap > RELIABILITY_GAP_THRESHOLD:
        if reliability_A.reliability_score > reliability_B.reliability_score:
            return TrustDecision.TRUST_A
        else:
            return TrustDecision.TRUST_B
    
    # Moderate gap - merge but weight by reliability
    if reliability_gap > 0.10:
        return TrustDecision.MERGE_WEIGHTED
    
    # Small gap - merge equally
    return TrustDecision.MERGE_EQUAL
```

### Update Source Authority Calculation

The `source_authority` should strongly favor XBRL evidence:

```python
def _compute_source_authority(self, evidence_types: Dict[str, int]) -> float:
    """
    Compute authority of sources.
    
    For numerical queries, XBRL is the gold standard.
    """
    total = sum(evidence_types.values())
    if total == 0:
        return 0.0
    
    # Weights by authority level
    AUTHORITY_WEIGHTS = {
        "FINANCIAL_LINE": 1.0,    # XBRL - highest authority
        "TABLE_ROW": 0.9,         # Structured table data
        "TABLE": 0.85,            # Table (less specific)
        "TEXT_SECTION": 0.4,      # Narrative text - can be out of context
        "NOTE": 0.3,              # Notes - often explanatory, may reference multiple periods
        "ENTITY": 0.2,            # Entity mentions - need context
    }
    
    weighted_sum = sum(
        count * AUTHORITY_WEIGHTS.get(node_type, 0.3)
        for node_type, count in evidence_types.items()
    )
    
    return weighted_sum / total
```

### Update Answer Generation for TRUST_A/TRUST_B

When trust decision is TRUST_A or TRUST_B, generate answer from trusted source only:

```python
def _generate_answer_with_trust(
    self,
    query: str,
    belief_A,
    belief_B,
    mode_decision: ModeDecision,
    trajectory: List,
) -> str:
    """Generate answer respecting trust decision."""
    
    mode = mode_decision.mode
    trust = mode_decision.trust_decision
    
    # =========================================================================
    # TRUST_A: Use Operator A's evidence as authoritative
    # =========================================================================
    if trust == TrustDecision.TRUST_A:
        return self._generate_trusted_answer(
            query=query,
            trusted_evidence=belief_A.evidence,
            trusted_answer=belief_A.answer,
            other_evidence=belief_B.evidence,
            other_answer=belief_B.answer,
            trusted_name="Operator A (Financial/XBRL)",
            mode_decision=mode_decision,
        )
    
    # =========================================================================
    # TRUST_B: Use Operator B's evidence as authoritative
    # =========================================================================
    elif trust == TrustDecision.TRUST_B:
        return self._generate_trusted_answer(
            query=query,
            trusted_evidence=belief_B.evidence,
            trusted_answer=belief_B.answer,
            other_evidence=belief_A.evidence,
            other_answer=belief_A.answer,
            trusted_name="Operator B (Narrative)",
            mode_decision=mode_decision,
        )
    
    # =========================================================================
    # MERGE modes: Use appropriate merge strategy
    # =========================================================================
    elif trust == TrustDecision.MERGE_WEIGHTED:
        return self._generate_weighted_answer(query, belief_A, belief_B, mode_decision)
    
    else:  # MERGE_EQUAL or CONFLICT
        return self._generate_merged_answer(query, belief_A, belief_B, mode_decision, trajectory)


def _generate_trusted_answer(
    self,
    query: str,
    trusted_evidence: List,
    trusted_answer: str,
    other_evidence: List,
    other_answer: str,
    trusted_name: str,
    mode_decision: ModeDecision,
) -> str:
    """
    Generate answer from trusted source only.
    
    For numerical queries, this ensures XBRL data takes precedence.
    """
    
    prompt = f"""Answer this question using the AUTHORITATIVE evidence provided.

Question: {query}

AUTHORITATIVE EVIDENCE (from {trusted_name}):
{self._format_evidence(trusted_evidence)}

AUTHORITATIVE ANSWER (use this as the primary source):
{trusted_answer}

INSTRUCTIONS:
1. Use ONLY the authoritative evidence and answer
2. Give a direct, confident answer
3. Do NOT average or blend with other sources
4. If the authoritative answer contains a specific number, use that EXACT number
5. Confidence: {mode_decision.confidence:.0%}

Answer:"""
    
    return self.llm.generate(prompt)
```

### Add to LLM Interface

In `llm_interface.py`, add the trusted answer generation:

```python
def generate_trusted_answer(
    self,
    query: str,
    trusted_evidence: List[Dict],
    trusted_operator: str,
    mode_decision,
) -> str:
    """
    Generate answer from trusted operator's evidence only.
    
    Used when trust decision is TRUST_A or TRUST_B.
    """
    
    # Format evidence
    evidence_text = self._format_evidence_for_prompt(trusted_evidence)
    
    # Build prompt
    prompt = f"""You are answering a financial question using authoritative data.

Question: {query}

Authoritative Evidence (from {trusted_operator}):
{evidence_text}

Instructions:
- Answer directly using ONLY the evidence above
- If the evidence contains specific numbers, use those EXACT numbers
- Do not hedge or provide ranges unless the evidence itself shows a range
- Do not mention alternative figures from other sources
- Be concise and confident

Answer:"""
    
    response = self._call_completion(prompt, max_tokens=500)
    return response
```

---

## Task 6: Verification Test for Revenue Fix

After implementing the trust decision fix, the revenue query should produce:

```
TEST 1: Revenue Query
================================================================================
Query: What was Apple's total revenue in FY2023?
Expected: EXPLOIT with TRUST_A

RESULT:
  Mode: EXPLOIT [CORRECT]
  Trust Decision: TRUST_A [NEW - was MERGE_EQUAL]
  Confidence: 90%
  
  Reasoning: TRUST_A: Operator A has 62% of FINANCIAL_LINE evidence for numerical query
  
  Evidence A types: {'FINANCIAL_LINE': 8, 'NOTE': 3, 'TEXT_SECTION': 2}
  Evidence B types: {'NOTE': 7, 'TEXT_SECTION': 1, 'FINANCIAL_LINE': 5}
  
  Financial Evidence: A=8, B=5, Total=13
  A's share: 8/13 = 61.5% > 55% threshold → TRUST_A
  
  ANSWER:
  ----------------------------------------
  Apple's total revenue for fiscal year 2023 was $383.29 billion.
  ----------------------------------------
  
  [CORRECT - Using XBRL figure, not narrative figure]
```

---

## Task 7: Add Unit Tests for Trust Decision

```python
# tests/test_trust_decision.py

import pytest
from src.opmech.mode_selection import ModeSelector, TrustDecision
from src.opmech.query_classifier import QueryType, QueryClassification


class TestTrustDecisionNumerical:
    """Test trust decision for numerical queries."""
    
    def test_numerical_query_prefers_more_financial_evidence(self):
        """For numerical queries, trust operator with more FINANCIAL_LINE."""
        
        selector = ModeSelector()
        
        # Mock query classification
        query_class = QueryClassification(
            query_type=QueryType.NUMERICAL,
            complexity="simple",
            confidence=0.9,
            expects_number=True,
            classification_method="pattern",
            reasoning="numerical query",
            pattern_scores={}
        )
        
        # Mock reliability with evidence breakdown
        reliability_A = MockReliability(
            score=0.75,
            evidence_breakdown={"FINANCIAL_LINE": 8, "NOTE": 3, "TEXT_SECTION": 2}
        )
        reliability_B = MockReliability(
            score=0.70,
            evidence_breakdown={"NOTE": 7, "TEXT_SECTION": 1, "FINANCIAL_LINE": 5}
        )
        
        # Mock commutator with slight answer difference
        commutator = MockCommutator(delta_A=0.05)
        
        trust = selector._determine_trust(
            commutator, reliability_A, reliability_B, 
            reliability_gap=0.05, query_class=query_class
        )
        
        # Should trust A because 8/(8+5) = 61.5% > 55%
        assert trust == TrustDecision.TRUST_A
    
    def test_numerical_query_equal_financial_uses_source_authority(self):
        """When financial evidence is equal, use source authority."""
        
        selector = ModeSelector()
        
        query_class = QueryClassification(
            query_type=QueryType.NUMERICAL,
            complexity="simple",
            confidence=0.9,
            expects_number=True,
            classification_method="pattern",
            reasoning="numerical query",
            pattern_scores={}
        )
        
        # Equal FINANCIAL_LINE counts
        reliability_A = MockReliability(
            score=0.75,
            source_authority=0.8,  # Higher authority
            evidence_breakdown={"FINANCIAL_LINE": 5, "NOTE": 3}
        )
        reliability_B = MockReliability(
            score=0.70,
            source_authority=0.5,  # Lower authority
            evidence_breakdown={"NOTE": 5, "FINANCIAL_LINE": 5}
        )
        
        commutator = MockCommutator(delta_A=0.10)  # Answers differ
        
        trust = selector._determine_trust(
            commutator, reliability_A, reliability_B,
            reliability_gap=0.05, query_class=query_class
        )
        
        # Should trust A due to higher source authority
        assert trust == TrustDecision.TRUST_A
    
    def test_non_numerical_query_uses_standard_logic(self):
        """Non-numerical queries should use standard trust logic."""
        
        selector = ModeSelector()
        
        query_class = QueryClassification(
            query_type=QueryType.CAUSAL,
            complexity="moderate",
            confidence=0.85,
            expects_number=False,
            classification_method="pattern",
            reasoning="causal query",
            pattern_scores={}
        )
        
        reliability_A = MockReliability(
            score=0.60,
            evidence_breakdown={"FINANCIAL_LINE": 8, "NOTE": 2}
        )
        reliability_B = MockReliability(
            score=0.65,
            evidence_breakdown={"TEXT_SECTION": 6, "NOTE": 4}
        )
        
        commutator = MockCommutator(delta_A=0.08)  # Close agreement
        
        trust = selector._determine_trust(
            commutator, reliability_A, reliability_B,
            reliability_gap=0.05, query_class=query_class
        )
        
        # Should merge equally since answers agree and it's not numerical
        assert trust == TrustDecision.MERGE_EQUAL


class MockReliability:
    def __init__(self, score, evidence_breakdown, source_authority=0.5):
        self.reliability_score = score
        self.evidence_breakdown = evidence_breakdown
        self.source_authority = source_authority


class MockCommutator:
    def __init__(self, delta_A):
        self.delta_A = delta_A
```

---

## Expected Final Results

After implementing all fixes:

```
================================================================================
MODE SELECTION VERIFICATION TEST - FINAL
================================================================================

TEST 1/3: EXPLOIT MODE TEST
Query: What was Apple's total revenue in FY2023?
Expected: EXPLOIT with correct answer

RESULT:
  Mode: EXPLOIT [CORRECT]
  Trust: TRUST_A [CORRECT - using XBRL data]
  Confidence: 90%
  
  ANSWER: Apple's total revenue for fiscal year 2023 was $383.29 billion.
  [CORRECT ✓]

TEST 2/3: EXPLORE MODE TEST
Query: Is Apple's gross margin pressure cyclical or structural?
Expected: EXPLORE

RESULT:
  Mode: EXPLORE [CORRECT]
  Trust: MERGE_EQUAL [CORRECT - opinion needs both perspectives]
  Confidence: 44%
  
  ANSWER: ### Multiple Perspectives on Apple's Gross Margin Pressure...
  [CORRECT ✓]

TEST 3/3: ADAPTIVE MODE TEST
Query: What factors drove iPhone revenue changes in FY2023?
Expected: ADAPTIVE

RESULT:
  Mode: ADAPTIVE [CORRECT]
  Trust: MERGE_WEIGHTED [CORRECT - balanced causal analysis]
  Confidence: 75%
  
  ANSWER: Based on the primary financial data... The decrease can be attributed to...
  [CORRECT ✓]

================================================================================
SUMMARY
================================================================================
Mode Accuracy: 3/3 (100%)
Answer Accuracy: 3/3 (100%)
Trust Decision Accuracy: 3/3 (100%)
```

---

## Summary

### Why This Approach is More Robust

| Aspect | Old Approach | Hybrid Approach |
|--------|--------------|-----------------|
| Pattern matching | Priority order | Weighted scoring |
| Ambiguity handling | First match wins | Context rules disambiguate |
| Novel queries | Fail silently | LLM fallback |
| Complexity | Hardcoded per type | Derived from features |
| Confidence | Binary (match/no match) | Continuous score |
| Testability | Hard to test edge cases | Clear signals to verify |

### Key Design Principles

1. **No priority order** - All patterns scored, context rules adjust
2. **Disambiguation via context** - Linguistic rules handle overlaps
3. **Graceful degradation** - LLM fallback for ambiguous cases
4. **Derived complexity** - Based on actual query features, not type
5. **Transparent confidence** - Know when classification is uncertain

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/opmech/query_classifier.py` | **CREATE** - New hybrid classifier |
| `src/opmech/mode_selection.py` | MODIFY - Use hybrid classifier |
| `tests/test_hybrid_classifier.py` | **CREATE** - Test suite |
| `tests/test_mode_verification.py` | MODIFY - Update expected behaviors |
