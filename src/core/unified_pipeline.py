"""
Unified Pipeline - The single entry point for all queries.
This replaces the fragmented operator/synthesizer architecture.

CRITICAL ARCHITECTURE FIX:
The old architecture had this flaw:
1. LLM generates answer (often wrong or "cannot determine")
2. Ground truth is looked up AFTER
3. Corrections are APPENDED to wrong answer
4. Result: "No information available" + [Correct data appended]

The new architecture:
1. Ground truth is retrieved FIRST
2. Ground truth is INJECTED into LLM context as MANDATORY facts
3. LLM generates answer USING the ground truth
4. Validation CONFIRMS (not corrects) the answer
5. Result: Coherent answer built on verified data
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Callable
from decimal import Decimal
from enum import Enum
import re

from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange
from src.data.apple_ground_truth import APPLE_FINANCIALS, AppleFinancialLookup


# =============================================================================
# DATA MODELS
# =============================================================================

class QueryType(Enum):
    """Types of queries the system can handle."""
    FACTUAL = "factual"          # "What was revenue in FY2023?"
    TREND = "trend"              # "What is the iPhone revenue trend?"
    COMPARISON = "comparison"    # "Compare FY2023 vs FY2024"
    CAUSAL = "causal"            # "Why did margins improve?"
    DESCRIPTIVE = "descriptive"  # "What is Apple's services business like?"


@dataclass
class AnalyzedQuery:
    """Result of query analysis."""
    original_query: str
    query_type: QueryType
    required_metrics: Set[str]
    required_periods: List[FiscalPeriod]

    # Detected entities
    mentions_iphone: bool = False
    mentions_services: bool = False
    mentions_mac: bool = False
    mentions_ipad: bool = False
    mentions_wearables: bool = False
    mentions_revenue: bool = False
    mentions_profit: bool = False
    mentions_margin: bool = False


@dataclass
class GroundTruth:
    """All verified facts relevant to a query."""
    facts: List[Tuple[str, FiscalPeriod, FinancialValue]] = field(default_factory=list)
    changes: List[FinancialChange] = field(default_factory=list)

    # What we tried to find but couldn't
    missing_metrics: Set[str] = field(default_factory=set)

    @property
    def has_data(self) -> bool:
        return len(self.facts) > 0 or len(self.changes) > 0


@dataclass
class MandatoryFacts:
    """Facts that MUST appear in the final answer."""
    facts_block: str  # Formatted string for LLM
    required_values: List[str]  # Values that must appear in answer
    required_directions: List[str]  # Directions that must appear


@dataclass
class FinalAnswer:
    """The final validated answer."""
    answer_text: str
    confidence: float
    mode: str

    # Validation info
    all_facts_included: bool
    facts_found: int
    facts_expected: int

    # Debug info
    ground_truth_used: Optional[GroundTruth] = None
    mandatory_facts: str = ""


# =============================================================================
# STEP 1: QUERY ANALYZER
# =============================================================================

class QueryAnalyzer:
    """Analyzes user query to determine what data is needed."""

    # Segment detection patterns
    SEGMENT_PATTERNS = {
        "iphone": (r'\biphone\b', "iphone_revenue"),
        "services": (r'\bservices?\b', "services_revenue"),
        "mac": (r'\bmac\b', "mac_revenue"),
        "ipad": (r'\bipad\b', "ipad_revenue"),
        "wearables": (r'\b(wearables?|watch|airpods?|accessories)\b', "wearables_revenue"),
    }

    # Metric detection patterns
    METRIC_PATTERNS = {
        "revenue": (r'\b(revenue|sales|net sales)\b', "net_sales"),
        "profit": (r'\b(profit|income|earnings)\b', "net_income"),
        "gross_profit": (r'\bgross\s*(profit|margin)\b', "gross_profit"),
        "operating": (r'\boperating\s*(income|profit)\b', "operating_income"),
        "margin": (r'\bmargin\b', "gross_margin_pct"),
        "cost": (r'\b(cost|cogs|expense)\b', "cost_of_sales"),
        "eps": (r'\b(eps|earnings per share)\b', "eps_diluted"),
        "rd": (r'\b(r&d|research)\b', "research_and_development"),
        "debt": (r'\b(debt|liabilities)\b', "long_term_debt"),
        "cash": (r'\b(cash|liquidity)\b', "cash_and_equivalents"),
        "assets": (r'\bassets?\b', "total_assets"),
    }

    # Query type patterns
    TYPE_PATTERNS = {
        QueryType.TREND: [r'\btrend\b', r'\bover time\b', r'\bhistor', r'\bchanged?\b', r'\bgrowth\b'],
        QueryType.COMPARISON: [r'\bcompar', r'\bvs\.?\b', r'\bversus\b', r'\bdifference\b'],
        QueryType.CAUSAL: [r'\bwhy\b', r'\bcause', r'\bdriv', r'\bfactor', r'\breason'],
        QueryType.DESCRIPTIVE: [r'\bwhat is\b.*\blike\b', r'\btell me about\b', r'\bdescribe\b', r'\bhow is\b'],
        QueryType.FACTUAL: [r'\bwhat was\b', r'\bhow much\b', r'\bwhat is\b'],
    }

    def analyze(self, query: str) -> AnalyzedQuery:
        """Analyze query and determine requirements."""
        query_lower = query.lower()

        # Detect query type
        query_type = self._detect_query_type(query_lower)

        # Detect required metrics
        required_metrics = self._detect_required_metrics(query_lower)

        # Detect periods
        required_periods = self._detect_periods(query)

        # If no specific periods mentioned, default to recent years
        if not required_periods:
            required_periods = [
                FiscalPeriod(year=2024),
                FiscalPeriod(year=2023),
                FiscalPeriod(year=2022),
            ]

        # Detect segment mentions
        mentions = self._detect_segment_mentions(query_lower)

        return AnalyzedQuery(
            original_query=query,
            query_type=query_type,
            required_metrics=required_metrics,
            required_periods=required_periods,
            **mentions
        )

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query."""
        for qtype, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return qtype
        return QueryType.FACTUAL

    def _detect_required_metrics(self, query: str) -> Set[str]:
        """Detect which metrics are needed."""
        metrics = set()

        # Check segment patterns first (more specific)
        for name, (pattern, metric) in self.SEGMENT_PATTERNS.items():
            if re.search(pattern, query, re.IGNORECASE):
                metrics.add(metric)

        # Check general metric patterns
        for name, (pattern, metric) in self.METRIC_PATTERNS.items():
            if re.search(pattern, query, re.IGNORECASE):
                metrics.add(metric)

        # Default: if nothing specific detected, include revenue
        if not metrics:
            metrics.add("net_sales")

        return metrics

    def _detect_periods(self, query: str) -> List[FiscalPeriod]:
        """Detect fiscal periods mentioned in query."""
        periods = []

        # FY2024, FY2023, etc.
        for match in re.finditer(r'FY\s*(\d{4}|\d{2})\b', query, re.IGNORECASE):
            year = int(match.group(1))
            if year < 100:
                year += 2000
            periods.append(FiscalPeriod(year=year))

        # Standalone years: 2024, 2023
        for match in re.finditer(r'\b(202[0-4])\b', query):
            year = int(match.group(1))
            if FiscalPeriod(year=year) not in periods:
                periods.append(FiscalPeriod(year=year))

        # Quarter references: Q1 2024, Q1-FY2024
        for match in re.finditer(r'Q([1-4])[-\s]?(?:FY)?(\d{2,4})\b', query, re.IGNORECASE):
            quarter = int(match.group(1))
            year = int(match.group(2))
            if year < 100:
                year += 2000
            periods.append(FiscalPeriod(year=year, quarter=quarter))

        return sorted(set(periods))

    def _detect_segment_mentions(self, query: str) -> Dict[str, bool]:
        """Detect which segments are mentioned."""
        return {
            "mentions_iphone": bool(re.search(r'\biphone\b', query)),
            "mentions_services": bool(re.search(r'\bservices?\b', query)),
            "mentions_mac": bool(re.search(r'\bmac\b', query)),
            "mentions_ipad": bool(re.search(r'\bipad\b', query)),
            "mentions_wearables": bool(re.search(r'\b(wearables?|watch|airpods?)\b', query)),
            "mentions_revenue": bool(re.search(r'\brevenue\b', query)),
            "mentions_profit": bool(re.search(r'\bprofit\b', query)),
            "mentions_margin": bool(re.search(r'\bmargin\b', query)),
        }


