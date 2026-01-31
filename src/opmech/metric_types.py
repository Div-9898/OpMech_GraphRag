"""
Financial metric type definitions and handling.

Different metrics require different change calculations:
- Absolute values (revenue): Dollar change + percentage change
- Percentages (margins): Percentage POINT change
- Ratios (P/E): Ratio difference
- Counts (employees): Absolute + percentage change

This module provides type detection and appropriate change calculations.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
import re


class MetricType(Enum):
    """Types of financial metrics."""
    ABSOLUTE = "absolute"      # Dollar amounts
    PERCENTAGE = "percentage"  # Percentage values (margins, rates)
    RATIO = "ratio"           # Financial ratios
    COUNT = "count"           # Counts (employees, stores)
    UNKNOWN = "unknown"


class ChangeDirection(Enum):
    """Direction of change."""
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    UNCHANGED = "UNCHANGED"


class GoodDirection(Enum):
    """What direction is typically 'good' for a metric."""
    INCREASE = "increase"   # Revenue, profit - higher is better
    DECREASE = "decrease"   # Costs, debt - lower is better
    NEUTRAL = "neutral"     # Depends on context


@dataclass
class MetricConfig:
    """Configuration for a specific metric type."""
    metric_type: MetricType
    unit: str
    good_direction: GoodDirection
    display_precision: int = 2

    # For absolute values, thresholds for B/M/K formatting
    billion_threshold: float = 1e9
    million_threshold: float = 1e6


# XBRL tag patterns to metric configurations
XBRL_METRIC_CONFIGS: Dict[str, MetricConfig] = {
    # Revenue and Sales (INCREASE = good)
    'Revenue': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'Revenues': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'NetSales': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'SalesRevenueNet': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'RevenueFromContractWithCustomer': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),

    # Profit metrics (INCREASE = good)
    'GrossProfit': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'OperatingIncome': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'OperatingIncomeLoss': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'NetIncome': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'NetIncomeLoss': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'ProfitLoss': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'EarningsPerShare': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE, display_precision=2),

    # Cost metrics (DECREASE = good)
    'CostOfRevenue': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'CostOfGoodsSold': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'CostOfGoodsAndServicesSold': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'OperatingExpenses': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'ResearchAndDevelopmentExpense': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.NEUTRAL),
    'SellingGeneralAndAdministrativeExpense': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'InterestExpense': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),

    # Debt and Liabilities (DECREASE = good typically)
    'LongTermDebt': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'TotalDebt': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE),
    'Liabilities': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.NEUTRAL),

    # Assets and Equity (INCREASE = good typically)
    'Assets': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'TotalAssets': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'StockholdersEquity': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),
    'CashAndCashEquivalents': MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE),

    # Margin percentages (INCREASE = good)
    'GrossMargin': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),
    'GrossProfitMargin': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),
    'OperatingMargin': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),
    'NetProfitMargin': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),
    'ProfitMargin': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),

    # Rate percentages (context-dependent)
    'EffectiveTaxRate': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.DECREASE),
    'InterestRate': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.NEUTRAL),

    # Financial ratios
    'PriceEarningsRatio': MetricConfig(MetricType.RATIO, 'x', GoodDirection.NEUTRAL),
    'DebtToEquityRatio': MetricConfig(MetricType.RATIO, 'x', GoodDirection.DECREASE),
    'CurrentRatio': MetricConfig(MetricType.RATIO, 'x', GoodDirection.INCREASE),
    'QuickRatio': MetricConfig(MetricType.RATIO, 'x', GoodDirection.INCREASE),
    'ReturnOnEquity': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),
    'ReturnOnAssets': MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE),

    # Counts
    'NumberOfEmployees': MetricConfig(MetricType.COUNT, 'employees', GoodDirection.NEUTRAL),
    'CommonStockSharesOutstanding': MetricConfig(MetricType.COUNT, 'shares', GoodDirection.NEUTRAL),
}

# Content patterns for metric type detection
CONTENT_PATTERNS = {
    MetricType.PERCENTAGE: [
        r'\d+\.?\d*\s*%',           # "45.2%"
        r'margin',                   # "gross margin"
        r'rate',                     # "tax rate"
        r'percentage',               # "percentage of"
        r'percent',                  # "percent"
    ],
    MetricType.RATIO: [
        r'\d+\.?\d*\s*x',           # "15.2x"
        r'ratio',                    # "debt ratio"
        r'multiple',                 # "earnings multiple"
        r'times',                    # "5 times"
    ],
    MetricType.COUNT: [
        r'employees',
        r'stores',
        r'locations',
        r'units',
        r'shares outstanding',
        r'headcount',
    ],
}


def get_metric_config(xbrl_tag: Optional[str] = None, content: Optional[str] = None) -> MetricConfig:
    """
    Get metric configuration from XBRL tag or content analysis.

    Args:
        xbrl_tag: XBRL tag like 'us-gaap:Revenues'
        content: Text content describing the metric

    Returns:
        MetricConfig for the detected metric type
    """
    # Try XBRL tag first (most reliable)
    if xbrl_tag:
        # Extract the concept name from full tag
        concept = xbrl_tag.split(':')[-1] if ':' in xbrl_tag else xbrl_tag

        # Check exact match
        if concept in XBRL_METRIC_CONFIGS:
            return XBRL_METRIC_CONFIGS[concept]

        # Check partial match
        for key, config in XBRL_METRIC_CONFIGS.items():
            if key.lower() in concept.lower() or concept.lower() in key.lower():
                return config

    # Fall back to content analysis
    if content:
        content_lower = content.lower()

        # Check percentage patterns
        for pattern in CONTENT_PATTERNS[MetricType.PERCENTAGE]:
            if re.search(pattern, content_lower):
                # Determine if it's a margin (good = increase) or rate (depends)
                if 'margin' in content_lower or 'profit' in content_lower:
                    return MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.INCREASE)
                elif 'tax' in content_lower:
                    return MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.DECREASE)
                else:
                    return MetricConfig(MetricType.PERCENTAGE, '%', GoodDirection.NEUTRAL)

        # Check ratio patterns
        for pattern in CONTENT_PATTERNS[MetricType.RATIO]:
            if re.search(pattern, content_lower):
                return MetricConfig(MetricType.RATIO, 'x', GoodDirection.NEUTRAL)

        # Check count patterns
        for pattern in CONTENT_PATTERNS[MetricType.COUNT]:
            if re.search(pattern, content_lower):
                return MetricConfig(MetricType.COUNT, 'units', GoodDirection.NEUTRAL)

        # Check for revenue/profit/cost keywords
        if any(word in content_lower for word in ['revenue', 'sales', 'income', 'profit']):
            return MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.INCREASE)
        elif any(word in content_lower for word in ['cost', 'expense', 'debt']):
            return MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.DECREASE)

    # Default to absolute with neutral direction
    return MetricConfig(MetricType.ABSOLUTE, 'USD', GoodDirection.NEUTRAL)


@dataclass
class ChangeResult:
    """Result of a change calculation."""
    direction: ChangeDirection
    absolute_change: float
    percentage_change: Optional[float]  # None for ratios
    formatted_change: str
    from_value: float
    to_value: float
    from_period: str
    to_period: str
    is_favorable: Optional[bool]  # Based on good_direction


def compute_change(
    from_value: float,
    to_value: float,
    from_period: str,
    to_period: str,
    config: MetricConfig,
) -> ChangeResult:
    """
    Compute change between two values based on metric type.

    Args:
        from_value: Earlier period value
        to_value: Later period value
        from_period: Label for earlier period (e.g., 'FY2022')
        to_period: Label for later period (e.g., 'FY2023')
        config: Metric configuration

    Returns:
        ChangeResult with all change details
    """
    absolute_change = to_value - from_value

    # Determine direction
    if absolute_change > 0:
        direction = ChangeDirection.INCREASE
    elif absolute_change < 0:
        direction = ChangeDirection.DECREASE
    else:
        direction = ChangeDirection.UNCHANGED

    # Calculate percentage change (if applicable)
    if config.metric_type == MetricType.RATIO:
        percentage_change = None
    elif from_value != 0:
        percentage_change = (absolute_change / abs(from_value)) * 100
    else:
        percentage_change = None

    # Format the change based on metric type
    formatted_change = _format_change(
        absolute_change,
        percentage_change,
        config,
        direction
    )

    # Determine if change is favorable
    is_favorable = None
    if config.good_direction == GoodDirection.INCREASE:
        is_favorable = direction == ChangeDirection.INCREASE
    elif config.good_direction == GoodDirection.DECREASE:
        is_favorable = direction == ChangeDirection.DECREASE

    return ChangeResult(
        direction=direction,
        absolute_change=absolute_change,
        percentage_change=percentage_change,
        formatted_change=formatted_change,
        from_value=from_value,
        to_value=to_value,
        from_period=from_period,
        to_period=to_period,
        is_favorable=is_favorable,
    )


def _format_change(
    absolute_change: float,
    percentage_change: Optional[float],
    config: MetricConfig,
    direction: ChangeDirection,
) -> str:
    """Format the change for display."""

    direction_str = direction.value
    abs_change = abs(absolute_change)

    if config.metric_type == MetricType.PERCENTAGE:
        # For percentages, show percentage point change
        return f"{direction_str} of {abs_change:.1f} percentage points"

    elif config.metric_type == MetricType.RATIO:
        # For ratios, show the difference
        return f"{direction_str} of {abs_change:.2f}x"

    elif config.metric_type == MetricType.COUNT:
        # For counts, show absolute and percentage
        if percentage_change is not None:
            return f"{direction_str} of {abs_change:,.0f} {config.unit} ({percentage_change:+.1f}%)"
        else:
            return f"{direction_str} of {abs_change:,.0f} {config.unit}"

    else:  # ABSOLUTE (dollar amounts)
        # Format with B/M/K suffix
        if abs_change >= config.billion_threshold:
            formatted_abs = f"${abs_change / 1e9:.2f}B"
        elif abs_change >= config.million_threshold:
            formatted_abs = f"${abs_change / 1e6:.2f}M"
        else:
            formatted_abs = f"${abs_change:,.0f}"

        if percentage_change is not None:
            return f"{direction_str} of {formatted_abs} ({percentage_change:+.1f}%)"
        else:
            return f"{direction_str} of {formatted_abs}"


def format_value(value: float, config: MetricConfig) -> str:
    """Format a single value based on metric type."""

    if config.metric_type == MetricType.PERCENTAGE:
        return f"{value:.1f}%"

    elif config.metric_type == MetricType.RATIO:
        return f"{value:.2f}x"

    elif config.metric_type == MetricType.COUNT:
        return f"{value:,.0f}"

    else:  # ABSOLUTE
        if abs(value) >= config.billion_threshold:
            return f"${value / 1e9:.2f}B"
        elif abs(value) >= config.million_threshold:
            return f"${value / 1e6:.2f}M"
        else:
            return f"${value:,.0f}"
