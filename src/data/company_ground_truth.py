"""
Company-Agnostic Financial Ground Truth Module.

Extracts ground truth values from XBRL documents at runtime.
Replaces hardcoded Apple-specific values.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange
from src.company_config import CompanyConfig, get_active_company


@dataclass
class MetricDefinition:
    """Definition of a financial metric with XBRL mappings."""

    canonical_name: str
    xbrl_tags: List[str]  # Possible XBRL tags for this metric
    aliases: List[str]  # Human-readable aliases
    unit: str = "USD"  # Default unit
    is_percentage: bool = False


# Standard financial metrics with their XBRL tag mappings
# These work across all companies that use US-GAAP
STANDARD_METRICS: Dict[str, MetricDefinition] = {
    # Revenue metrics
    "net_sales": MetricDefinition(
        canonical_name="net_sales",
        xbrl_tags=[
            "us-gaap:Revenues",
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:SalesRevenueNet",
            "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
        ],
        aliases=["revenue", "total revenue", "net sales", "total net sales", "sales", "total sales"],
    ),

    # Profit metrics
    "gross_profit": MetricDefinition(
        canonical_name="gross_profit",
        xbrl_tags=["us-gaap:GrossProfit"],
        aliases=["gross profit", "gross margin dollars"],
    ),
    "operating_income": MetricDefinition(
        canonical_name="operating_income",
        xbrl_tags=[
            "us-gaap:OperatingIncomeLoss",
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ],
        aliases=["operating income", "operating profit", "income from operations"],
    ),
    "net_income": MetricDefinition(
        canonical_name="net_income",
        xbrl_tags=[
            "us-gaap:NetIncomeLoss",
            "us-gaap:ProfitLoss",
        ],
        aliases=["net income", "net profit", "profit", "earnings", "net earnings"],
    ),

    # Cost metrics
    "cost_of_sales": MetricDefinition(
        canonical_name="cost_of_sales",
        xbrl_tags=[
            "us-gaap:CostOfGoodsAndServicesSold",
            "us-gaap:CostOfRevenue",
            "us-gaap:CostOfGoodsSold",
        ],
        aliases=["cost of sales", "cogs", "cost of revenue", "cost of goods sold"],
    ),
    "research_and_development": MetricDefinition(
        canonical_name="research_and_development",
        xbrl_tags=["us-gaap:ResearchAndDevelopmentExpense"],
        aliases=["r&d", "rd", "research and development", "research & development"],
    ),
    "selling_general_admin": MetricDefinition(
        canonical_name="selling_general_admin",
        xbrl_tags=[
            "us-gaap:SellingGeneralAndAdministrativeExpense",
            "us-gaap:GeneralAndAdministrativeExpense",
        ],
        aliases=["sg&a", "sga", "selling general and administrative"],
    ),

    # Balance sheet metrics
    "total_assets": MetricDefinition(
        canonical_name="total_assets",
        xbrl_tags=["us-gaap:Assets"],
        aliases=["assets", "total assets"],
    ),
    "cash_and_equivalents": MetricDefinition(
        canonical_name="cash_and_equivalents",
        xbrl_tags=[
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:Cash",
        ],
        aliases=["cash", "cash and equivalents", "cash and cash equivalents"],
    ),
    "long_term_debt": MetricDefinition(
        canonical_name="long_term_debt",
        xbrl_tags=[
            "us-gaap:LongTermDebt",
            "us-gaap:LongTermDebtNoncurrent",
        ],
        aliases=["debt", "long term debt", "long-term debt"],
    ),
    "total_liabilities": MetricDefinition(
        canonical_name="total_liabilities",
        xbrl_tags=["us-gaap:Liabilities"],
        aliases=["liabilities", "total liabilities"],
    ),
    "stockholders_equity": MetricDefinition(
        canonical_name="stockholders_equity",
        xbrl_tags=[
            "us-gaap:StockholdersEquity",
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        aliases=["equity", "stockholders equity", "shareholders equity"],
    ),

    # Per-share metrics
    "eps_diluted": MetricDefinition(
        canonical_name="eps_diluted",
        xbrl_tags=["us-gaap:EarningsPerShareDiluted"],
        aliases=["eps", "eps diluted", "earnings per share", "diluted eps"],
        unit="USD/share",
    ),
    "eps_basic": MetricDefinition(
        canonical_name="eps_basic",
        xbrl_tags=["us-gaap:EarningsPerShareBasic"],
        aliases=["basic eps", "eps basic"],
        unit="USD/share",
    ),
    "dividends_per_share": MetricDefinition(
        canonical_name="dividends_per_share",
        xbrl_tags=["us-gaap:CommonStockDividendsPerShareDeclared"],
        aliases=["dividend", "dividends", "dividends per share", "dps"],
        unit="USD/share",
    ),

    # Margin metrics (percentages)
    "gross_margin_pct": MetricDefinition(
        canonical_name="gross_margin_pct",
        xbrl_tags=[],  # Usually computed, not directly in XBRL
        aliases=["gross margin", "gross margin %", "gross margin percent"],
        is_percentage=True,
    ),
}


class DynamicFinancialLookup:
    """
    Dynamic financial lookup that extracts values from XBRL documents.

    COMPANY-AGNOSTIC: Works with any company's filings.
    """

    def __init__(self, company_config: Optional[CompanyConfig] = None):
        """
        Initialize the lookup service.

        Args:
            company_config: Company configuration. Uses active company if not provided.
        """
        self._company_config = company_config
        self._extracted_data: Dict[str, Dict[str, Decimal]] = {}
        self._data_loaded = False

    @property
    def company_config(self) -> Optional[CompanyConfig]:
        """Get the company configuration."""
        if self._company_config:
            return self._company_config
        return get_active_company()

    def load_from_xbrl_facts(self, xbrl_facts: dict) -> None:
        """
        Load financial data from SEC XBRL company facts.

        Args:
            xbrl_facts: Response from SEC's companyfacts API endpoint
        """
        facts = xbrl_facts.get("facts", {})
        us_gaap = facts.get("us-gaap", {})

        for metric_name, metric_def in STANDARD_METRICS.items():
            self._extracted_data[metric_name] = {}

            for xbrl_tag in metric_def.xbrl_tags:
                # Remove namespace prefix for lookup
                tag_name = xbrl_tag.split(":")[-1]

                if tag_name in us_gaap:
                    tag_data = us_gaap[tag_name]
                    units = tag_data.get("units", {})

                    # Get USD values (or shares for per-share metrics)
                    values = units.get("USD", units.get("USD/shares", []))

                    for entry in values:
                        # Only use annual (10-K) values with fiscal year frame
                        frame = entry.get("frame", "")
                        if not frame.startswith("CY"):
                            continue

                        # Extract fiscal year from frame (e.g., "CY2023" -> FY2023)
                        try:
                            year = int(frame[2:6])
                            period_key = f"FY{year}"

                            # Prefer entries without 'Q' (annual values)
                            if "Q" not in frame:
                                value = Decimal(str(entry.get("val", 0)))
                                self._extracted_data[metric_name][period_key] = value
                        except (ValueError, IndexError):
                            continue

                    # If we found data, don't try other tags
                    if self._extracted_data[metric_name]:
                        break

        self._data_loaded = True
        logger.info(f"Loaded {len([m for m in self._extracted_data if self._extracted_data[m]])} metrics from XBRL")

    def load_from_nodes(self, nodes: List[Dict]) -> None:
        """
        Load financial data from parsed document nodes.

        Args:
            nodes: List of parsed XBRL/document nodes
        """
        for node in nodes:
            xbrl_tag = node.get("xbrl_tag", "")
            if not xbrl_tag:
                continue

            value = node.get("value")
            if value is None:
                continue

            period = node.get("period", node.get("metadata", {}).get("period", ""))
            if not period:
                continue

            # Find matching metric
            for metric_name, metric_def in STANDARD_METRICS.items():
                if xbrl_tag in metric_def.xbrl_tags:
                    if metric_name not in self._extracted_data:
                        self._extracted_data[metric_name] = {}
                    self._extracted_data[metric_name][period] = Decimal(str(value))
                    break

        self._data_loaded = True

    @classmethod
    def resolve_metric(cls, name: str) -> Optional[str]:
        """Resolve metric alias to canonical name."""
        name_lower = name.lower().strip()

        # Direct lookup
        if name_lower in STANDARD_METRICS:
            return name_lower

        # Search aliases
        for metric_name, metric_def in STANDARD_METRICS.items():
            if name_lower in metric_def.aliases:
                return metric_name

        return None

    def get_value(
        self,
        metric: str,
        period: FiscalPeriod
    ) -> Optional[FinancialValue]:
        """
        Get value for a metric and period.

        Args:
            metric: Metric name or alias
            period: Fiscal period

        Returns:
            FinancialValue if found, None otherwise
        """
        canonical_metric = self.resolve_metric(metric)
        if not canonical_metric:
            return None

        if canonical_metric not in self._extracted_data:
            return None

        period_key = period.label
        metric_data = self._extracted_data[canonical_metric]

        if period_key not in metric_data:
            return None

        amount = metric_data[period_key]
        metric_def = STANDARD_METRICS.get(canonical_metric)

        return FinancialValue(
            amount=amount,
            period=period,
            source="XBRL",
            confidence=1.0
        )

    def get_change(
        self,
        metric: str,
        from_period: FiscalPeriod,
        to_period: FiscalPeriod
    ) -> Optional[FinancialChange]:
        """
        Get pre-computed change between two periods.

        Args:
            metric: Metric name or alias
            from_period: Starting period
            to_period: Ending period

        Returns:
            FinancialChange if both values found, None otherwise
        """
        from_value = self.get_value(metric, from_period)
        to_value = self.get_value(metric, to_period)

        if from_value is None or to_value is None:
            return None

        return FinancialChange(
            metric_name=metric,
            from_period=from_period,
            to_period=to_period,
            from_value=from_value,
            to_value=to_value
        )

    def validate_claim(
        self,
        metric: str,
        period: FiscalPeriod,
        claimed_value: FinancialValue,
        tolerance: float = 0.01
    ) -> Tuple[bool, Optional[FinancialValue], str]:
        """
        Validate a claimed value against extracted ground truth.

        Args:
            metric: Metric name
            period: Fiscal period
            claimed_value: Value to validate
            tolerance: Acceptable relative error (default 1%)

        Returns:
            (is_valid, ground_truth, message)
        """
        ground_truth = self.get_value(metric, period)

        if ground_truth is None:
            return True, None, "No ground truth available for validation"

        if ground_truth.amount == 0:
            is_valid = claimed_value.amount == 0
            return is_valid, ground_truth, "Zero comparison"

        relative_error = abs(
            float(claimed_value.amount - ground_truth.amount) / float(ground_truth.amount)
        )

        if relative_error <= tolerance:
            return True, ground_truth, f"Validated (error: {relative_error:.2%})"
        else:
            return False, ground_truth, (
                f"MISMATCH: Claimed {claimed_value.format()}, "
                f"actual {ground_truth.format()} (error: {relative_error:.2%})"
            )

    def validate_direction_claim(
        self,
        metric: str,
        from_period: FiscalPeriod,
        to_period: FiscalPeriod,
        claimed_direction: str
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validate a direction claim (INCREASE/DECREASE/UNCHANGED).

        Args:
            metric: Metric name
            from_period: Starting period
            to_period: Ending period
            claimed_direction: Claimed direction

        Returns:
            (is_valid, actual_direction, message)
        """
        change = self.get_change(metric, from_period, to_period)

        if change is None:
            return True, None, "No ground truth available for direction validation"

        actual_direction = change.direction
        claimed_upper = claimed_direction.upper().strip()

        # Normalize claimed direction
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
            return False, actual_direction, (
                f"Direction MISMATCH: Claimed {claimed_normalized}, "
                f"actual {actual_direction} ({change.format_concise()})"
            )

    def get_all_metrics(self) -> List[str]:
        """Get all available metrics."""
        return [m for m in self._extracted_data if self._extracted_data[m]]

    def get_available_periods(self, metric: str) -> List[str]:
        """Get all available periods for a metric."""
        canonical_metric = self.resolve_metric(metric)
        if not canonical_metric or canonical_metric not in self._extracted_data:
            return []
        return list(self._extracted_data[canonical_metric].keys())

    def get_segment_metrics(self) -> List[str]:
        """Get all segment revenue metrics (company-specific, extracted from docs)."""
        # These would be populated from company-specific segment tags
        return [m for m in self._extracted_data if "segment" in m.lower() or "revenue" in m.lower()]

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """Export extracted data as dictionary."""
        return {
            metric: {period: str(value) for period, value in periods.items()}
            for metric, periods in self._extracted_data.items()
        }


# Global instance for backwards compatibility
_global_lookup: Optional[DynamicFinancialLookup] = None


def get_financial_lookup() -> DynamicFinancialLookup:
    """Get or create the global financial lookup instance."""
    global _global_lookup
    if _global_lookup is None:
        _global_lookup = DynamicFinancialLookup()
    return _global_lookup


def set_financial_lookup(lookup: DynamicFinancialLookup) -> None:
    """Set the global financial lookup instance."""
    global _global_lookup
    _global_lookup = lookup
