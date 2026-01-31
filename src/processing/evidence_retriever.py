"""
Evidence Retrieval - Ensures segment data is always retrieved.

FIX 3: Added period granularity detection (annual vs quarterly)
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import re
from loguru import logger

from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange
from src.data.apple_ground_truth import AppleFinancialLookup


# =============================================================================
# FIX 3: Period Granularity Detection
# =============================================================================

# Keywords that indicate annual data is needed
ANNUAL_KEYWORDS = [
    "year", "years", "annual", "annually", "fy", "fiscal year",
    "three years", "past years", "yearly", "10-k", "10k",
    "full year", "over the years", "last few years"
]

# Keywords that indicate quarterly data is needed
QUARTERLY_KEYWORDS = [
    "quarter", "quarterly", "q1", "q2", "q3", "q4",
    "10-q", "10q", "this quarter", "last quarter",
    "quarterly basis", "quarter-over-quarter", "qoq"
]


def detect_period_granularity(query: str) -> str:
    """
    Detect whether the query asks for annual or quarterly data.

    FIX 3: This prevents returning quarterly data when user asks for
    "past three years" or annual trends.

    Args:
        query: User query string

    Returns:
        "quarterly" or "annual" (default to annual if unclear)
    """
    query_lower = query.lower()

    # Check for quarterly keywords first (more specific)
    if any(kw in query_lower for kw in QUARTERLY_KEYWORDS):
        logger.debug(f"FIX 3: Detected quarterly granularity for query")
        return "quarterly"

    # Check for annual keywords
    if any(kw in query_lower for kw in ANNUAL_KEYWORDS):
        logger.debug(f"FIX 3: Detected annual granularity for query")
        return "annual"

    # Default to annual (more common for financial analysis)
    return "annual"


def filter_evidence_by_granularity(evidence: List, granularity: str) -> List:
    """
    Filter evidence nodes based on period granularity.

    FIX 3: Ensures we return annual data for annual queries and
    quarterly data for quarterly queries.

    Args:
        evidence: List of evidence nodes
        granularity: "annual" or "quarterly"

    Returns:
        Filtered list of evidence nodes matching the granularity
    """
    if not evidence:
        return evidence

    filtered = []

    for e in evidence:
        # Get source and period information from the evidence
        source = getattr(e, 'source', '') or ''
        period = str(getattr(e, 'period', '') or getattr(e, 'periods', '') or '')
        content = getattr(e, 'content', '') or ''

        if granularity == "annual":
            # Include 10-K data or FY annual data
            is_annual = (
                "10-K" in source or
                "10-k" in source.lower() or
                "FY20" in period or
                "FY19" in period or
                bool(re.search(r'\bFY\d{4}\b', period)) or
                ("annual" in content.lower() and "quarterly" not in content.lower()) or
                # Also include if no quarter is specified
                (not any(q in period for q in ["Q1", "Q2", "Q3", "Q4", "q1", "q2", "q3", "q4"]))
            )
            if is_annual:
                filtered.append(e)
        else:  # quarterly
            # Include 10-Q data or quarterly data
            is_quarterly = (
                "10-Q" in source or
                "10-q" in source.lower() or
                any(q in period for q in ["Q1", "Q2", "Q3", "Q4", "q1", "q2", "q3", "q4"]) or
                "quarter" in content.lower()
            )
            if is_quarterly:
                filtered.append(e)

    # If filtering removed all evidence, return original
    # (better to have some evidence than none)
    if not filtered:
        logger.warning(f"FIX 3: Granularity filter removed all evidence, returning original")
        return evidence

    logger.debug(f"FIX 3: Filtered evidence from {len(evidence)} to {len(filtered)} for {granularity} granularity")
    return filtered


@dataclass
class EvidenceNode:
    """A piece of retrieved evidence"""
    id: str
    content: str
    source: str
    node_type: str  # "xbrl", "text", "table"

    # Extracted structured data
    periods: List[FiscalPeriod] = field(default_factory=list)
    values: List[FinancialValue] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)

    # Pre-computed changes
    changes: List[FinancialChange] = field(default_factory=list)

    confidence: float = 1.0
    relevance_score: float = 0.0


@dataclass
class EvidenceSet:
    """Collection of evidence for a query"""
    query: str
    nodes: List[EvidenceNode] = field(default_factory=list)

    # Metrics that were requested but not found
    missing_metrics: Set[str] = field(default_factory=set)

    # Metrics that were found
    found_metrics: Set[str] = field(default_factory=set)

    def add(self, node: EvidenceNode):
        self.nodes.append(node)

    def get_xbrl_nodes(self) -> List[EvidenceNode]:
        return [n for n in self.nodes if n.node_type == "xbrl"]

    def get_text_nodes(self) -> List[EvidenceNode]:
        return [n for n in self.nodes if n.node_type == "text"]

    def get_all_changes(self) -> List[FinancialChange]:
        """Get all pre-computed changes from all nodes"""
        all_changes = []
        seen = set()
        for node in self.nodes:
            for change in node.changes:
                key = (change.metric_name, change.from_period.label, change.to_period.label)
                if key not in seen:
                    seen.add(key)
                    all_changes.append(change)
        return all_changes

    def get_all_values(self) -> Dict[str, Dict[str, FinancialValue]]:
        """Get all values organized by metric and period"""
        result: Dict[str, Dict[str, FinancialValue]] = {}
        for node in self.nodes:
            for i, metric in enumerate(node.metrics):
                if metric not in result:
                    result[metric] = {}
                if i < len(node.values) and i < len(node.periods):
                    result[metric][node.periods[i].label] = node.values[i]
        return result


class EvidenceRetriever:
    """
    Retrieves evidence for queries.
    CRITICAL: Always retrieves segment data for segment queries.
    """

    # Keywords that indicate segment-specific queries
    SEGMENT_KEYWORDS = {
        "iphone": ["iphone_revenue"],
        "services": ["services_revenue"],
        "service": ["services_revenue"],
        "mac": ["mac_revenue"],
        "ipad": ["ipad_revenue"],
        "wearables": ["wearables_revenue"],
        "accessories": ["wearables_revenue"],
        "watch": ["wearables_revenue"],
        "airpods": ["wearables_revenue"],
    }

    # Keywords that indicate specific metrics
    METRIC_KEYWORDS = {
        "revenue": ["net_sales"],
        "sales": ["net_sales"],
        "profit": ["gross_profit", "operating_income", "net_income"],
        "margin": ["gross_margin_pct"],
        "income": ["operating_income", "net_income"],
        "cost": ["cost_of_sales"],
        "eps": ["eps_diluted"],
        "earnings": ["net_income", "eps_diluted"],
        "r&d": ["research_and_development"],
        "research": ["research_and_development"],
        "debt": ["long_term_debt"],
        "cash": ["cash_and_equivalents"],
        "assets": ["total_assets"],
        "dividend": ["dividends_per_share"],
    }

    # Keywords that indicate comparison/trend queries
    TEMPORAL_KEYWORDS = [
        "trend", "trending", "change", "changed", "growth", "grew",
        "decline", "declined", "increase", "increased", "decrease",
        "decreased", "compare", "comparison", "over time", "year over year",
        "yoy", "y/y", "performing", "performance"
    ]

    def __init__(self, company: str = "AAPL"):
        self.company = company
        self.lookup = AppleFinancialLookup

    def retrieve(self, query: str, periods: List[FiscalPeriod] = None) -> EvidenceSet:
        """
        Retrieve evidence for a query.

        CRITICAL: For segment queries (iPhone, Services, etc.),
        ALWAYS retrieves segment-specific data.

        FIX 3: Respects period granularity (annual vs quarterly).
        """
        evidence = EvidenceSet(query=query)

        # FIX 3: Detect period granularity from query
        granularity = detect_period_granularity(query)

        # Default periods based on granularity
        if not periods:
            if granularity == "annual":
                # Default to annual periods (FY)
                periods = [
                    FiscalPeriod(year=2024, company=self.company, is_annual=True),
                    FiscalPeriod(year=2023, company=self.company, is_annual=True),
                    FiscalPeriod(year=2022, company=self.company, is_annual=True),
                    FiscalPeriod(year=2021, company=self.company, is_annual=True),
                ]
            else:
                # Default to recent quarters
                periods = [
                    FiscalPeriod(year=2024, quarter=4, company=self.company),
                    FiscalPeriod(year=2024, quarter=3, company=self.company),
                    FiscalPeriod(year=2024, quarter=2, company=self.company),
                    FiscalPeriod(year=2024, quarter=1, company=self.company),
                ]

        # Identify required metrics from query
        required_metrics = self._identify_required_metrics(query)

        # Retrieve XBRL data for each metric and period
        for metric in required_metrics:
            values_for_metric = []
            periods_for_metric = []

            for period in periods:
                value = self.lookup.get_value(metric, period)

                if value:
                    values_for_metric.append(value)
                    periods_for_metric.append(period)
                    evidence.found_metrics.add(metric)
                else:
                    evidence.missing_metrics.add(f"{metric}_{period.label}")

            if values_for_metric:
                # Create a node for this metric with all its values
                node = EvidenceNode(
                    id=f"xbrl_{metric}",
                    content=self._format_metric_content(metric, values_for_metric, periods_for_metric),
                    source="XBRL",
                    node_type="xbrl",
                    periods=periods_for_metric,
                    values=values_for_metric,
                    metrics=[metric] * len(values_for_metric),
                    confidence=1.0
                )

                # Compute changes between consecutive periods
                sorted_periods = sorted(periods_for_metric)
                for i in range(len(sorted_periods) - 1):
                    from_period = sorted_periods[i]
                    to_period = sorted_periods[i + 1]

                    change = self.lookup.get_change(metric, from_period, to_period)
                    if change:
                        node.changes.append(change)

                evidence.add(node)

        return evidence

    def _format_metric_content(
        self,
        metric: str,
        values: List[FinancialValue],
        periods: List[FiscalPeriod]
    ) -> str:
        """Format metric content for display"""
        lines = [f"[XBRL VERIFIED] {metric.upper().replace('_', ' ')}:"]
        for value, period in zip(values, periods):
            lines.append(f"  {period.label}: {value.format()}")
        return "\n".join(lines)

    def _identify_required_metrics(self, query: str) -> List[str]:
        """
        Identify which metrics are needed for the query.

        CRITICAL: Always includes segment-specific metrics when mentioned.
        """
        query_lower = query.lower()
        metrics = set()

        # Check for segment keywords - these take priority
        for keyword, segment_metrics in self.SEGMENT_KEYWORDS.items():
            if keyword in query_lower:
                metrics.update(segment_metrics)

        # Check for metric keywords
        for keyword, metric_list in self.METRIC_KEYWORDS.items():
            if keyword in query_lower:
                metrics.update(metric_list)

        # If asking about a specific segment, DON'T add total revenue
        # unless explicitly mentioned
        has_segment_query = any(
            keyword in query_lower
            for keyword in self.SEGMENT_KEYWORDS.keys()
        )

        # Default: if no specific metrics identified, get revenue overview
        if not metrics:
            metrics = {"net_sales", "gross_profit", "net_income"}

        # Add total revenue for context ONLY if not a specific segment query
        # or if "total" or "overall" is mentioned
        if not has_segment_query or "total" in query_lower or "overall" in query_lower:
            metrics.add("net_sales")

        # If this is a temporal/trend query, ensure we get multiple years of data
        is_temporal = any(kw in query_lower for kw in self.TEMPORAL_KEYWORDS)
        if is_temporal:
            # Make sure we have comparison data
            pass  # Already handled by default periods

        return list(metrics)

    def format_for_llm(self, evidence: EvidenceSet) -> str:
        """
        Format evidence for LLM consumption.

        CRITICAL: Includes pre-computed changes so LLM doesn't have to calculate.
        """
        lines = []

        # Section 1: XBRL Ground Truth
        xbrl_nodes = evidence.get_xbrl_nodes()
        if xbrl_nodes:
            lines.append("=" * 60)
            lines.append("XBRL VERIFIED DATA (Use these as ground truth)")
            lines.append("=" * 60)

            # Group by metric
            by_metric: Dict[str, List[EvidenceNode]] = {}
            for node in xbrl_nodes:
                for metric in set(node.metrics):
                    if metric not in by_metric:
                        by_metric[metric] = []
                    by_metric[metric].append(node)

            for metric, nodes in sorted(by_metric.items()):
                lines.append(f"\n{metric.upper().replace('_', ' ')}:")
                # Collect all values for this metric
                values_by_period = {}
                for node in nodes:
                    for i, (value, period) in enumerate(zip(node.values, node.periods)):
                        if i < len(node.metrics) and node.metrics[i] == metric:
                            values_by_period[period.label] = value

                # Sort by period and display
                for period_label in sorted(values_by_period.keys(), reverse=True):
                    value = values_by_period[period_label]
                    lines.append(f"  {period_label}: {value.format()}")

            lines.append("")

        # Section 2: Pre-computed Changes
        all_changes = evidence.get_all_changes()

        if all_changes:
            lines.append("=" * 60)
            lines.append("PRE-COMPUTED CHANGES (Use these, do NOT recompute)")
            lines.append("=" * 60)

            for change in all_changes:
                lines.append(f"\n{change.format()}")

            lines.append("")

        # Section 3: Missing data warning
        if evidence.missing_metrics:
            lines.append("=" * 60)
            lines.append("WARNING: Missing Data")
            lines.append("=" * 60)
            for missing in sorted(evidence.missing_metrics):
                lines.append(f"  - {missing}")
            lines.append("")

        return "\n".join(lines)

    def get_segment_evidence(
        self,
        segment: str,
        periods: List[FiscalPeriod] = None
    ) -> EvidenceSet:
        """
        Get evidence specifically for a product segment.
        """
        segment_lower = segment.lower()

        # Map segment name to metric
        segment_metric_map = {
            "iphone": "iphone_revenue",
            "services": "services_revenue",
            "mac": "mac_revenue",
            "ipad": "ipad_revenue",
            "wearables": "wearables_revenue",
            "accessories": "wearables_revenue",
        }

        metric = segment_metric_map.get(segment_lower)
        if not metric:
            # Try to find partial match
            for key, value in segment_metric_map.items():
                if key in segment_lower or segment_lower in key:
                    metric = value
                    break

        if not metric:
            evidence = EvidenceSet(query=f"Segment: {segment}")
            evidence.missing_metrics.add(f"Unknown segment: {segment}")
            return evidence

        # Create a query that targets this segment
        query = f"{segment} revenue"
        return self.retrieve(query, periods)

    def get_comparison_evidence(
        self,
        metric: str,
        from_period: FiscalPeriod,
        to_period: FiscalPeriod
    ) -> Optional[FinancialChange]:
        """
        Get pre-computed comparison between two periods.
        """
        return self.lookup.get_change(metric, from_period, to_period)

    def validate_value(
        self,
        metric: str,
        period: FiscalPeriod,
        claimed_value: FinancialValue
    ) -> tuple:
        """
        Validate a claimed value against ground truth.
        """
        return self.lookup.validate_claim(metric, period, claimed_value)