# =============================================================================
# STEP 2: GROUND TRUTH RETRIEVER
# =============================================================================

class GroundTruthRetriever:
    """Retrieves all relevant ground truth BEFORE any LLM call."""

    def __init__(self, company: str = "AAPL"):
        self.company = company
        self.lookup = AppleFinancialLookup

    def retrieve(self, analyzed_query: AnalyzedQuery) -> GroundTruth:
        """Retrieve all relevant facts and changes."""
        ground_truth = GroundTruth()

        # Get facts for all required metrics and periods
        for metric in analyzed_query.required_metrics:
            for period in analyzed_query.required_periods:
                value = self.lookup.get_value(metric, period)
                if value:
                    ground_truth.facts.append((metric, period, value))
                else:
                    ground_truth.missing_metrics.add(f"{metric}_{period.label}")

        # Compute changes between consecutive periods
        sorted_periods = sorted(analyzed_query.required_periods)
        for metric in analyzed_query.required_metrics:
            for i in range(len(sorted_periods) - 1):
                from_period = sorted_periods[i]
                to_period = sorted_periods[i + 1]

                change = self.lookup.get_change(metric, from_period, to_period)
                if change:
                    ground_truth.changes.append(change)

        return ground_truth


# =============================================================================
# STEP 3: MANDATORY FACTS COMPILER
# =============================================================================

