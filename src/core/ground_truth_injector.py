"""
Ground Truth Injector - Injects ground truth into the OpMech pipeline.

This module provides a way to inject ground truth data into the existing
OpMech-GraphRAG system's LLM prompts, fixing the core architectural issue
without replacing the graph traversal functionality.

The key insight:
- Keep the full OpMech pipeline (dual operators, graph traversal, commutator)
- Modify the final answer generation to include mandatory ground truth facts
"""

from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field

from loguru import logger

from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange
from src.data.apple_ground_truth import APPLE_FINANCIALS, AppleFinancialLookup


@dataclass
class InjectedGroundTruth:
    """Ground truth data to inject into prompts."""
    facts_block: str
    required_values: List[str]
    metrics_found: Set[str]
    periods_found: Set[str]


class GroundTruthInjector:
    """
    Injects ground truth data into LLM prompts.

    Usage:
        injector = GroundTruthInjector()
        enhanced_prompt = injector.enhance_prompt(original_prompt, query)
    """

    # Segment detection patterns
    SEGMENT_MAP = {
        "iphone": "iphone_revenue",
        "services": "services_revenue",
        "mac": "mac_revenue",
        "ipad": "ipad_revenue",
        "wearables": "wearables_revenue",
    }

    # Metric detection patterns
    METRIC_MAP = {
        "revenue": "net_sales",
        "sales": "net_sales",
        "income": "net_income",
        "profit": "net_income",
        "gross profit": "gross_profit",
        "operating": "operating_income",
        "margin": "gross_margin_pct",
        "cost": "cost_of_sales",
        "eps": "eps_diluted",
        "r&d": "research_and_development",
        "research": "research_and_development",
    }

    def __init__(self, company: str = "AAPL"):
        self.company = company
        self.lookup = AppleFinancialLookup

    def extract_context(self, query: str) -> Tuple[Set[str], List[FiscalPeriod]]:
        """Extract required metrics and periods from query."""
        import re

        query_lower = query.lower()
        metrics = set()
        periods = []

        # Detect segments
        for segment, metric in self.SEGMENT_MAP.items():
            if segment in query_lower:
                metrics.add(metric)

        # Detect general metrics
        for pattern, metric in self.METRIC_MAP.items():
            if pattern in query_lower:
                metrics.add(metric)

        # Default to net_sales if nothing specific
        if not metrics:
            metrics.add("net_sales")

        # Detect periods
        for match in re.finditer(r'FY\s*(\d{4}|\d{2})\b', query, re.IGNORECASE):
            year = int(match.group(1))
            if year < 100:
                year += 2000
            periods.append(FiscalPeriod(year=year))

        for match in re.finditer(r'\b(202[0-4])\b', query):
            year = int(match.group(1))
            fp = FiscalPeriod(year=year)
            if fp not in periods:
                periods.append(fp)

        # Default to recent years
        if not periods:
            periods = [
                FiscalPeriod(year=2024),
                FiscalPeriod(year=2023),
                FiscalPeriod(year=2022),
            ]

        return metrics, sorted(set(periods))

    def get_ground_truth(self, query: str) -> InjectedGroundTruth:
        """Get ground truth data relevant to query."""
        metrics, periods = self.extract_context(query)

        lines = []
        required_values = []
        metrics_found = set()
        periods_found = set()

        lines.append("=" * 60)
        lines.append("VERIFIED XBRL DATA - USE THESE FACTS IN YOUR ANSWER")
        lines.append("=" * 60)
        lines.append("")

        # Get values for each metric/period combination
        for metric in metrics:
            metric_display = metric.replace("_", " ").title()
            metric_lines = []

            for period in periods:
                value = self.lookup.get_value(metric, period)
                if value:
                    formatted = value.format()
                    metric_lines.append(f"  - {period.label}: {formatted}")
                    required_values.append(formatted)
                    metrics_found.add(metric)
                    periods_found.add(period.label)

            if metric_lines:
                lines.append(f"{metric_display}:")
                lines.extend(metric_lines)
                lines.append("")

        # Get changes between consecutive periods
        if len(periods) >= 2:
            lines.append("Year-over-Year Changes:")
            sorted_periods = sorted(periods)
            for metric in metrics:
                for i in range(len(sorted_periods) - 1):
                    from_period = sorted_periods[i]
                    to_period = sorted_periods[i + 1]

                    change = self.lookup.get_change(metric, from_period, to_period)
                    if change:
                        change_str = change.format_concise()
                        lines.append(f"  - {change_str}")
                        required_values.append(change.direction)
            lines.append("")

        lines.append("=" * 60)
        lines.append("CRITICAL: Include these verified numbers in your answer.")
        lines.append("DO NOT say 'cannot determine' - the data is above.")
        lines.append("=" * 60)

        return InjectedGroundTruth(
            facts_block="\n".join(lines),
            required_values=required_values,
            metrics_found=metrics_found,
            periods_found=periods_found,
        )

    def enhance_prompt(self, original_prompt: str, query: str) -> str:
        """
        Enhance a prompt with ground truth data.

        This is the key function - it injects ground truth BEFORE the LLM
        generates its answer, rather than validating/correcting AFTER.
        """
        ground_truth = self.get_ground_truth(query)

        if not ground_truth.metrics_found:
            return original_prompt

        # Inject ground truth at the beginning of the prompt
        enhanced = f"{ground_truth.facts_block}\n\n{original_prompt}"

        return enhanced

    def validate_answer(
        self,
        answer: str,
        ground_truth: InjectedGroundTruth
    ) -> Tuple[bool, float, List[str]]:
        """
        Validate that answer includes ground truth values.
        Returns: (all_included, inclusion_rate, missing_items)
        """
        answer_upper = answer.upper()
        missing = []
        found = 0

        for value in ground_truth.required_values:
            value_normalized = value.replace(" ", "").upper()
            answer_normalized = answer_upper.replace(" ", "")

            if value_normalized in answer_normalized or value.upper() in answer_upper:
                found += 1
            else:
                # Check for direction synonyms
                if value == "INCREASE" and any(w in answer_upper for w in ["GREW", "ROSE", "GAINED", "GROWTH", "UP"]):
                    found += 1
                elif value == "DECREASE" and any(w in answer_upper for w in ["FELL", "DROPPED", "DECLINED", "DOWN"]):
                    found += 1
                else:
                    missing.append(f"Missing: {value}")

        total = len(ground_truth.required_values)
        rate = found / total if total > 0 else 1.0
        all_included = len(missing) == 0

        return all_included, rate, missing


def create_injector(company: str = "AAPL") -> GroundTruthInjector:
    """Create a ground truth injector."""
    return GroundTruthInjector(company=company)
