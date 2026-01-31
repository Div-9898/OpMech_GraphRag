"""
Temporal Intelligence Module for OpMech Production System

Handles temporal reasoning for financial data with ground truth validation.

KEY PRINCIPLE: Always compute direction from actual values,
never rely on text interpretation alone. Pre-compute changes
so the LLM doesn't have to compute directions itself.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

from .type_safe_models import (
    FiscalPeriod,
    FinancialValue,
    Direction,
    EvidenceNode,
    ComputedChange,
)
from .metric_types import (
    MetricConfig,
    MetricType,
    GoodDirection,
    get_metric_config,
)


class TemporalIntelligence:
    """
    Handles temporal reasoning for financial data.

    KEY PRINCIPLE: Always compute direction from actual values,
    never rely on text interpretation alone.
    """

    def __init__(self, company: str = "AAPL"):
        """
        Initialize temporal intelligence module.

        Args:
            company: Company ticker for configuration
        """
        self.company = company

    def validate_direction_claim(
        self,
        claimed_direction: Direction,
        from_period: FiscalPeriod,
        to_period: FiscalPeriod,
        from_value: FinancialValue,
        to_value: FinancialValue
    ) -> Tuple[bool, Direction, str]:
        """
        Validate a claimed direction against actual values.

        CRITICAL: This is the ground truth. If the claim doesn't match
        the computed direction, the claim is WRONG.

        Args:
            claimed_direction: The direction claimed by the LLM
            from_period: Earlier fiscal period
            to_period: Later fiscal period
            from_value: Value in earlier period
            to_value: Value in later period

        Returns:
            Tuple of (is_valid, actual_direction, explanation)
        """
        # Compute actual direction from values
        actual_diff = to_value.normalized_amount - from_value.normalized_amount

        if actual_diff > Decimal("0"):
            actual_direction = Direction.INCREASE
        elif actual_diff < Decimal("0"):
            actual_direction = Direction.DECREASE
        else:
            actual_direction = Direction.UNCHANGED

        is_valid = claimed_direction == actual_direction

        # Format the change for the explanation
        change_value = FinancialValue(amount=abs(actual_diff), scale="units")

        # Calculate percentage change if possible
        if from_value.normalized_amount != Decimal("0"):
            pct_change = float(actual_diff / from_value.normalized_amount * 100)
            pct_str = f" ({pct_change:+.1f}%)"
        else:
            pct_str = ""

        if is_valid:
            explanation = (
                f"CORRECT: {actual_direction.value.upper()} "
                f"from {from_value.format()} [{from_period.label}] "
                f"to {to_value.format()} [{to_period.label}]{pct_str}"
            )
        else:
            explanation = (
                f"INCORRECT: Claimed {claimed_direction.value}, "
                f"but actual is {actual_direction.value}. "
                f"Values: {from_value.format()} [{from_period.label}] -> "
                f"{to_value.format()} [{to_period.label}] "
                f"(diff: {change_value.format()}{pct_str})"
            )

        return is_valid, actual_direction, explanation

    def compute_change(
        self,
        metric_name: str,
        from_period: FiscalPeriod,
        to_period: FiscalPeriod,
        from_value: FinancialValue,
        to_value: FinancialValue,
        metric_config: Optional[MetricConfig] = None
    ) -> ComputedChange:
        """
        Compute a change between two periods with all details.

        This should be called BEFORE the LLM sees the data,
        so the LLM can use the pre-computed direction instead
        of computing it itself (and potentially getting it wrong).

        Args:
            metric_name: Name of the metric (e.g., "Revenue", "Net Income")
            from_period: Earlier fiscal period
            to_period: Later fiscal period
            from_value: Value in earlier period
            to_value: Value in later period
            metric_config: Optional metric configuration for favorability

        Returns:
            ComputedChange with all details
        """
        # Compute direction
        diff = to_value.normalized_amount - from_value.normalized_amount

        if diff > Decimal("0"):
            direction = Direction.INCREASE
        elif diff < Decimal("0"):
            direction = Direction.DECREASE
        else:
            direction = Direction.UNCHANGED

        # Compute absolute change
        absolute_change = FinancialValue(amount=abs(diff), scale="units")

        # Compute percentage change
        if from_value.normalized_amount != Decimal("0"):
            percentage_change = float(diff / from_value.normalized_amount * 100)
        else:
            percentage_change = None

        # Determine favorability based on metric type
        is_favorable = None
        if metric_config is None:
            metric_config = get_metric_config(content=metric_name)

        if metric_config.good_direction == GoodDirection.INCREASE:
            is_favorable = direction == Direction.INCREASE
        elif metric_config.good_direction == GoodDirection.DECREASE:
            is_favorable = direction == Direction.DECREASE

        return ComputedChange(
            metric_name=metric_name,
            from_period=from_period,
            to_period=to_period,
            from_value=from_value,
            to_value=to_value,
            direction=direction,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            is_favorable=is_favorable
        )

    def compute_change_description(
        self,
        metric: str,
        from_period: FiscalPeriod,
        to_period: FiscalPeriod,
        from_value: FinancialValue,
        to_value: FinancialValue
    ) -> str:
        """
        Compute a change description that is ALWAYS correct.

        This description should be included in LLM context so the LLM
        doesn't have to compute the direction itself (and potentially get it wrong).

        Args:
            metric: Name of the metric
            from_period: Earlier fiscal period
            to_period: Later fiscal period
            from_value: Value in earlier period
            to_value: Value in later period

        Returns:
            Human-readable change description
        """
        diff = to_value.normalized_amount - from_value.normalized_amount
        abs_diff = abs(diff)

        # Create change value object
        change_value = FinancialValue(amount=abs_diff, scale="units")

        # Calculate percentage change
        if from_value.normalized_amount != Decimal("0"):
            pct_change = float(diff / from_value.normalized_amount * 100)
            pct_str = f" ({pct_change:+.1f}%)"
        else:
            pct_str = ""

        # Determine direction
        if diff > Decimal("0"):
            direction = "INCREASED"
        elif diff < Decimal("0"):
            direction = "DECREASED"
        else:
            direction = "UNCHANGED"

        # Determine favorability based on metric name
        metric_lower = metric.lower()
        if any(word in metric_lower for word in ['revenue', 'sales', 'income', 'profit', 'margin']):
            if direction == "INCREASED":
                favorability = "favorable"
            elif direction == "DECREASED":
                favorability = "unfavorable"
            else:
                favorability = "neutral"
        elif any(word in metric_lower for word in ['cost', 'expense', 'debt', 'loss']):
            if direction == "DECREASED":
                favorability = "favorable"
            elif direction == "INCREASED":
                favorability = "unfavorable"
            else:
                favorability = "neutral"
        else:
            favorability = "neutral"

        return (
            f"{metric}: {direction} from {from_period.label} to {to_period.label}\n"
            f"  {from_value.format()} -> {to_value.format()}\n"
            f"  Change: {change_value.format()}{pct_str}\n"
            f"  Assessment: [{favorability}]"
        )

    def enrich_evidence_nodes(
        self,
        nodes: List[EvidenceNode],
        xbrl_data: Optional[Dict[str, Dict[str, FinancialValue]]] = None
    ) -> List[EvidenceNode]:
        """
        Enrich evidence nodes with pre-computed changes.

        This is the main entry point for temporal enrichment.

        Args:
            nodes: List of evidence nodes to enrich
            xbrl_data: Optional XBRL data mapping metric -> period -> value

        Returns:
            Enriched nodes with computed_changes populated
        """
        # Group values by metric
        values_by_metric: Dict[str, Dict[FiscalPeriod, FinancialValue]] = {}

        for node in nodes:
            for value in node.values:
                # Try to determine metric from context
                metric_name = self._extract_metric_name(node.content)
                if metric_name:
                    if metric_name not in values_by_metric:
                        values_by_metric[metric_name] = {}
                    if value.period:
                        values_by_metric[metric_name][value.period] = value

        # Add XBRL data if provided
        if xbrl_data:
            for metric, period_values in xbrl_data.items():
                if metric not in values_by_metric:
                    values_by_metric[metric] = {}
                values_by_metric[metric].update(period_values)

        # Compute changes for each metric with 2+ periods
        all_changes: List[ComputedChange] = []

        for metric_name, period_values in values_by_metric.items():
            if len(period_values) < 2:
                continue

            # Sort periods chronologically
            sorted_periods = sorted(period_values.keys(), key=lambda p: p.sort_key)

            # Compute sequential changes
            for i in range(1, len(sorted_periods)):
                from_period = sorted_periods[i - 1]
                to_period = sorted_periods[i]
                from_value = period_values[from_period]
                to_value = period_values[to_period]

                change = self.compute_change(
                    metric_name=metric_name,
                    from_period=from_period,
                    to_period=to_period,
                    from_value=from_value,
                    to_value=to_value
                )
                all_changes.append(change)

        # Attach changes to relevant nodes
        for node in nodes:
            node_content_lower = node.content.lower()
            for change in all_changes:
                # Check if this node mentions this metric
                metric_lower = change.metric_name.lower()
                if metric_lower in node_content_lower:
                    if change not in node.computed_changes:
                        node.computed_changes.append(change)

        return nodes

    def _extract_metric_name(self, content: str) -> Optional[str]:
        """
        Extract metric name from content.
        """
        if not content:
            return None

        content_lower = content.lower()

        # Common financial metric patterns
        metrics = [
            ("total net sales", "Total Net Sales"),
            ("net sales", "Net Sales"),
            ("total revenue", "Total Revenue"),
            ("revenue", "Revenue"),
            ("gross profit", "Gross Profit"),
            ("gross margin", "Gross Margin"),
            ("operating income", "Operating Income"),
            ("operating margin", "Operating Margin"),
            ("net income", "Net Income"),
            ("net profit", "Net Profit"),
            ("earnings per share", "Earnings Per Share"),
            ("eps", "EPS"),
            ("iphone", "iPhone Revenue"),
            ("mac", "Mac Revenue"),
            ("ipad", "iPad Revenue"),
            ("services", "Services Revenue"),
            ("wearables", "Wearables Revenue"),
        ]

        for pattern, name in metrics:
            if pattern in content_lower:
                return name

        return None

    def format_evidence_for_llm(self, nodes: List[EvidenceNode]) -> str:
        """
        Format evidence for LLM consumption with pre-computed changes.

        CRITICAL: Includes pre-computed changes so LLM doesn't have to
        compute directions itself.
        """
        lines = []

        # Separate XBRL nodes (ground truth) from text nodes
        xbrl_nodes = [n for n in nodes if n.node_type == "xbrl" or n.xbrl_tag]
        text_nodes = [n for n in nodes if n.node_type == "text" and not n.xbrl_tag]

        # XBRL ground truth first
        if xbrl_nodes:
            lines.append("=== XBRL GROUND TRUTH (Verified) ===")
            for node in xbrl_nodes:
                lines.append(f"[XBRL] {node.content}")
                if node.values:
                    for value in node.values:
                        lines.append(f"  Value: {value.format()}")
            lines.append("")

        # Collect all computed changes
        all_changes = []
        for node in nodes:
            all_changes.extend(node.computed_changes)

        # Deduplicate changes
        seen_changes = set()
        unique_changes = []
        for change in all_changes:
            key = (change.metric_name, change.from_period, change.to_period)
            if key not in seen_changes:
                seen_changes.add(key)
                unique_changes.append(change)

        # Pre-computed changes (THE LLM SHOULD USE THESE, NOT COMPUTE ITS OWN)
        if unique_changes:
            lines.append("=== PRE-COMPUTED CHANGES (Use these, don't recompute) ===")
            for change in unique_changes:
                lines.append(change.format())
            lines.append("")

        # Supporting text
        if text_nodes:
            lines.append("=== SUPPORTING TEXT ===")
            for node in text_nodes[:10]:  # Limit to 10 text nodes
                content = node.content[:500] + "..." if len(node.content) > 500 else node.content
                lines.append(f"[{node.source_document}] {content}")

        return "\n".join(lines)


class XBRLGroundTruth:
    """
    XBRL data as ground truth for validation.
    """

    def __init__(self):
        self.data: Dict[str, Dict[str, Dict[str, FinancialValue]]] = {}
        # Structure: company -> metric -> period_label -> value

    def add_value(
        self,
        company: str,
        metric: str,
        period: FiscalPeriod,
        value: FinancialValue
    ):
        """Add a ground truth value."""
        if company not in self.data:
            self.data[company] = {}
        if metric not in self.data[company]:
            self.data[company][metric] = {}
        self.data[company][metric][period.label] = value

    def get_value(
        self,
        company: str,
        metric: str,
        period: FiscalPeriod
    ) -> Optional[FinancialValue]:
        """Get a ground truth value."""
        return (
            self.data
            .get(company, {})
            .get(metric, {})
            .get(period.label)
        )

    def validate_claim(
        self,
        company: str,
        metric: str,
        period: FiscalPeriod,
        claimed_value: FinancialValue,
        tolerance: float = 0.05
    ) -> Tuple[bool, Optional[FinancialValue], str]:
        """
        Validate a claimed value against XBRL ground truth.

        Args:
            company: Company ticker
            metric: Metric name
            period: Fiscal period
            claimed_value: The value being claimed
            tolerance: Acceptable difference as fraction (default 5%)

        Returns:
            Tuple of (is_valid, ground_truth_value, explanation)
        """
        ground_truth = self.get_value(company, metric, period)

        if ground_truth is None:
            return True, None, f"No ground truth available for {metric} in {period.label}"

        # Compare normalized amounts
        claimed_norm = claimed_value.normalized_amount
        truth_norm = ground_truth.normalized_amount

        if truth_norm != Decimal("0"):
            diff_pct = abs(float((claimed_norm - truth_norm) / truth_norm))
        else:
            diff_pct = float(abs(claimed_norm))

        is_valid = diff_pct <= tolerance

        if is_valid:
            explanation = (
                f"VALID: Claimed {claimed_value.format()} matches ground truth "
                f"{ground_truth.format()} within {tolerance*100:.0f}% tolerance"
            )
        else:
            explanation = (
                f"INVALID: Claimed {claimed_value.format()} differs from ground truth "
                f"{ground_truth.format()} by {diff_pct*100:.1f}%"
            )

        return is_valid, ground_truth, explanation


def create_temporal_intelligence(company: str = "AAPL") -> TemporalIntelligence:
    """
    Factory function to create temporal intelligence module.

    Args:
        company: Company ticker

    Returns:
        Configured TemporalIntelligence instance
    """
    return TemporalIntelligence(company=company)