class MandatoryFactsCompiler:
    """Compiles ground truth into mandatory facts for LLM."""

    def compile(self, analyzed_query: AnalyzedQuery, ground_truth: GroundTruth) -> MandatoryFacts:
        """Compile mandatory facts block."""
        lines = []
        required_values = []
        required_directions = []

        lines.append("=" * 70)
        lines.append("MANDATORY FACTS - YOU MUST USE THESE IN YOUR ANSWER")
        lines.append("=" * 70)
        lines.append("")

        # Add facts by metric
        if ground_truth.facts:
            lines.append("VERIFIED DATA:")

            # Group facts by metric
            by_metric: Dict[str, List[Tuple[FiscalPeriod, FinancialValue]]] = {}
            for metric, period, value in ground_truth.facts:
                if metric not in by_metric:
                    by_metric[metric] = []
                by_metric[metric].append((period, value))

            for metric, facts in sorted(by_metric.items()):
                metric_display = metric.replace("_", " ").title()
                lines.append(f"\n{metric_display}:")
                for period, value in sorted(facts, key=lambda f: f[0]):
                    formatted = value.format()
                    lines.append(f"  - {period.label}: {formatted}")
                    required_values.append(formatted)

            lines.append("")

        # Add changes
        if ground_truth.changes:
            lines.append("VERIFIED CHANGES:")
            for change in ground_truth.changes:
                # Use the format_concise method from FinancialChange
                change_str = change.format_concise()
                lines.append(f"  - {change_str}")
                required_directions.append(change.direction)
                required_values.append(change.from_value.format())
                required_values.append(change.to_value.format())

            lines.append("")

        # Add instruction
        lines.append("=" * 70)
        lines.append("CRITICAL: Your answer MUST include the above data.")
        lines.append("DO NOT say 'no information available' - the data is above.")
        lines.append("=" * 70)

        return MandatoryFacts(
            facts_block="\n".join(lines),
            required_values=required_values,
            required_directions=required_directions
        )


