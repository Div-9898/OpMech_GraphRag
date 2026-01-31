"""
Apple Financial Ground Truth Data - DEPRECATED.

This module provides backwards compatibility.
New code should use DynamicFinancialLookup from company_ground_truth.py.

Usage for new code:
    from src.data.company_ground_truth import DynamicFinancialLookup
    lookup = DynamicFinancialLookup()
    lookup.load_from_xbrl_facts(xbrl_data)
"""

import warnings
from decimal import Decimal
from typing import Dict, Optional, Tuple

from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange

# Import the new company-agnostic module
from src.data.company_ground_truth import (
    DynamicFinancialLookup,
    get_financial_lookup,
    set_financial_lookup,
    STANDARD_METRICS,
)


def _emit_deprecation_warning():
    warnings.warn(
        "apple_ground_truth.py is deprecated. "
        "Use company_ground_truth.DynamicFinancialLookup instead for company-agnostic support.",
        DeprecationWarning,
        stacklevel=3
    )


# XBRL-verified Apple financial data (kept for backwards compatibility)
# New code should load data dynamically from SEC XBRL API
APPLE_FINANCIALS: Dict[str, Dict[str, Decimal]] = {
    # Total Net Sales (Revenue)
    "net_sales": {
        "FY2024": Decimal("391035000000"),
        "FY2023": Decimal("383285000000"),
        "FY2022": Decimal("394328000000"),
        "FY2021": Decimal("365817000000"),
        "FY2020": Decimal("274515000000"),
    },
    "iphone_revenue": {
        "FY2024": Decimal("201183000000"),
        "FY2023": Decimal("200583000000"),
        "FY2022": Decimal("205489000000"),
        "FY2021": Decimal("191973000000"),
        "FY2020": Decimal("137781000000"),
    },
    "services_revenue": {
        "FY2024": Decimal("96169000000"),
        "FY2023": Decimal("85200000000"),
        "FY2022": Decimal("78129000000"),
        "FY2021": Decimal("68425000000"),
        "FY2020": Decimal("53768000000"),
    },
    "mac_revenue": {
        "FY2024": Decimal("29984000000"),
        "FY2023": Decimal("29357000000"),
        "FY2022": Decimal("40177000000"),
        "FY2021": Decimal("35190000000"),
        "FY2020": Decimal("28622000000"),
    },
    "ipad_revenue": {
        "FY2024": Decimal("26694000000"),
        "FY2023": Decimal("28300000000"),
        "FY2022": Decimal("29292000000"),
        "FY2021": Decimal("31862000000"),
        "FY2020": Decimal("23724000000"),
    },
    "wearables_revenue": {
        "FY2024": Decimal("37005000000"),
        "FY2023": Decimal("39845000000"),
        "FY2022": Decimal("41241000000"),
        "FY2021": Decimal("38367000000"),
        "FY2020": Decimal("30620000000"),
    },
    "gross_profit": {
        "FY2024": Decimal("180683000000"),
        "FY2023": Decimal("169148000000"),
        "FY2022": Decimal("170782000000"),
        "FY2021": Decimal("152836000000"),
        "FY2020": Decimal("104956000000"),
    },
    "operating_income": {
        "FY2024": Decimal("123216000000"),
        "FY2023": Decimal("114301000000"),
        "FY2022": Decimal("119437000000"),
        "FY2021": Decimal("108949000000"),
        "FY2020": Decimal("66288000000"),
    },
    "net_income": {
        "FY2024": Decimal("93736000000"),
        "FY2023": Decimal("96995000000"),
        "FY2022": Decimal("99803000000"),
        "FY2021": Decimal("94680000000"),
        "FY2020": Decimal("57411000000"),
    },
    "cost_of_sales": {
        "FY2024": Decimal("210352000000"),
        "FY2023": Decimal("214137000000"),
        "FY2022": Decimal("223546000000"),
        "FY2021": Decimal("212981000000"),
        "FY2020": Decimal("169559000000"),
    },
    "gross_margin_pct": {
        "FY2024": Decimal("46.21"),
        "FY2023": Decimal("44.13"),
        "FY2022": Decimal("43.31"),
        "FY2021": Decimal("41.78"),
        "FY2020": Decimal("38.23"),
    },
    "eps_diluted": {
        "FY2024": Decimal("6.08"),
        "FY2023": Decimal("6.13"),
        "FY2022": Decimal("6.11"),
        "FY2021": Decimal("5.61"),
        "FY2020": Decimal("3.28"),
    },
    "research_and_development": {
        "FY2024": Decimal("31370000000"),
        "FY2023": Decimal("29915000000"),
        "FY2022": Decimal("26251000000"),
        "FY2021": Decimal("21914000000"),
        "FY2020": Decimal("18752000000"),
    },
    "selling_general_admin": {
        "FY2024": Decimal("26097000000"),
        "FY2023": Decimal("24932000000"),
        "FY2022": Decimal("25094000000"),
        "FY2021": Decimal("21973000000"),
        "FY2020": Decimal("19916000000"),
    },
    "total_assets": {
        "FY2024": Decimal("364980000000"),
        "FY2023": Decimal("352583000000"),
        "FY2022": Decimal("352755000000"),
        "FY2021": Decimal("351002000000"),
        "FY2020": Decimal("323888000000"),
    },
    "cash_and_equivalents": {
        "FY2024": Decimal("29943000000"),
        "FY2023": Decimal("29965000000"),
        "FY2022": Decimal("23646000000"),
        "FY2021": Decimal("34940000000"),
        "FY2020": Decimal("38016000000"),
    },
    "long_term_debt": {
        "FY2024": Decimal("85750000000"),
        "FY2023": Decimal("95281000000"),
        "FY2022": Decimal("98959000000"),
        "FY2021": Decimal("109106000000"),
        "FY2020": Decimal("98667000000"),
    },
    "dividends_per_share": {
        "FY2024": Decimal("0.99"),
        "FY2023": Decimal("0.96"),
        "FY2022": Decimal("0.91"),
        "FY2021": Decimal("0.85"),
        "FY2020": Decimal("0.80"),
    },
}


