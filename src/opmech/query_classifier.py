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

from src.opmech.constants import NUMERICAL_ASPECT_TERMS


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
    # Compatibility with old QueryClassification
    time_period: Optional[str] = None
    entities_mentioned: List[str] = None
    numerical_expected: bool = None    # Alias for expects_number
    # NEW: Track if query has numerical aspects even if not purely NUMERICAL type
    has_numerical_aspect: bool = False  # True if query mentions financial terms

    def __post_init__(self):
        if self.entities_mentioned is None:
            self.entities_mentioned = []
        if self.numerical_expected is None:
            self.numerical_expected = self.expects_number


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
    # QUALITATIVE AND DESCRIPTIVE PATTERNS (FIX 1)
    # These patterns indicate queries that should NEVER be EXPLOIT mode
    # =========================================================================

    # Patterns indicating qualitative/subjective content
    QUALITATIVE_PATTERNS = [
        "risk factors", "risks", "challenges", "threats", "concerns",
        "issues", "problems", "weaknesses", "strengths", "opportunities",
        "outlook", "guidance", "strategy", "competitive position",
        "competitive advantage", "market position", "headwinds", "tailwinds",
        "uncertainties", "vulnerabilities", "exposure"
    ]

    # Patterns indicating descriptive queries
    DESCRIPTIVE_QUERY_PATTERNS = [
        "describe", "explain", "discuss", "what are the", "tell me about",
        "overview", "summary", "main", "key", "primary", "major",
        "list", "enumerate", "identify", "outline"
    ]

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
        # Percentage/margin questions
        r"(margin|percentage|percent|rate|ratio)\s*(percentage|%)?\??$",
        r"^what is .*(margin|percentage|percent|rate|ratio)\b",
        r"\b(gross|net|operating|profit)\s*margin\b",
        # Short queries with fiscal year reference
        r"^[a-z]+'?s?\s*(fy|fiscal)\s*\d{4}\s*(revenue|income|sales|earnings)\??$",
        r"\b(fy|fiscal)\s*\d{4}\s*(revenue|income|sales|earnings)\??$",
        # Total/sales keywords as standalone
        r"^(total|annual)\s*(revenue|sales|income|expense|cost)\b",
    ]

    # OPINION: Asking for judgment/speculation
    OPINION_PATTERNS = [
        # Is/Are + judgment adjective
        r"^(is|are|does|do) .*(sustainable|viable|risky|safe|healthy|strong|weak)\b",
        r"^(is|are) .*(cyclical|structural|temporary|permanent|improving|worsening)\b",
        r"^(is|are) .* pressure .*(cyclical|structural)\b",
        # Should/Would/Will (speculation)
        r"^(should|would|will|could|might) .*(invest|buy|sell|increase|decrease|grow|decline)\b",
        # Will X continue/remain/keep (prediction questions)
        r"^will .*(continue|remain|keep|stay|last|persist|sustain)\b",
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
        # Valuation judgments
        r"^(is|are) .*(overvalued|undervalued|fairly valued|expensive|cheap)\b",
        r"\b(overvalued|undervalued|fairly valued)\b",
        # Investment opinion
        r"^should i (invest|buy|sell|hold)\b",
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
            "description": "Questions starting with Is/Are + judgment word -> OPINION",
            "pattern": r"^(is|are|does|do|will|would|should|could)\b",
            "judgment_words": ["sustainable", "cyclical", "structural", "risky",
                             "safe", "good", "bad", "healthy", "concerning",
                             "temporary", "permanent", "improving", "worsening",
                             "overvalued", "undervalued", "fairly valued", "expensive", "cheap"],
            "boost": {QueryType.OPINION: 5},
            "penalize": {QueryType.NUMERICAL: 3},
        },
        {
            "name": "what_was_amount",
            "description": "What was/is + financial term at end -> NUMERICAL",
            "pattern": r"^what (was|is|were|are)\b",
            "end_words": ["revenue", "income", "sales", "expense", "profit",
                         "margin", "earnings", "eps", "cost"],
            "check_ending": True,
            "boost": {QueryType.NUMERICAL: 4},
            "penalize": {QueryType.OPINION: 2},
        },
        {
            "name": "why_what_caused",
            "description": "Why/What caused/drove -> CAUSAL",
            "pattern": r"(^why\b|what (caused|drove|factors))",
            "boost": {QueryType.CAUSAL: 5},
            "penalize": {QueryType.NUMERICAL: 3, QueryType.OPINION: 2},
        },
        {
            "name": "or_judgment",
            "description": "X or Y where both are judgment terms -> OPINION",
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
            "description": "Ends with fiscal year reference -> likely NUMERICAL",
            "pattern": r"(in |for )(fy|fiscal year)?\s*\d{4}\s*\??$",
            "boost": {QueryType.NUMERICAL: 3, QueryType.TEMPORAL: 2},
            "penalize": {},
        },
        {
            "name": "how_did_change",
            "description": "How did X change -> TEMPORAL",
            "pattern": r"^how (did|has|have)\b.*\b(change|grow|decline|increase|decrease)",
            "boost": {QueryType.TEMPORAL: 4},
            "penalize": {QueryType.NUMERICAL: 2},
        },
        {
            "name": "factors_drove",
            "description": "What factors drove/caused -> CAUSAL not NUMERICAL",
            "pattern": r"(what |which )(factors?|reasons?|drivers?)\b",
            "boost": {QueryType.CAUSAL: 5},
            "penalize": {QueryType.NUMERICAL: 4},
        },
        {
            "name": "short_fiscal_year_query",
            "description": "Short queries with fiscal year + financial term -> NUMERICAL",
            "pattern": r"(fy|fiscal)\s*\d{4}",
            "end_words": ["revenue", "income", "sales", "earnings", "profit", "expense", "cost"],
            "check_ending": True,
            "boost": {QueryType.NUMERICAL: 5},
            "penalize": {QueryType.DESCRIPTIVE: 3},
        },
        {
            "name": "margin_percentage_query",
            "description": "Queries asking for margin/percentage value -> NUMERICAL",
            "pattern": r"(^what is|^how much|\?$).*(margin|percentage|percent|ratio|rate)",
            "boost": {QueryType.NUMERICAL: 3},
            "penalize": {QueryType.DESCRIPTIVE: 2},
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
        0. Check for qualitative patterns (FIX 1: force DESCRIPTIVE for qualitative)
        1. Pattern scoring
        2. Context rule application
        3. Confidence check
        4. LLM fallback (if needed)
        5. Complexity determination
        """
        query_lower = query.lower().strip()

        # Stage 0 (FIX 1): Check for qualitative patterns first
        # These queries should NEVER be classified as factual/numerical
        is_qualitative = self._is_qualitative_query(query_lower)
        if is_qualitative:
            logger.debug(f"Query detected as qualitative: {query[:50]}...")

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

        # Stage 3.5 (FIX 1): Override to DESCRIPTIVE for qualitative queries
        # This prevents risk factor queries from being classified as factual
        if is_qualitative and query_type in [QueryType.NUMERICAL]:
            logger.info(f"FIX 1: Overriding {query_type.value} to DESCRIPTIVE for qualitative query")
            query_type = QueryType.DESCRIPTIVE
            method = "qualitative_override"
            # Boost descriptive score for downstream use
            adjusted_scores[QueryType.DESCRIPTIVE] = max(
                adjusted_scores.get(QueryType.DESCRIPTIVE, 0) + 5,
                adjusted_scores.get(QueryType.NUMERICAL, 0) + 1
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

        # Extract time period
        time_period = self._extract_time_period(query_lower)

        # Extract entities
        entities = self._extract_entities(query)

        # NEW: Check for numerical aspects (even if not purely NUMERICAL type)
        has_numerical_aspect = self._has_numerical_aspect(query_lower)

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
            pattern_scores={k.value: v for k, v in adjusted_scores.items()},
            time_period=time_period,
            entities_mentioned=entities,
            has_numerical_aspect=has_numerical_aspect,
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
- "What was revenue?" -> NUMERICAL (asking for a number)
- "Why did revenue decline?" -> CAUSAL (asking for reasons)
- "Is the decline temporary?" -> OPINION (asking for judgment)
- "How did revenue change over time?" -> TEMPORAL (asking about trend)
- "What factors drove revenue?" -> CAUSAL (asking for causes, not a number)

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

    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract time period if mentioned."""
        time_patterns = [
            r"fy\s*(\d{4})",
            r"fiscal\s*(year\s*)?(\d{4})",
            r"q([1-4])\s*(\d{4})",
            r"(\d{4})\s*(annual|yearly)",
        ]
        for pattern in time_patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(0)
        return None

    def _extract_entities(self, query: str) -> List[str]:
        """Extract mentioned entities (simplified)."""
        words = query.split()
        entities = []
        for word in words:
            if word.lower() in ["what", "how", "why", "the", "a", "an", "is", "was", "were", "are"]:
                continue
            if len(word) > 2 and word[0].isupper():
                entities.append(word)
        return entities

    def _has_numerical_aspect(self, query: str) -> bool:
        """
        Check if query has numerical/financial aspects even if not purely NUMERICAL type.

        This is critical for hybrid queries like "Is Apple's gross margin pressure cyclical?"
        which are classified as OPINION but need FINANCIAL_LINE data to answer properly.

        Args:
            query: User query string

        Returns:
            True if query mentions financial terms that need numerical data
        """
        query_lower = query.lower()
        return any(term in query_lower for term in NUMERICAL_ASPECT_TERMS)

    def _is_qualitative_query(self, query: str) -> bool:
        """
        Check if query is asking for qualitative/descriptive information.

        FIX 1: These queries should NEVER trigger EXPLOIT mode because they
        require narrative evidence, not just numbers.

        Examples:
        - "What are Apple's risk factors?" -> qualitative (needs Item 1A narrative)
        - "What challenges does Apple face?" -> qualitative
        - "Describe Apple's competitive position" -> qualitative

        Args:
            query: User query string (lowercase)

        Returns:
            True if query matches qualitative patterns
        """
        # Check for qualitative subject patterns
        has_qualitative_subject = any(
            pattern in query for pattern in self.QUALITATIVE_PATTERNS
        )

        # Check for descriptive verb patterns
        has_descriptive_verb = any(
            pattern in query for pattern in self.DESCRIPTIVE_QUERY_PATTERNS
        )

        # If query matches qualitative patterns OR asks for descriptive info about something
        if has_qualitative_subject:
            return True

        # "What are the X" patterns combined with certain nouns
        if has_descriptive_verb and any(
            word in query for word in ["factors", "risks", "challenges", "issues", "concerns"]
        ):
            return True

        return False

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
# FACTORY FUNCTION
# =============================================================================

def create_hybrid_classifier(llm_interface=None) -> HybridQueryClassifier:
    """Create a configured hybrid query classifier."""
    return HybridQueryClassifier(
        llm_interface=llm_interface,
        enable_llm_fallback=llm_interface is not None
    )