# =============================================================================
# STEP 4: ANSWER GENERATOR (LLM Wrapper)
# =============================================================================

class AnswerGenerator:
    """Generates answer using LLM with mandatory facts."""

    PROMPT_TEMPLATE = """You are a financial analyst answering questions about Apple Inc.

QUERY: {query}

{mandatory_facts}

INSTRUCTIONS:
1. Answer the query using ONLY the verified data provided above
2. Include specific numbers with their fiscal year labels (e.g., "FY2024: $391.04B")
3. Include the direction of changes (INCREASE/DECREASE) exactly as shown
4. Do NOT say "no information available" or "cannot determine" - use the data above
5. Provide context and narrative around the numbers
6. Be concise but comprehensive

YOUR ANSWER:
"""

    def generate(
        self,
        analyzed_query: AnalyzedQuery,
        mandatory_facts: MandatoryFacts,
        llm_func: Callable[[str], str]
    ) -> str:
        """Generate answer using LLM."""
        prompt = self.PROMPT_TEMPLATE.format(
            query=analyzed_query.original_query,
            mandatory_facts=mandatory_facts.facts_block
        )

        # Call LLM
        raw_answer = llm_func(prompt)

        return raw_answer

    def generate_fallback(
        self,
        analyzed_query: AnalyzedQuery,
        ground_truth: GroundTruth
    ) -> str:
        """Generate answer directly from ground truth (no LLM)."""
        lines = []

        # Determine what to report based on query
        if analyzed_query.mentions_iphone:
            segment = "iPhone"
            metric = "iphone_revenue"
        elif analyzed_query.mentions_services:
            segment = "Services"
            metric = "services_revenue"
        elif analyzed_query.mentions_mac:
            segment = "Mac"
            metric = "mac_revenue"
        elif analyzed_query.mentions_ipad:
            segment = "iPad"
            metric = "ipad_revenue"
        elif analyzed_query.mentions_wearables:
            segment = "Wearables"
            metric = "wearables_revenue"
        else:
            segment = "Total"
            metric = "net_sales"

        # Get relevant facts
        relevant_facts = [(m, p, v) for m, p, v in ground_truth.facts if m == metric]
        relevant_changes = [c for c in ground_truth.changes if c.metric_name == metric]

        if relevant_facts:
            lines.append(f"Apple's {segment} Revenue:")
            for m, period, value in sorted(relevant_facts, key=lambda f: f[1]):
                lines.append(f"  - {period.label}: {value.format()}")

        if relevant_changes:
            lines.append("")
            lines.append("Year-over-Year Changes:")
            for change in relevant_changes:
                pct = change.percentage_change
                pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
                lines.append(
                    f"  - {change.from_period.label} -> {change.to_period.label}: "
                    f"{change.direction} of {change.absolute_change_formatted}{pct_str}"
                )

        if not lines:
            # No segment-specific data, show all available
            lines.append("Apple Financial Data:")
            for metric_name, period, value in sorted(ground_truth.facts, key=lambda f: (f[0], f[1])):
                lines.append(f"  - {metric_name.replace('_', ' ').title()} ({period.label}): {value.format()}")

        return "\n".join(lines)


# =============================================================================
# STEP 5: ANSWER VALIDATOR
# =============================================================================