class AppleFinancialLookup:
    """
    Lookup service for Apple financial data.
    DEPRECATED: Use DynamicFinancialLookup for company-agnostic support.
    """

    METRIC_ALIASES = {
        "revenue": "net_sales",
        "total revenue": "net_sales",
        "net sales": "net_sales",
        "total net sales": "net_sales",
        "sales": "net_sales",
        "total sales": "net_sales",
        "iphone": "iphone_revenue",
        "iphone sales": "iphone_revenue",
        "iphone revenue": "iphone_revenue",
        "services": "services_revenue",
        "services revenue": "services_revenue",
        "service revenue": "services_revenue",
        "service": "services_revenue",
        "mac": "mac_revenue",
        "mac revenue": "mac_revenue",
        "mac sales": "mac_revenue",
        "ipad": "ipad_revenue",
        "ipad revenue": "ipad_revenue",
        "ipad sales": "ipad_revenue",
        "wearables": "wearables_revenue",
        "wearables revenue": "wearables_revenue",
        "accessories": "wearables_revenue",
        "wearables home and accessories": "wearables_revenue",
        "wearables, home and accessories": "wearables_revenue",
        "watch": "wearables_revenue",
        "airpods": "wearables_revenue",
        "gross profit": "gross_profit",
        "operating income": "operating_income",
        "operating profit": "operating_income",
        "net income": "net_income",
        "net profit": "net_income",
        "profit": "net_income",
        "earnings": "net_income",
        "cost of sales": "cost_of_sales",
        "cogs": "cost_of_sales",
        "cost of revenue": "cost_of_sales",
        "cost of goods sold": "cost_of_sales",
        "gross margin": "gross_margin_pct",
        "gross margin %": "gross_margin_pct",
        "gross margin percent": "gross_margin_pct",
        "eps": "eps_diluted",
        "eps diluted": "eps_diluted",
        "earnings per share": "eps_diluted",
        "diluted eps": "eps_diluted",
        "r&d": "research_and_development",
        "rd": "research_and_development",
        "research and development": "research_and_development",
        "research & development": "research_and_development",
        "sg&a": "selling_general_admin",
        "sga": "selling_general_admin",
        "selling general and administrative": "selling_general_admin",
        "assets": "total_assets",
        "total assets": "total_assets",
        "cash": "cash_and_equivalents",
        "cash and equivalents": "cash_and_equivalents",
        "debt": "long_term_debt",
        "long term debt": "long_term_debt",
        "long-term debt": "long_term_debt",
        "dividend": "dividends_per_share",
        "dividends": "dividends_per_share",
        "dividends per share": "dividends_per_share",
        "dps": "dividends_per_share",
    }

    @classmethod
    def resolve_metric(cls, name: str) -> Optional[str]:
        """Resolve metric alias to canonical name"""
        name_lower = name.lower().strip()
        return cls.METRIC_ALIASES.get(name_lower, name_lower)

    @classmethod
    def get_value(cls, metric: str, period: FiscalPeriod) -> Optional[FinancialValue]:
        """Get XBRL-verified value for a metric and period."""
        _emit_deprecation_warning()
        canonical_metric = cls.resolve_metric(metric)
        if canonical_metric not in APPLE_FINANCIALS:
            return None
        period_key = period.label
        metric_data = APPLE_FINANCIALS[canonical_metric]
        if period_key not in metric_data:
            return None
        amount = metric_data[period_key]
        return FinancialValue(amount=amount, period=period, source="XBRL", confidence=1.0)

    @classmethod
    def get_change(cls, metric: str, from_period: FiscalPeriod, to_period: FiscalPeriod) -> Optional[FinancialChange]:
        """Get pre-computed change between two periods."""
        _emit_deprecation_warning()
        from_value = cls.get_value(metric, from_period)
        to_value = cls.get_value(metric, to_period)
        if from_value is None or to_value is None:
            return None
        return FinancialChange(
            metric_name=metric,
            from_period=from_period,
            to_period=to_period,
            from_value=from_value,
            to_value=to_value
        )

    @classmethod
    def validate_claim(cls, metric: str, period: FiscalPeriod, claimed_value: FinancialValue, tolerance: float = 0.01) -> Tuple[bool, Optional[FinancialValue], str]:
        """Validate a claimed value against ground truth."""
        _emit_deprecation_warning()
        ground_truth = cls.get_value(metric, period)
        if ground_truth is None:
            return True, None, "No ground truth available for validation"
        if ground_truth.amount == 0:
            is_valid = claimed_value.amount == 0
            return is_valid, ground_truth, "Zero comparison"
        relative_error = abs(float(claimed_value.amount - ground_truth.amount) / float(ground_truth.amount))
        if relative_error <= tolerance:
            return True, ground_truth, f"Validated (error: {relative_error:.2%})"
        else:
            return False, ground_truth, f"MISMATCH: Claimed {claimed_value.format()}, actual {ground_truth.format()} (error: {relative_error:.2%})"

    @classmethod
    def validate_direction_claim(cls, metric: str, from_period: FiscalPeriod, to_period: FiscalPeriod, claimed_direction: str) -> Tuple[bool, Optional[str], str]:
        """Validate a direction claim."""
        _emit_deprecation_warning()
        change = cls.get_change(metric, from_period, to_period)
        if change is None:
            return True, None, "No ground truth available for direction validation"
        actual_direction = change.direction
        claimed_upper = claimed_direction.upper().strip()
        if claimed_upper in ['INCREASE', 'INCREASED', 'GREW', 'ROSE', 'UP']:
            claimed_normalized = "INCREASE"
        elif claimed_upper in ['DECREASE', 'DECREASED', 'DECLINED', 'FELL', 'DOWN']:
            claimed_normalized = "DECREASE"
        elif claimed_upper in ['UNCHANGED', 'STABLE', 'FLAT', 'NO CHANGE']:
            claimed_normalized = "UNCHANGED"
        else:
            claimed_normalized = claimed_upper
        if claimed_normalized == actual_direction:
            return True, actual_direction, f"Direction validated: {actual_direction}"
        else:
            return False, actual_direction, f"Direction MISMATCH: Claimed {claimed_normalized}, actual {actual_direction} ({change.format_concise()})"

    @classmethod
    def get_all_metrics(cls) -> list:
        """Get all available metrics"""
        _emit_deprecation_warning()
        return list(APPLE_FINANCIALS.keys())

    @classmethod
    def get_available_periods(cls, metric: str) -> list:
        """Get all available periods for a metric"""
        _emit_deprecation_warning()
        canonical_metric = cls.resolve_metric(metric)
        if canonical_metric not in APPLE_FINANCIALS:
            return []
        return list(APPLE_FINANCIALS[canonical_metric].keys())

    @classmethod
    def get_segment_metrics(cls) -> list:
        """Get all product segment metrics"""
        _emit_deprecation_warning()
        return ["iphone_revenue", "services_revenue", "mac_revenue", "ipad_revenue", "wearables_revenue"]

    @classmethod
    def get_full_segment_breakdown(cls, period: FiscalPeriod) -> Dict[str, FinancialValue]:
        """Get full segment breakdown for a period"""
        _emit_deprecation_warning()
        segments = {}
        for segment in cls.get_segment_metrics():
            value = cls.get_value(segment, period)
            if value:
                segments[segment] = value
        return segments