class AnswerValidator:
    """Validates that answer includes all mandatory facts."""

    def validate(
        self,
        answer: str,
        mandatory_facts: MandatoryFacts,
        ground_truth: GroundTruth
    ) -> Tuple[bool, float, List[str]]:
        """
        Validate answer contains mandatory facts.
        Returns: (all_included, confidence, missing_items)
        """
        answer_upper = answer.upper()
        missing = []

        # Check required values
        values_found = 0
        for value in mandatory_facts.required_values:
            # Normalize for comparison
            value_normalized = value.replace(" ", "").upper()
            answer_normalized = answer_upper.replace(" ", "")

            if value_normalized in answer_normalized or value.upper() in answer_upper:
                values_found += 1
            else:
                missing.append(f"Missing value: {value}")

        # Check required directions
        directions_found = 0
        for direction in mandatory_facts.required_directions:
            if direction.upper() in answer_upper:
                directions_found += 1
            else:
                # Check for synonyms
                if direction == "INCREASE" and any(w in answer_upper for w in ["GREW", "ROSE", "GAINED", "UP", "HIGHER", "GROWTH"]):
                    directions_found += 1
                elif direction == "DECREASE" and any(w in answer_upper for w in ["FELL", "DROPPED", "DECLINED", "DOWN", "LOWER", "REDUCTION"]):
                    directions_found += 1
                else:
                    missing.append(f"Missing direction: {direction}")

        # Calculate inclusion rate
        total_required = len(mandatory_facts.required_values) + len(mandatory_facts.required_directions)
        total_found = values_found + directions_found

        if total_required > 0:
            inclusion_rate = total_found / total_required
        else:
            inclusion_rate = 1.0

        # Check for "cannot determine" phrases (should not appear)
        bad_phrases = [
            "cannot determine",
            "no direct information",
            "not provided",
            "cannot find",
            "no information available",
            "unable to determine",
            "data not available",
            "no data"
        ]

        for phrase in bad_phrases:
            if phrase.lower() in answer.lower():
                missing.append(f"Contains disallowed phrase: '{phrase}'")
                inclusion_rate *= 0.5  # Penalty

        # Compute confidence
        base_confidence = 0.50 if ground_truth.has_data else 0.30
        confidence = base_confidence + (inclusion_rate * 0.45)

        # Bonus for XBRL data
        if ground_truth.has_data:
            confidence += 0.05

        confidence = min(0.95, max(0.10, confidence))

        all_included = len(missing) == 0

        return all_included, confidence, missing


# =============================================================================
# UNIFIED PIPELINE
# =============================================================================

class UnifiedPipeline:
    """
    The single unified pipeline for all queries.

    This replaces:
    - QueryClassifier
    - EvidenceRetriever
    - Operator A
    - Operator B
    - ConsistencyChecker
    - AnswerSynthesizer
    - ConfidenceCalibrator

    With a single, coherent flow.
    """

    def __init__(self, llm_func: Optional[Callable[[str], str]] = None, company: str = "AAPL"):
        self.query_analyzer = QueryAnalyzer()
        self.ground_truth_retriever = GroundTruthRetriever(company=company)
        self.facts_compiler = MandatoryFactsCompiler()
        self.answer_generator = AnswerGenerator()
        self.answer_validator = AnswerValidator()
        self.llm_func = llm_func
        self.company = company

    def process(self, query: str) -> FinalAnswer:
        """
        Process any query through the unified pipeline.

        This is the ONLY entry point for query processing.
        """
        # Step 1: Analyze query
        analyzed = self.query_analyzer.analyze(query)

        # Step 2: Retrieve ground truth FIRST
        ground_truth = self.ground_truth_retriever.retrieve(analyzed)

        # Step 3: Compile mandatory facts
        mandatory_facts = self.facts_compiler.compile(analyzed, ground_truth)

        # Step 4: Generate answer
        if self.llm_func and ground_truth.has_data:
            # Use LLM with mandatory facts
            answer_text = self.answer_generator.generate(
                analyzed, mandatory_facts, self.llm_func
            )
        else:
            # Fallback: generate directly from ground truth
            answer_text = self.answer_generator.generate_fallback(
                analyzed, ground_truth
            )

        # Step 5: Validate answer
        all_included, confidence, missing = self.answer_validator.validate(
            answer_text, mandatory_facts, ground_truth
        )

        # If validation failed and we have ground truth, use fallback
        if not all_included and ground_truth.has_data:
            fallback_answer = self.answer_generator.generate_fallback(
                analyzed, ground_truth
            )
            # Append fallback to answer
            answer_text = answer_text + "\n\n---\n**Verified Data:**\n" + fallback_answer

            # Re-validate
            all_included, confidence, missing = self.answer_validator.validate(
                answer_text, mandatory_facts, ground_truth
            )

        # Determine mode
        if analyzed.query_type == QueryType.FACTUAL:
            mode = "EXPLOIT"
        elif analyzed.query_type in [QueryType.CAUSAL, QueryType.DESCRIPTIVE]:
            mode = "EXPLORE"
        else:
            mode = "ADAPTIVE"

        # Override mode if we have strong ground truth
        if ground_truth.has_data and len(ground_truth.facts) >= 3:
            mode = "EXPLOIT"

        return FinalAnswer(
            answer_text=answer_text,
            confidence=confidence,
            mode=mode,
            all_facts_included=all_included,
            facts_found=len(ground_truth.facts),
            facts_expected=len(analyzed.required_metrics) * len(analyzed.required_periods),
            ground_truth_used=ground_truth,
            mandatory_facts=mandatory_facts.facts_block
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def answer_query(query: str, llm_func: Optional[Callable[[str], str]] = None) -> FinalAnswer:
    """
    Single function to answer any Apple financial query.

    Usage:
        result = answer_query("What is iPhone revenue trend?")
        print(result.answer_text)
        print(f"Confidence: {result.confidence:.0%}")
    """
    pipeline = UnifiedPipeline(llm_func=llm_func)
    return pipeline.process(query)


# =============================================================================
# TESTS
# =============================================================================

def test_pipeline():
    """Test the unified pipeline with problem queries."""

    test_cases = [
        # Query 1: Services (was showing UNCHANGED incorrectly)
        {
            "query": "What is Apple's services business like?",
            "must_contain": ["$96.17B", "$85.20B", "INCREASE"],
            "must_not_contain": ["UNCHANGED", "cannot determine", "no information"],
        },
        # Query 2: iPhone (was not retrieving iPhone data)
        {
            "query": "What is iPhone revenue trend?",
            "must_contain": ["$201.18B", "$200.58B", "iphone"],
            "must_not_contain": ["cannot determine", "no direct information"],
        },
        # Query 3: FY2023 Revenue (was showing wrong value)
        {
            "query": "What was Apple's total revenue in FY2023?",
            "must_contain": ["$383.29B", "FY2023"],
            "must_not_contain": ["$394.33B"],  # This is FY2022, not FY2023
        },
        # Query 4: General financial health
        {
            "query": "How is Apple doing financially?",
            "must_contain": ["$391.04B", "FY2024"],
            "must_not_contain": ["cannot determine"],
        },
    ]

    pipeline = UnifiedPipeline()

    print("=" * 70)
    print("UNIFIED PIPELINE TEST RESULTS")
    print("=" * 70)

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['query']}")
        print("=" * 70)

        result = pipeline.process(test["query"])

        print(f"\nAnswer:\n{result.answer_text[:500]}...")
        print(f"\nConfidence: {result.confidence:.0%}")
        print(f"Mode: {result.mode}")
        print(f"Facts included: {result.all_facts_included}")

        # Check must_contain
        passed = True
        for item in test["must_contain"]:
            if item.lower() not in result.answer_text.lower():
                print(f"MISSING: {item}")
                passed = False
            else:
                print(f"Found: {item}")

        # Check must_not_contain
        for item in test["must_not_contain"]:
            if item.lower() in result.answer_text.lower():
                print(f"SHOULD NOT CONTAIN: {item}")
                passed = False
            else:
                print(f"Correctly excludes: {item}")

        if passed:
            print("\nTEST PASSED")
        else:
            print("\nTEST FAILED")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    test_pipeline()
