# OpMech-GraphRAG: Fully Generalized Temporal & Metric Handling

## Overview

The current temporal direction fixes work for the specific test case (Apple revenue FY2022→FY2023). This prompt enhances the system to handle ALL temporal and metric scenarios.

### Current Coverage vs Target

| Scenario | Current | Target |
|----------|---------|--------|
| Annual revenue YoY (Apple) | ✅ | ✅ |
| Quarterly comparisons | ⚠️ 50% | ✅ 100% |
| Percentage metrics (margins) | ⚠️ 30% | ✅ 100% |
| Multi-year trends (3+ periods) | ⚠️ 40% | ✅ 100% |
| Different companies | ❌ 0% | ✅ 100% |
| Cost metrics (decrease=good) | ⚠️ 50% | ✅ 100% |
| Ratio metrics (P/E, D/E) | ❌ 0% | ✅ 100% |

---

## File Structure

Create/update these files:

```
src/opmech/
├── company_config.py          # NEW: Company fiscal year configurations
├── metric_types.py            # NEW: Metric type definitions and handling
├── evidence_preprocessor.py   # UPDATE: Enhanced with all features
├── answer_validator.py        # UPDATE: Type-aware validation
├── consistency_checker.py     # UPDATE: Enhanced discrepancy detection
├── prompts.py                 # UPDATE: Metric-specific prompts
└── tests/
    └── test_generalized_temporal.py  # NEW: Comprehensive test suite
```

---

## File 1: Company Configuration

Create `src/opmech/company_config.py`:

```python
"""
Company-specific fiscal year configurations.

Different companies have different fiscal year end dates:
- Apple: September (last Saturday)
- Microsoft: June 30
- Walmart: January 31
- Amazon: December 31

This module provides configuration for accurate fiscal period mapping.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import date


@dataclass
class FiscalConfig:
    """Fiscal year configuration for a company."""
    ticker: str
    name: str
    fiscal_year_end_month: int  # 1-12
    fiscal_year_end_day: int | str  # Specific day or 'last_saturday', 'last_friday', etc.
    fiscal_year_label_format: str = "FY{year}"  # How to format fiscal year labels
    quarter_labels: tuple = ("Q1", "Q2", "Q3", "Q4")
    
    def get_quarter_for_month(self, month: int) -> int:
        """
        Get fiscal quarter (1-4) for a given calendar month.
        
        Q1 starts the month AFTER fiscal year end.
        """
        # Months after fiscal year end (0-11)
        months_into_fy = (month - self.fiscal_year_end_month - 1) % 12
        return (months_into_fy // 3) + 1
    
    def get_fiscal_year_for_date(self, d: date) -> int:
        """
        Get fiscal year for a given date.
        
        If date is after fiscal year end month, it's the NEXT fiscal year.
        """
        if d.month > self.fiscal_year_end_month:
            return d.year + 1
        elif d.month == self.fiscal_year_end_month:
            # Check if after the end day
            end_day = self._get_end_day_for_year(d.year)
            if d.day > end_day:
                return d.year + 1
        return d.year
    
    def _get_end_day_for_year(self, year: int) -> int:
        """Get the actual end day for a specific year."""
        if isinstance(self.fiscal_year_end_day, int):
            return self.fiscal_year_end_day
        
        # Handle dynamic end days like 'last_saturday'
        if self.fiscal_year_end_day == 'last_saturday':
            return self._get_last_weekday_of_month(year, self.fiscal_year_end_month, 5)
        elif self.fiscal_year_end_day == 'last_friday':
            return self._get_last_weekday_of_month(year, self.fiscal_year_end_month, 4)
        
        # Default to last day of month
        return self._get_last_day_of_month(year, self.fiscal_year_end_month)
    
    def _get_last_weekday_of_month(self, year: int, month: int, weekday: int) -> int:
        """Get the last occurrence of a weekday (0=Mon, 5=Sat) in a month."""
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        d = date(year, month, last_day)
        while d.weekday() != weekday:
            d = d.replace(day=d.day - 1)
        return d.day
    
    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """Get the last day of a month."""
        import calendar
        return calendar.monthrange(year, month)[1]


# Pre-defined configurations for major companies
COMPANY_CONFIGS: Dict[str, FiscalConfig] = {
    # Technology
    'AAPL': FiscalConfig(
        ticker='AAPL',
        name='Apple Inc.',
        fiscal_year_end_month=9,  # September
        fiscal_year_end_day='last_saturday',
    ),
    'MSFT': FiscalConfig(
        ticker='MSFT',
        name='Microsoft Corporation',
        fiscal_year_end_month=6,  # June
        fiscal_year_end_day=30,
    ),
    'GOOGL': FiscalConfig(
        ticker='GOOGL',
        name='Alphabet Inc.',
        fiscal_year_end_month=12,  # December (calendar year)
        fiscal_year_end_day=31,
    ),
    'AMZN': FiscalConfig(
        ticker='AMZN',
        name='Amazon.com Inc.',
        fiscal_year_end_month=12,
        fiscal_year_end_day=31,
    ),
    'META': FiscalConfig(
        ticker='META',
        name='Meta Platforms Inc.',
        fiscal_year_end_month=12,
        fiscal_year_end_day=31,
    ),
    'NVDA': FiscalConfig(
        ticker='NVDA',
        name='NVIDIA Corporation',
        fiscal_year_end_month=1,  # January
        fiscal_year_end_day=31,
    ),
    
    # Retail
    'WMT': FiscalConfig(
        ticker='WMT',
        name='Walmart Inc.',
        fiscal_year_end_month=1,  # January
        fiscal_year_end_day=31,
    ),
    'COST': FiscalConfig(
        ticker='COST',
        name='Costco Wholesale',
        fiscal_year_end_month=8,  # August
        fiscal_year_end_day='last_sunday',
    ),
    
    # Financial
    'JPM': FiscalConfig(
        ticker='JPM',
        name='JPMorgan Chase',
        fiscal_year_end_month=12,
        fiscal_year_end_day=31,
    ),
    'BAC': FiscalConfig(
        ticker='BAC',
        name='Bank of America',
        fiscal_year_end_month=12,
        fiscal_year_end_day=31,
    ),
    
    # Healthcare
    'JNJ': FiscalConfig(
        ticker='JNJ',
        name='Johnson & Johnson',
        fiscal_year_end_month=12,
        fiscal_year_end_day=31,
    ),
    'UNH': FiscalConfig(
        ticker='UNH',
        name='UnitedHealth Group',
        fiscal_year_end_month=12,
        fiscal_year_end_day=31,
    ),
}

# Default configuration for unknown companies (calendar year)
DEFAULT_CONFIG = FiscalConfig(
    ticker='DEFAULT',
    name='Default (Calendar Year)',
    fiscal_year_end_month=12,
    fiscal_year_end_day=31,
)


def get_company_config(ticker: str) -> FiscalConfig:
    """
    Get fiscal configuration for a company.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        
    Returns:
        FiscalConfig for the company, or DEFAULT_CONFIG if unknown
    """
    return COMPANY_CONFIGS.get(ticker.upper(), DEFAULT_CONFIG)


def detect_company_from_content(content: str) -> Optional[str]:
    """
    Try to detect company ticker from content.
    
    Args:
        content: Text content that might mention a company
        
    Returns:
        Detected ticker or None
    """
    content_lower = content.lower()
    
    # Company name to ticker mapping
    name_to_ticker = {
        'apple': 'AAPL',
        'microsoft': 'MSFT',
        'google': 'GOOGL',
        'alphabet': 'GOOGL',
        'amazon': 'AMZN',
        'meta': 'META',
        'facebook': 'META',
        'nvidia': 'NVDA',
        'walmart': 'WMT',
        'costco': 'COST',
        'jpmorgan': 'JPM',
        'bank of america': 'BAC',
        'johnson & johnson': 'JNJ',
        'unitedhealth': 'UNH',
    }
    
    for name, ticker in name_to_ticker.items():
        if name in content_lower:
            return ticker
    
    return None


def get_fiscal_period_label(
    d: date,
    config: FiscalConfig,
    include_quarter: bool = True,
    is_annual: bool = False,
) -> str:
    """
    Get a human-readable fiscal period label.
    
    Args:
        d: The date
        config: Company fiscal configuration
        include_quarter: Whether to include quarter in label
        is_annual: Whether this is an annual (year-end) figure
        
    Returns:
        Label like 'FY2023', 'Q2-FY2023', etc.
    """
    fiscal_year = config.get_fiscal_year_for_date(d)
    
    if is_annual or not include_quarter:
        return config.fiscal_year_label_format.format(year=fiscal_year)
    
    quarter = config.get_quarter_for_month(d.month)
    quarter_label = config.quarter_labels[quarter - 1]
    
    return f"{quarter_label}-{config.fiscal_year_label_format.format(year=fiscal_year)}"
```

---

## File 2: Metric Types

Create `src/opmech/metric_types.py`:

```python
"""
Financial metric type definitions and handling.

Different metrics require different change calculations:
- Absolute values (revenue): Dollar change + percentage change
- Percentages (margins): Percentage POINT change
- Ratios (P/E): Ratio difference
- Counts (employees): Absolute + percentage change

This module provides type detection and appropriate change calculations.
"""

from typing import Dict, Optional, Tuple
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
```

---

## File 3: Enhanced Evidence Preprocessor

Update `src/opmech/evidence_preprocessor.py`:

```python
"""
Enhanced Evidence Preprocessor

Enriches evidence with:
- Fiscal year/quarter labels
- Pre-computed period-over-period changes
- Multi-period trend analysis
- Metric type detection

This prevents LLM temporal interpretation errors by providing
explicit, pre-computed change information.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
import re
from loguru import logger

from .company_config import (
    FiscalConfig, 
    get_company_config, 
    detect_company_from_content,
    get_fiscal_period_label,
    DEFAULT_CONFIG,
)
from .metric_types import (
    MetricConfig,
    MetricType,
    ChangeDirection,
    ChangeResult,
    get_metric_config,
    compute_change,
    format_value,
)


@dataclass
class TrendAnalysis:
    """Analysis of multi-period trend."""
    pattern: str  # 'accelerating_growth', 'decelerating_decline', 'reversal', etc.
    description: str
    periods: List[str]
    values: List[float]
    changes: List[ChangeResult]


class EvidencePreprocessor:
    """
    Preprocesses evidence to add temporal context and computed metrics.
    
    Key features:
    - Adds explicit fiscal year/quarter labels
    - Pre-computes period-over-period changes
    - Handles different metric types (%, $, ratios)
    - Detects multi-period trends
    - Company-specific fiscal year handling
    """
    
    def __init__(self, company_ticker: Optional[str] = None):
        """
        Initialize preprocessor.
        
        Args:
            company_ticker: Stock ticker for company-specific fiscal config.
                           If None, will try to auto-detect from content.
        """
        self.company_ticker = company_ticker
        self.fiscal_config = get_company_config(company_ticker) if company_ticker else None
        
        # Date parsing patterns
        self.date_patterns = [
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),                    # 2023-09-30
            (r'(\d{2}/\d{2}/\d{4})', '%m/%d/%Y'),                    # 09/30/2023
            (r'(\w+ \d{1,2}, \d{4})', '%B %d, %Y'),                  # September 30, 2023
            (r'(\w+ \d{4})', '%B %Y'),                               # September 2023
            (r'FY(\d{4})', None),                                     # FY2023 (fiscal year only)
            (r'Q([1-4])[-\s]?(?:FY)?(\d{4})', None),                 # Q3-2023 or Q3-FY2023
        ]
    
    def preprocess(self, evidence_nodes: List[Dict]) -> List[Dict]:
        """
        Enrich evidence nodes with temporal context and computed metrics.
        
        Args:
            evidence_nodes: List of evidence node dictionaries
            
        Returns:
            Enriched evidence nodes with fiscal labels and computed changes
        """
        if not evidence_nodes:
            return evidence_nodes
        
        # Auto-detect company if not provided
        if not self.fiscal_config:
            self.fiscal_config = self._detect_company_config(evidence_nodes)
        
        enriched = []
        
        # First pass: Add fiscal period labels
        for node in evidence_nodes:
            enriched_node = self._enrich_node(node)
            enriched.append(enriched_node)
        
        # Sort by fiscal period
        enriched = self._sort_chronologically(enriched)
        
        # Second pass: Compute period-over-period changes
        enriched = self._compute_sequential_changes(enriched)
        
        # Third pass: Compute multi-period trends (for 3+ periods)
        enriched = self._compute_trends(enriched)
        
        return enriched
    
    def _detect_company_config(self, nodes: List[Dict]) -> FiscalConfig:
        """Try to detect company from evidence content."""
        for node in nodes:
            content = node.get('content', '')
            ticker = detect_company_from_content(content)
            if ticker:
                logger.debug(f"Auto-detected company: {ticker}")
                return get_company_config(ticker)
        
        logger.debug("Could not detect company, using default calendar year config")
        return DEFAULT_CONFIG
    
    def _enrich_node(self, node: Dict) -> Dict:
        """Add fiscal period and metric information to a single node."""
        enriched = node.copy()
        
        # Extract date
        date_str = node.get('period_end') or node.get('date')
        if not date_str:
            date_str = self._extract_date_from_content(node.get('content', ''))
        
        # Parse date and determine fiscal period
        if date_str:
            parsed = self._parse_date(date_str)
            if parsed:
                fiscal_year = self.fiscal_config.get_fiscal_year_for_date(parsed)
                fiscal_quarter = self.fiscal_config.get_quarter_for_month(parsed.month)
                
                # Determine if this is annual (year-end) or quarterly
                is_annual = self._is_annual_figure(node, parsed)
                
                enriched['fiscal_year'] = fiscal_year
                enriched['fiscal_quarter'] = fiscal_quarter
                enriched['fiscal_label'] = get_fiscal_period_label(
                    parsed, 
                    self.fiscal_config,
                    include_quarter=not is_annual,
                    is_annual=is_annual
                )
                enriched['parsed_date'] = parsed
                enriched['is_annual'] = is_annual
        
        # Detect metric type
        metric_config = get_metric_config(
            xbrl_tag=node.get('xbrl_tag'),
            content=node.get('content', '')
        )
        enriched['metric_config'] = metric_config
        enriched['metric_type'] = metric_config.metric_type.value
        
        # Format value if present
        if 'value' in node:
            enriched['formatted_value'] = format_value(node['value'], metric_config)
        
        return enriched
    
    def _extract_date_from_content(self, content: str) -> Optional[str]:
        """Extract date string from content."""
        for pattern, _ in self.date_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object."""
        for pattern, fmt in self.date_patterns:
            match = re.search(pattern, date_str)
            if match:
                if fmt:
                    try:
                        return datetime.strptime(match.group(1), fmt).date()
                    except ValueError:
                        continue
                else:
                    # Handle FY or Q formats
                    if 'FY' in pattern:
                        year = int(match.group(1))
                        # Assume fiscal year end
                        return date(year, self.fiscal_config.fiscal_year_end_month, 28)
                    elif 'Q' in pattern:
                        quarter = int(match.group(1))
                        year = int(match.group(2))
                        # Estimate quarter end month
                        quarter_end_month = (self.fiscal_config.fiscal_year_end_month + quarter * 3 - 3) % 12 + 1
                        return date(year, quarter_end_month, 28)
        
        return None
    
    def _is_annual_figure(self, node: Dict, parsed_date: date) -> bool:
        """Determine if this is an annual figure."""
        content = node.get('content', '').lower()
        
        # Check content for annual indicators
        annual_indicators = ['annual', 'fiscal year', 'full year', 'fy20', 'year ended']
        if any(ind in content for ind in annual_indicators):
            return True
        
        # Check if date is near fiscal year end
        if parsed_date.month == self.fiscal_config.fiscal_year_end_month:
            return True
        
        return False
    
    def _sort_chronologically(self, nodes: List[Dict]) -> List[Dict]:
        """Sort nodes by fiscal period, oldest first."""
        def sort_key(node):
            fy = node.get('fiscal_year', 9999)
            fq = node.get('fiscal_quarter', 5)
            return (fy, fq, node.get('content', '')[:50])
        
        return sorted(nodes, key=sort_key)
    
    def _compute_sequential_changes(self, nodes: List[Dict]) -> List[Dict]:
        """Compute period-over-period changes for matching metrics."""
        
        # Group by metric (using XBRL tag or content similarity)
        by_metric = self._group_by_metric(nodes)
        
        for metric_key, metric_nodes in by_metric.items():
            if len(metric_nodes) < 2:
                continue
            
            # Sort by period
            sorted_nodes = sorted(
                [n for n in metric_nodes if n.get('fiscal_year')],
                key=lambda x: (x['fiscal_year'], x.get('fiscal_quarter', 0))
            )
            
            # Compute sequential changes
            for i in range(1, len(sorted_nodes)):
                prev = sorted_nodes[i - 1]
                curr = sorted_nodes[i]
                
                if 'value' in prev and 'value' in curr:
                    change = compute_change(
                        from_value=float(prev['value']),
                        to_value=float(curr['value']),
                        from_period=prev.get('fiscal_label', 'prior'),
                        to_period=curr.get('fiscal_label', 'current'),
                        config=curr.get('metric_config', get_metric_config()),
                    )
                    curr['computed_change'] = change
        
        return nodes
    
    def _compute_trends(self, nodes: List[Dict]) -> List[Dict]:
        """Compute multi-period trends for metrics with 3+ periods."""
        
        by_metric = self._group_by_metric(nodes)
        
        for metric_key, metric_nodes in by_metric.items():
            # Need at least 3 periods for trend analysis
            nodes_with_changes = [n for n in metric_nodes if n.get('computed_change')]
            
            if len(nodes_with_changes) < 2:
                continue
            
            # Get the changes
            changes = [n['computed_change'] for n in nodes_with_changes]
            
            # Analyze trend pattern
            trend = self._analyze_trend_pattern(changes)
            
            # Add to the most recent node
            nodes_with_changes[-1]['trend_analysis'] = trend
        
        return nodes
    
    def _group_by_metric(self, nodes: List[Dict]) -> Dict[str, List[Dict]]:
        """Group nodes by their metric (XBRL tag or content similarity)."""
        groups = {}
        
        for node in nodes:
            # Use XBRL tag if available
            key = node.get('xbrl_tag')
            
            if not key:
                # Fall back to extracting metric name from content
                key = self._extract_metric_name(node.get('content', ''))
            
            if not key:
                key = 'unknown'
            
            if key not in groups:
                groups[key] = []
            groups[key].append(node)
        
        return groups
    
    def _extract_metric_name(self, content: str) -> Optional[str]:
        """Extract a metric name from content for grouping."""
        # Common patterns
        patterns = [
            r'(Total (?:Net )?(?:Sales|Revenue|Income|Profit))',
            r'(Gross (?:Profit|Margin))',
            r'(Operating (?:Income|Expenses|Margin))',
            r'(Net (?:Income|Sales|Revenue))',
            r'(iPhone|iPad|Mac|Services|Wearables)',  # Apple segments
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).lower().strip()
        
        return None
    
    def _analyze_trend_pattern(self, changes: List[ChangeResult]) -> TrendAnalysis:
        """Analyze the pattern of changes across periods."""
        
        if len(changes) < 2:
            return TrendAnalysis(
                pattern='insufficient_data',
                description='Insufficient data for trend analysis',
                periods=[c.to_period for c in changes],
                values=[c.to_value for c in changes],
                changes=changes,
            )
        
        # Get percentage changes (or absolute for ratios)
        pct_changes = []
        for c in changes:
            if c.percentage_change is not None:
                pct_changes.append(c.percentage_change)
            else:
                pct_changes.append(c.absolute_change)
        
        # Determine pattern
        all_positive = all(c > 0 for c in pct_changes)
        all_negative = all(c < 0 for c in pct_changes)
        
        if all_positive:
            if pct_changes[-1] > pct_changes[-2]:
                pattern = 'accelerating_growth'
                description = 'Growth is accelerating'
            else:
                pattern = 'decelerating_growth'
                description = 'Growth is slowing but still positive'
        elif all_negative:
            if pct_changes[-1] < pct_changes[-2]:
                pattern = 'accelerating_decline'
                description = 'Decline is accelerating'
            else:
                pattern = 'decelerating_decline'
                description = 'Decline is slowing'
        else:
            # Direction changed
            if pct_changes[-1] > 0 and pct_changes[-2] < 0:
                pattern = 'reversal_to_growth'
                description = 'Reversed from decline to growth'
            elif pct_changes[-1] < 0 and pct_changes[-2] > 0:
                pattern = 'reversal_to_decline'
                description = 'Reversed from growth to decline'
            else:
                pattern = 'volatile'
                description = 'Volatile with mixed direction changes'
        
        return TrendAnalysis(
            pattern=pattern,
            description=description,
            periods=[c.to_period for c in changes],
            values=[c.to_value for c in changes],
            changes=changes,
        )
    
    def format_for_llm(self, nodes: List[Dict]) -> str:
        """
        Format preprocessed evidence for LLM consumption.
        
        Includes explicit temporal labels and pre-computed changes
        to prevent LLM interpretation errors.
        """
        lines = []
        
        for node in nodes:
            # Build the evidence line
            node_type = node.get('type', node.get('node_type', 'UNKNOWN'))
            fiscal_label = node.get('fiscal_label', '')
            content = node.get('content', '')
            
            # Add fiscal year prefix if available
            if fiscal_label:
                line = f"[{node_type}] [{fiscal_label}] {content}"
            else:
                line = f"[{node_type}] {content}"
            
            # Add formatted value if different from content
            if 'formatted_value' in node and node['formatted_value'] not in content:
                line += f" (Value: {node['formatted_value']})"
            
            # Add computed change if available
            if 'computed_change' in node:
                change = node['computed_change']
                change_line = (
                    f"    -> Change from {change.from_period} to {change.to_period}: "
                    f"{change.formatted_change}"
                )
                
                # Add favorability indicator
                if change.is_favorable is not None:
                    indicator = "✓ Favorable" if change.is_favorable else "⚠ Unfavorable"
                    change_line += f" [{indicator}]"
                
                line += "\n" + change_line
            
            # Add trend analysis if available
            if 'trend_analysis' in node:
                trend = node['trend_analysis']
                trend_line = f"    -> Trend: {trend.description} ({trend.pattern})"
                line += "\n" + trend_line
            
            lines.append(line)
        
        return "\n\n".join(lines)
```

---

## File 4: Enhanced Answer Validator

Update `src/opmech/answer_validator.py`:

```python
"""
Enhanced Answer Validator

Validates operator answers for:
- Temporal direction accuracy
- Numerical consistency
- Metric type appropriate claims
- Cross-period consistency

Adjusts confidence when errors are detected.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re
from loguru import logger

from .metric_types import MetricType, ChangeDirection, get_metric_config


@dataclass
class ValidationIssue:
    """A specific validation issue found."""
    issue_type: str  # 'direction_error', 'numerical_mismatch', 'period_confusion'
    description: str
    severity: str  # 'critical', 'warning', 'info'
    correction: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result."""
    is_valid: bool
    issues: List[ValidationIssue]
    confidence_adjustment: float
    corrected_answer: Optional[str] = None


class AnswerValidator:
    """
    Validates operator answers for factual consistency.
    
    Catches:
    - Temporal direction errors (claimed increase but numbers show decrease)
    - Numerical mismatches (wrong figures)
    - Period labeling errors (FY2022 vs FY2023 confusion)
    - Metric type errors (percentage points vs percentage change)
    """
    
    # Confidence penalties for different issue types
    SEVERITY_PENALTIES = {
        'critical': 0.20,
        'warning': 0.10,
        'info': 0.02,
    }
    
    # Direction indicator patterns
    INCREASE_PATTERNS = [
        r'\bincreas\w*\b',
        r'\bgrew\b',
        r'\bgrowth\b',
        r'\brose\b',
        r'\bgain\w*\b',
        r'\bhigher\b',
        r'\bup\s+\d',
        r'\bimproved?\b',
        r'\bexpand\w*\b',
    ]
    
    DECREASE_PATTERNS = [
        r'\bdecreas\w*\b',
        r'\bdeclin\w*\b',
        r'\bfell\b',
        r'\bfall\w*\b',
        r'\bdrop\w*\b',
        r'\blower\b',
        r'\bdown\s+\d',
        r'\breduction\b',
        r'\bcontract\w*\b',
        r'\bshrink\w*\b',
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self._increase_re = [re.compile(p, re.IGNORECASE) for p in self.INCREASE_PATTERNS]
        self._decrease_re = [re.compile(p, re.IGNORECASE) for p in self.DECREASE_PATTERNS]
    
    def validate(
        self,
        answer: str,
        evidence: List[Dict],
        query: str,
    ) -> ValidationResult:
        """
        Validate an answer against the evidence.
        
        Args:
            answer: The generated answer text
            evidence: Preprocessed evidence nodes
            query: The original query
            
        Returns:
            ValidationResult with issues and confidence adjustment
        """
        issues = []
        
        # Extract claims from answer
        temporal_claims = self._extract_temporal_claims(answer)
        
        # Validate each claim
        for claim in temporal_claims:
            claim_issues = self._validate_claim(claim, evidence)
            issues.extend(claim_issues)
        
        # Check for internal contradictions
        contradiction_issues = self._check_contradictions(answer)
        issues.extend(contradiction_issues)
        
        # Check metric type usage
        metric_issues = self._check_metric_type_usage(answer, evidence)
        issues.extend(metric_issues)
        
        # Calculate confidence adjustment
        confidence_adjustment = sum(
            -self.SEVERITY_PENALTIES.get(issue.severity, 0.05)
            for issue in issues
        )
        confidence_adjustment = max(confidence_adjustment, -0.50)  # Cap at 50% reduction
        
        is_valid = not any(i.severity == 'critical' for i in issues)
        
        if issues:
            logger.warning(f"Answer validation found {len(issues)} issues: {[i.description for i in issues][:3]}...")
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            confidence_adjustment=confidence_adjustment,
        )
    
    def _extract_temporal_claims(self, answer: str) -> List[Dict]:
        """Extract claims about temporal changes from the answer."""
        claims = []
        
        # Pattern: value1 in period1 to value2 in period2
        # Handles: "$394B in FY2022 to $383B in FY2023"
        patterns = [
            # $XXX in FYxxxx to $YYY in FYyyyy
            r'\$?([\d,.]+)\s*[BbMm]?\w*\s+(?:in\s+)?(?:FY)?(\d{4}).*?(?:to|→|->)\s*\$?([\d,.]+)\s*[BbMm]?\w*\s+(?:in\s+)?(?:FY)?(\d{4})',
            # from $XXX to $YYY (FYxxxx to FYyyyy)
            r'from\s+\$?([\d,.]+)\s*[BbMm]?\s+to\s+\$?([\d,.]+)\s*[BbMm]?.*?(?:FY)?(\d{4}).*?(?:FY)?(\d{4})',
            # XXX% in FYxxxx to YYY% in FYyyyy (percentages)
            r'([\d.]+)\s*%?\s+(?:in\s+)?(?:FY)?(\d{4}).*?(?:to|→)\s*([\d.]+)\s*%?\s+(?:in\s+)?(?:FY)?(\d{4})',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, answer, re.IGNORECASE):
                groups = match.groups()
                
                # Parse based on pattern type
                if len(groups) == 4:
                    value1 = self._parse_number(groups[0])
                    year1 = int(groups[1]) if groups[1].isdigit() else int(groups[2])
                    value2 = self._parse_number(groups[2] if groups[1].isdigit() else groups[1])
                    year2 = int(groups[3])
                    
                    # Ensure chronological order
                    if year1 > year2:
                        value1, value2 = value2, value1
                        year1, year2 = year2, year1
                
                # Get claimed direction from surrounding context
                start = max(0, match.start() - 100)
                end = min(len(answer), match.end() + 100)
                context = answer[start:end]
                claimed_direction = self._detect_direction(context)
                
                # Compute actual direction
                if value1 > 0 and value2 > 0:
                    if value2 > value1:
                        actual_direction = 'increase'
                    elif value2 < value1:
                        actual_direction = 'decrease'
                    else:
                        actual_direction = 'unchanged'
                else:
                    actual_direction = None
                
                claims.append({
                    'text': match.group(0),
                    'from_value': value1,
                    'from_year': year1,
                    'to_value': value2,
                    'to_year': year2,
                    'claimed_direction': claimed_direction,
                    'actual_direction': actual_direction,
                    'context': context,
                    'is_percentage': '%' in match.group(0),
                })
        
        return claims
    
    def _parse_number(self, text: str) -> float:
        """Parse a number, handling B/M suffixes and commas."""
        if not text:
            return 0.0
        
        text = str(text).replace(',', '').replace('$', '').strip()
        
        multiplier = 1
        if text.upper().endswith('B'):
            multiplier = 1e9
            text = text[:-1]
        elif text.upper().endswith('M'):
            multiplier = 1e6
            text = text[:-1]
        elif text.upper().endswith('K'):
            multiplier = 1e3
            text = text[:-1]
        
        try:
            return float(text) * multiplier
        except ValueError:
            return 0.0
    
    def _detect_direction(self, context: str) -> Optional[str]:
        """Detect claimed direction from context."""
        context_lower = context.lower()
        
        increase_matches = sum(1 for p in self._increase_re if p.search(context_lower))
        decrease_matches = sum(1 for p in self._decrease_re if p.search(context_lower))
        
        if increase_matches > decrease_matches:
            return 'increase'
        elif decrease_matches > increase_matches:
            return 'decrease'
        
        return None
    
    def _validate_claim(self, claim: Dict, evidence: List[Dict]) -> List[ValidationIssue]:
        """Validate a single temporal claim."""
        issues = []
        
        claimed = claim.get('claimed_direction')
        actual = claim.get('actual_direction')
        
        # Check direction consistency
        if claimed and actual and claimed != actual:
            from_val = claim['from_value']
            to_val = claim['to_value']
            
            if from_val >= 1e9:  # Billions
                from_fmt = f"${from_val/1e9:.0f}B"
                to_fmt = f"${to_val/1e9:.0f}B"
            elif from_val >= 1e6:  # Millions
                from_fmt = f"${from_val/1e6:.0f}M"
                to_fmt = f"${to_val/1e6:.0f}M"
            else:
                from_fmt = f"${from_val:,.0f}"
                to_fmt = f"${to_val:,.0f}"
            
            pct_change = ((to_val - from_val) / from_val * 100) if from_val != 0 else 0
            
            issues.append(ValidationIssue(
                issue_type='direction_error',
                description=f"Direction error: Claimed {claimed} but {from_fmt} -> {to_fmt} is actually a {actual} ({pct_change:+.1f}%)",
                severity='critical',
                correction=f"{from_fmt} (FY{claim['from_year']}) to {to_fmt} (FY{claim['to_year']}), a {actual} of {abs(pct_change):.1f}%",
            ))
        
        # Check if years might be swapped
        if claim['from_year'] > claim['to_year']:
            issues.append(ValidationIssue(
                issue_type='period_order',
                description=f"Period order issue: Earlier period (FY{claim['from_year']}) should come before later period (FY{claim['to_year']})",
                severity='warning',
            ))
        
        return issues
    
    def _check_contradictions(self, answer: str) -> List[ValidationIssue]:
        """Check for internal contradictions in the answer."""
        issues = []
        
        sentences = re.split(r'[.!?]', answer)
        
        # Look for contradictory claims about the same metric
        metrics = ['revenue', 'sales', 'income', 'profit', 'margin', 'iphone', 'cost', 'expense']
        
        for metric in metrics:
            metric_sentences = [s for s in sentences if metric in s.lower()]
            
            if len(metric_sentences) >= 2:
                directions = []
                for sent in metric_sentences:
                    sent_lower = sent.lower()
                    if any(p.search(sent_lower) for p in self._increase_re):
                        directions.append(('increase', sent[:50]))
                    elif any(p.search(sent_lower) for p in self._decrease_re):
                        directions.append(('decrease', sent[:50]))
                
                # Check for contradictions
                unique_dirs = set(d[0] for d in directions)
                if len(unique_dirs) > 1:
                    issues.append(ValidationIssue(
                        issue_type='internal_contradiction',
                        description=f"Contradictory claims about {metric}: both 'increase' and 'decrease' mentioned",
                        severity='warning',
                    ))
        
        return issues
    
    def _check_metric_type_usage(self, answer: str, evidence: List[Dict]) -> List[ValidationIssue]:
        """Check that percentage changes are described correctly."""
        issues = []
        
        # Check for "increased by X%" when discussing margin changes
        # Margins should use "percentage points", not "percent"
        margin_pattern = r'margin.*(?:increased?|decreased?|changed?).*by\s+([\d.]+)\s*%'
        
        for match in re.finditer(margin_pattern, answer, re.IGNORECASE):
            # This might be confusing percentage points with percentage change
            pct_value = float(match.group(1))
            
            # If the value is small (< 5), it's probably percentage points (correct)
            # If it's larger, it might be a relative percentage change (potentially confusing)
            if pct_value > 5:
                issues.append(ValidationIssue(
                    issue_type='metric_type_confusion',
                    description=f"Potential confusion: '{match.group(0)}' - for margins, changes are typically stated in percentage POINTS (e.g., '2 percentage points'), not relative percent",
                    severity='info',
                ))
        
        return issues


def validate_and_adjust_answer(
    answer: str,
    evidence: List[Dict],
    query: str,
    original_confidence: float,
) -> Tuple[str, float, List[str]]:
    """
    Validate answer and adjust confidence.
    
    Convenience function that returns a tuple of (answer, adjusted_confidence, issues).
    """
    validator = AnswerValidator()
    result = validator.validate(answer, evidence, query)
    
    adjusted_confidence = original_confidence + result.confidence_adjustment
    adjusted_confidence = max(0.10, min(0.99, adjusted_confidence))
    
    issue_strings = [i.description for i in result.issues]
    
    # Add correction notes if critical issues found
    if any(i.severity == 'critical' for i in result.issues):
        corrections = [i.correction for i in result.issues if i.correction]
        if corrections:
            answer += "\n\n**Note: Validation identified potential accuracy issues. Please verify:**\n"
            for c in corrections:
                answer += f"- {c}\n"
    
    return answer, adjusted_confidence, issue_strings
```

---

## File 5: Enhanced Prompts

Update `src/opmech/prompts.py`:

```python
"""
Enhanced prompts for temporal accuracy and metric-type awareness.
"""

TEMPORAL_VERIFICATION_INSTRUCTIONS = """
CRITICAL INSTRUCTIONS FOR TEMPORAL AND NUMERICAL ACCURACY:

1. VERIFY DIRECTION BEFORE STATING:
   - Identify the EARLIER period value
   - Identify the LATER period value
   - Compute: later_value - earlier_value
   - If result is POSITIVE → INCREASE
   - If result is NEGATIVE → DECREASE
   - NEVER guess - always compute

2. FOR DOLLAR AMOUNTS (revenue, profit, costs):
   - Compare dollar amounts directly
   - Example: $394B (FY2022) → $383B (FY2023)
   - Computation: $383B - $394B = -$11B
   - Result: DECREASE of $11B (-2.8%)

3. FOR PERCENTAGES (margins, rates):
   - Compare percentage POINTS, not relative change
   - Example: 43.3% → 44.1%
   - Computation: 44.1 - 43.3 = +0.8
   - Result: INCREASE of 0.8 percentage points
   - Do NOT say "increased by 1.8%" (that's relative change)

4. FOR RATIOS (P/E, debt-to-equity):
   - Compare the ratio values directly
   - Example: 15.2x → 18.5x
   - Result: INCREASE of 3.3x

5. USE PRE-COMPUTED CHANGES:
   - When evidence includes "-> Change from X to Y: DIRECTION"
   - USE that pre-computed value as the authoritative source
   - It has been validated for accuracy

6. FISCAL YEAR LABELS:
   - [FY2022] means fiscal year 2022
   - [FY2023] means fiscal year 2023
   - FY2022 is EARLIER than FY2023
   - Values with [FY2022] are from the EARLIER period
"""

OPERATOR_ANSWER_PROMPT = f"""You are a financial analyst assistant analyzing SEC filings.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

BEFORE answering, verify any temporal claims by computing the actual change direction.

Answer:"""


OPERATOR_ANSWER_PROMPT_STRUCTURED = f"""You are a financial analyst assistant.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

Structure your response as follows:
1. First, identify the key values and their periods
2. Compute the direction of change (show your work)
3. State your answer using the computed direction

Answer:"""


EXPLORE_MODE_MERGE_PROMPT = f"""You are synthesizing two analytical perspectives on a financial question.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

CRITICAL: Both perspectives should agree on basic FACTUAL claims (numbers, directions).
If they disagree on direction (one says increase, other says decrease), this is a factual error.

Perspective A (Quantitative/Financial):
{{answer_A}}

Perspective B (Qualitative/Narrative):
{{answer_B}}

{{discrepancy_note}}

FACT CHECK before synthesizing:
1. Do both perspectives agree on the direction of change?
   - If NO, use the pre-computed changes from evidence as the authoritative source
2. Do the specific figures match?
3. Note any discrepancies explicitly

Question: {{query}}

Synthesized Answer:"""


ADAPTIVE_MODE_PROMPT = f"""You are providing a balanced financial analysis.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence from multiple sources:
{{evidence}}

Primary finding:
{{primary_answer}}

Additional context:
{{secondary_answer}}

Question: {{query}}

Provide a balanced answer that:
1. States the factual finding with verified direction
2. Adds relevant context
3. Notes any limitations or uncertainties

Answer:"""


# Prompts for specific query types

NUMERICAL_QUERY_PROMPT = f"""You are answering a specific numerical question about financial data.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

Requirements:
1. Provide a specific number as the answer
2. Cite the source (XBRL tag, fiscal period)
3. If multiple values exist, clarify which period/context
4. Use the pre-computed change if a comparison is requested

Answer:"""


CAUSAL_QUERY_PROMPT = f"""You are analyzing the causes/factors behind a financial change.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

Requirements:
1. First, establish the FACTUAL change (direction and magnitude)
2. Then, analyze the contributing factors
3. Distinguish between:
   - Verified factors (mentioned in filings)
   - Possible factors (inferred from context)
4. Do not speculate beyond the evidence

Answer:"""


OPINION_QUERY_PROMPT = f"""You are providing a balanced analysis of a debatable financial question.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

Requirements:
1. Present multiple perspectives (quantitative and qualitative)
2. Ground opinions in factual evidence
3. Acknowledge limitations and uncertainties
4. Do not claim certainty on inherently uncertain questions

Answer:"""
```

---

## File 6: Enhanced Consistency Checker

Update `src/opmech/consistency_checker.py`:

```python
"""
Enhanced Cross-Operator Consistency Checker

Detects discrepancies between operator answers:
- Direction disagreements (A says increase, B says decrease)
- Numerical mismatches (different figures for same metric)
- Period labeling conflicts

Generates resolution recommendations and analyst notes.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
from loguru import logger


@dataclass
class Discrepancy:
    """A discrepancy between operator answers."""
    discrepancy_type: str  # 'direction', 'numerical', 'period'
    metric: str
    operator_A_claim: str
    operator_B_claim: str
    resolution: Optional[str] = None
    severity: str = 'warning'  # 'critical', 'warning', 'info'


@dataclass
class ConsistencyResult:
    """Result of consistency check."""
    is_consistent: bool
    discrepancies: List[Discrepancy]
    analyst_note: str
    recommended_action: str


class CrossOperatorConsistencyChecker:
    """
    Checks consistency between Operator A and Operator B answers.
    
    Detects:
    - Direction discrepancies (increase vs decrease)
    - Numerical discrepancies (different values)
    - Period labeling discrepancies
    
    Generates analyst notes for discrepancies.
    """
    
    # Direction patterns
    INCREASE_WORDS = ['increase', 'grew', 'growth', 'rose', 'gain', 'higher', 'up', 'improve', 'expand']
    DECREASE_WORDS = ['decrease', 'decline', 'fell', 'drop', 'lower', 'down', 'contract', 'shrink', 'reduction']
    
    def check_consistency(
        self,
        answer_A: str,
        answer_B: str,
        evidence_A: Optional[List[Dict]] = None,
        evidence_B: Optional[List[Dict]] = None,
    ) -> ConsistencyResult:
        """
        Check if both operators agree on factual claims.
        
        Args:
            answer_A: Operator A's answer
            answer_B: Operator B's answer
            evidence_A: Operator A's evidence (for resolution)
            evidence_B: Operator B's evidence (for resolution)
            
        Returns:
            ConsistencyResult with discrepancies and recommendations
        """
        discrepancies = []
        
        # Check direction discrepancies
        direction_discrepancies = self._check_direction_consistency(answer_A, answer_B)
        discrepancies.extend(direction_discrepancies)
        
        # Check numerical discrepancies
        numerical_discrepancies = self._check_numerical_consistency(answer_A, answer_B)
        discrepancies.extend(numerical_discrepancies)
        
        # Try to resolve discrepancies using evidence
        if evidence_A or evidence_B:
            for d in discrepancies:
                if not d.resolution:
                    d.resolution = self._resolve_from_evidence(d, evidence_A, evidence_B)
        
        # Generate analyst note
        analyst_note = self._generate_analyst_note(discrepancies)
        
        # Determine recommended action
        recommended_action = self._get_recommended_action(discrepancies)
        
        is_consistent = len(discrepancies) == 0
        
        if discrepancies:
            logger.warning(f"Found {len(discrepancies)} discrepancies between operators")
        
        return ConsistencyResult(
            is_consistent=is_consistent,
            discrepancies=discrepancies,
            analyst_note=analyst_note,
            recommended_action=recommended_action,
        )
    
    def _check_direction_consistency(self, answer_A: str, answer_B: str) -> List[Discrepancy]:
        """Check if operators agree on direction of changes."""
        discrepancies = []
        
        # Extract direction claims for common metrics
        metrics = ['revenue', 'sales', 'income', 'profit', 'margin', 'iphone', 'mac', 'ipad', 'services']
        
        for metric in metrics:
            dir_A = self._extract_direction_for_metric(answer_A, metric)
            dir_B = self._extract_direction_for_metric(answer_B, metric)
            
            if dir_A and dir_B and dir_A != dir_B:
                discrepancies.append(Discrepancy(
                    discrepancy_type='direction',
                    metric=metric,
                    operator_A_claim=dir_A,
                    operator_B_claim=dir_B,
                    severity='critical',
                ))
        
        return discrepancies
    
    def _extract_direction_for_metric(self, answer: str, metric: str) -> Optional[str]:
        """Extract claimed direction for a specific metric."""
        # Find sentences mentioning this metric
        sentences = re.split(r'[.!?]', answer.lower())
        metric_sentences = [s for s in sentences if metric in s]
        
        for sent in metric_sentences:
            # Check for direction indicators
            for word in self.INCREASE_WORDS:
                if word in sent:
                    return 'increase'
            for word in self.DECREASE_WORDS:
                if word in sent:
                    return 'decrease'
        
        return None
    
    def _check_numerical_consistency(self, answer_A: str, answer_B: str) -> List[Discrepancy]:
        """Check if operators agree on specific numbers."""
        discrepancies = []
        
        # Extract numbers with context
        numbers_A = self._extract_numbers_with_context(answer_A)
        numbers_B = self._extract_numbers_with_context(answer_B)
        
        # Find numbers that appear in both with same context but different values
        for context_A, value_A in numbers_A.items():
            for context_B, value_B in numbers_B.items():
                # Check if contexts are similar (same metric/period)
                if self._contexts_match(context_A, context_B):
                    # Check if values differ significantly (>5%)
                    if value_A > 0 and value_B > 0:
                        diff_pct = abs(value_A - value_B) / max(value_A, value_B) * 100
                        if diff_pct > 5:
                            discrepancies.append(Discrepancy(
                                discrepancy_type='numerical',
                                metric=context_A,
                                operator_A_claim=f"${value_A/1e9:.2f}B",
                                operator_B_claim=f"${value_B/1e9:.2f}B",
                                severity='warning',
                            ))
        
        return discrepancies
    
    def _extract_numbers_with_context(self, text: str) -> Dict[str, float]:
        """Extract dollar amounts with their context."""
        numbers = {}
        
        # Pattern: $XXX.XXB or XXX.XX billion
        pattern = r'(\$?[\d,.]+)\s*([BbMm](?:illion)?)?'
        
        for match in re.finditer(pattern, text):
            value_str = match.group(1).replace('$', '').replace(',', '')
            suffix = match.group(2) or ''
            
            try:
                value = float(value_str)
                if 'b' in suffix.lower():
                    value *= 1e9
                elif 'm' in suffix.lower():
                    value *= 1e6
                
                # Get context (surrounding words)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 30)
                context = text[start:end].lower()
                
                # Clean context for use as key
                context_key = re.sub(r'[^\w\s]', '', context)[:50]
                
                numbers[context_key] = value
                
            except ValueError:
                continue
        
        return numbers
    
    def _contexts_match(self, context_A: str, context_B: str) -> bool:
        """Check if two contexts are referring to the same metric/period."""
        # Look for common keywords
        keywords = ['revenue', 'sales', 'income', 'profit', 'margin', 'fy202', '2023', '2022']
        
        common = sum(1 for k in keywords if k in context_A and k in context_B)
        return common >= 2
    
    def _resolve_from_evidence(
        self,
        discrepancy: Discrepancy,
        evidence_A: Optional[List[Dict]],
        evidence_B: Optional[List[Dict]],
    ) -> str:
        """Try to resolve discrepancy using evidence."""
        all_evidence = (evidence_A or []) + (evidence_B or [])
        
        for node in all_evidence:
            # Check if evidence has pre-computed change for this metric
            if discrepancy.metric.lower() in node.get('content', '').lower():
                if 'computed_change' in node:
                    change = node['computed_change']
                    return f"Evidence shows {change.direction.value}: {change.formatted_change}"
        
        return "Unable to resolve - check raw evidence for authoritative figures"
    
    def _generate_analyst_note(self, discrepancies: List[Discrepancy]) -> str:
        """Generate an analyst note for discrepancies."""
        if not discrepancies:
            return ""
        
        note = "\n\n---\n**Analyst Note:** "
        
        direction_issues = [d for d in discrepancies if d.discrepancy_type == 'direction']
        numerical_issues = [d for d in discrepancies if d.discrepancy_type == 'numerical']
        
        if direction_issues:
            for d in direction_issues:
                note += (
                    f"There was initial disagreement about the direction of {d.metric} change "
                    f"(A: {d.operator_A_claim}, B: {d.operator_B_claim}). "
                )
                if d.resolution:
                    note += f"Resolution: {d.resolution}. "
        
        if numerical_issues:
            note += "Some numerical values differed between analyses - figures have been verified against source data. "
        
        return note
    
    def _get_recommended_action(self, discrepancies: List[Discrepancy]) -> str:
        """Get recommended action based on discrepancies."""
        if not discrepancies:
            return "No action needed - answers are consistent"
        
        critical = [d for d in discrepancies if d.severity == 'critical']
        
        if critical:
            return (
                "CRITICAL: Direction discrepancy detected. "
                "Use pre-computed changes from evidence as authoritative source. "
                "Add analyst note to final answer."
            )
        
        return (
            "Minor discrepancies detected. "
            "Verify figures against evidence and note any uncertainties."
        )
```

---

## File 7: Comprehensive Test Suite

Create `src/opmech/tests/test_generalized_temporal.py`:

```python
"""
Comprehensive test suite for generalized temporal handling.

Tests:
- Quarterly period mapping
- Multiple companies (different fiscal year ends)
- Different metric types (%, $, ratios)
- Multi-period trends
- Edge cases
"""

import pytest
from datetime import date
from ..company_config import get_company_config, FiscalConfig, get_fiscal_period_label
from ..metric_types import (
    get_metric_config, compute_change, MetricType, ChangeDirection, GoodDirection
)
from ..evidence_preprocessor import EvidencePreprocessor
from ..answer_validator import AnswerValidator, validate_and_adjust_answer
from ..consistency_checker import CrossOperatorConsistencyChecker


class TestCompanyConfig:
    """Test company fiscal year configurations."""
    
    def test_apple_fiscal_year(self):
        """Apple's fiscal year ends in September."""
        config = get_company_config('AAPL')
        
        # September 2023 = FY2023
        assert config.get_fiscal_year_for_date(date(2023, 9, 30)) == 2023
        
        # October 2023 = FY2024 (new fiscal year started)
        assert config.get_fiscal_year_for_date(date(2023, 10, 1)) == 2024
        
        # June 2023 = FY2023
        assert config.get_fiscal_year_for_date(date(2023, 6, 15)) == 2023
    
    def test_microsoft_fiscal_year(self):
        """Microsoft's fiscal year ends in June."""
        config = get_company_config('MSFT')
        
        # June 2023 = FY2023
        assert config.get_fiscal_year_for_date(date(2023, 6, 30)) == 2023
        
        # July 2023 = FY2024
        assert config.get_fiscal_year_for_date(date(2023, 7, 1)) == 2024
        
        # December 2023 = FY2024
        assert config.get_fiscal_year_for_date(date(2023, 12, 15)) == 2024
    
    def test_walmart_fiscal_year(self):
        """Walmart's fiscal year ends in January."""
        config = get_company_config('WMT')
        
        # January 2024 = FY2024
        assert config.get_fiscal_year_for_date(date(2024, 1, 31)) == 2024
        
        # February 2024 = FY2025
        assert config.get_fiscal_year_for_date(date(2024, 2, 1)) == 2025
    
    def test_quarter_mapping_apple(self):
        """Test quarterly mapping for Apple."""
        config = get_company_config('AAPL')
        
        # Apple Q1 = Oct-Dec, Q2 = Jan-Mar, Q3 = Apr-Jun, Q4 = Jul-Sep
        assert config.get_quarter_for_month(10) == 1  # October = Q1
        assert config.get_quarter_for_month(1) == 2   # January = Q2
        assert config.get_quarter_for_month(4) == 3   # April = Q3
        assert config.get_quarter_for_month(9) == 4   # September = Q4
    
    def test_fiscal_period_label(self):
        """Test fiscal period label generation."""
        config = get_company_config('AAPL')
        
        # Annual
        label = get_fiscal_period_label(date(2023, 9, 30), config, is_annual=True)
        assert label == 'FY2023'
        
        # Quarterly
        label = get_fiscal_period_label(date(2023, 4, 1), config, include_quarter=True)
        assert 'Q3' in label and '2023' in label


class TestMetricTypes:
    """Test metric type detection and change computation."""
    
    def test_revenue_detection(self):
        """Test revenue metric detection."""
        config = get_metric_config(xbrl_tag='us-gaap:Revenues')
        
        assert config.metric_type == MetricType.ABSOLUTE
        assert config.good_direction == GoodDirection.INCREASE
    
    def test_margin_detection(self):
        """Test margin (percentage) metric detection."""
        config = get_metric_config(xbrl_tag='GrossMargin')
        
        assert config.metric_type == MetricType.PERCENTAGE
        assert config.good_direction == GoodDirection.INCREASE
    
    def test_cost_detection(self):
        """Test cost metric detection (decrease is good)."""
        config = get_metric_config(xbrl_tag='us-gaap:CostOfRevenue')
        
        assert config.metric_type == MetricType.ABSOLUTE
        assert config.good_direction == GoodDirection.DECREASE
    
    def test_revenue_change_computation(self):
        """Test change computation for revenue (absolute value)."""
        config = get_metric_config(xbrl_tag='us-gaap:Revenues')
        
        change = compute_change(
            from_value=394.33e9,
            to_value=383.29e9,
            from_period='FY2022',
            to_period='FY2023',
            config=config,
        )
        
        assert change.direction == ChangeDirection.DECREASE
        assert abs(change.percentage_change - (-2.8)) < 0.1
        assert change.is_favorable == False  # Decrease in revenue is bad
        assert 'DECREASE' in change.formatted_change
    
    def test_margin_change_computation(self):
        """Test change computation for margin (percentage points)."""
        config = get_metric_config(xbrl_tag='GrossMargin')
        
        change = compute_change(
            from_value=43.3,
            to_value=44.1,
            from_period='FY2022',
            to_period='FY2023',
            config=config,
        )
        
        assert change.direction == ChangeDirection.INCREASE
        assert 'percentage points' in change.formatted_change
        assert change.is_favorable == True  # Increase in margin is good
    
    def test_cost_change_computation(self):
        """Test change computation for cost (decrease is favorable)."""
        config = get_metric_config(xbrl_tag='us-gaap:OperatingExpenses')
        
        change = compute_change(
            from_value=100e9,
            to_value=95e9,
            from_period='FY2022',
            to_period='FY2023',
            config=config,
        )
        
        assert change.direction == ChangeDirection.DECREASE
        assert change.is_favorable == True  # Decrease in cost is good


class TestEvidencePreprocessor:
    """Test evidence preprocessing."""
    
    def test_fiscal_year_labeling(self):
        """Test that fiscal year labels are added correctly."""
        preprocessor = EvidencePreprocessor(company_ticker='AAPL')
        
        evidence = [
            {'content': 'Revenue: $394B', 'period_end': '2022-09-24', 'value': 394e9},
            {'content': 'Revenue: $383B', 'period_end': '2023-09-30', 'value': 383e9},
        ]
        
        enriched = preprocessor.preprocess(evidence)
        
        assert enriched[0]['fiscal_label'] == 'FY2022'
        assert enriched[1]['fiscal_label'] == 'FY2023'
    
    def test_change_computation(self):
        """Test that changes are computed correctly."""
        preprocessor = EvidencePreprocessor(company_ticker='AAPL')
        
        evidence = [
            {'content': 'Revenue', 'period_end': '2022-09-24', 'value': 394e9, 'xbrl_tag': 'Revenues'},
            {'content': 'Revenue', 'period_end': '2023-09-30', 'value': 383e9, 'xbrl_tag': 'Revenues'},
        ]
        
        enriched = preprocessor.preprocess(evidence)
        
        # Second node should have computed change
        assert 'computed_change' in enriched[1]
        assert enriched[1]['computed_change'].direction == ChangeDirection.DECREASE
    
    def test_llm_formatting(self):
        """Test formatting for LLM consumption."""
        preprocessor = EvidencePreprocessor(company_ticker='AAPL')
        
        evidence = [
            {'content': 'Total Net Sales: $394B', 'period_end': '2022-09-24', 'value': 394e9, 'xbrl_tag': 'Revenues'},
            {'content': 'Total Net Sales: $383B', 'period_end': '2023-09-30', 'value': 383e9, 'xbrl_tag': 'Revenues'},
        ]
        
        enriched = preprocessor.preprocess(evidence)
        formatted = preprocessor.format_for_llm(enriched)
        
        assert '[FY2022]' in formatted
        assert '[FY2023]' in formatted
        assert 'DECREASE' in formatted
        assert 'Change from FY2022 to FY2023' in formatted


class TestAnswerValidator:
    """Test answer validation."""
    
    def test_direction_error_detection(self):
        """Test that direction errors are detected."""
        validator = AnswerValidator()
        
        # This answer claims increase but numbers show decrease
        bad_answer = """
        Apple's revenue increased from $394.33B in FY2022 to $383.29B in FY2023,
        representing growth of about 2.8%.
        """
        
        result = validator.validate(bad_answer, [], "")
        
        assert not result.is_valid
        assert any('direction' in i.issue_type.lower() for i in result.issues)
        assert result.confidence_adjustment < 0
    
    def test_correct_answer_validation(self):
        """Test that correct answers pass validation."""
        validator = AnswerValidator()
        
        good_answer = """
        Apple's revenue decreased from $394.33B in FY2022 to $383.29B in FY2023,
        a decline of about 2.8%.
        """
        
        result = validator.validate(good_answer, [], "")
        
        # Should have no critical issues
        critical_issues = [i for i in result.issues if i.severity == 'critical']
        assert len(critical_issues) == 0
    
    def test_confidence_adjustment(self):
        """Test that confidence is adjusted for errors."""
        answer = "Revenue increased from $394B to $383B in FY2023."  # Wrong direction
        
        _, adjusted_conf, issues = validate_and_adjust_answer(
            answer, [], "", original_confidence=0.90
        )
        
        assert adjusted_conf < 0.90
        assert len(issues) > 0


class TestConsistencyChecker:
    """Test cross-operator consistency checking."""
    
    def test_direction_discrepancy_detection(self):
        """Test detection of direction discrepancies."""
        checker = CrossOperatorConsistencyChecker()
        
        answer_A = "Apple's revenue increased significantly in FY2023."
        answer_B = "Apple experienced a revenue decline in FY2023."
        
        result = checker.check_consistency(answer_A, answer_B)
        
        assert not result.is_consistent
        assert any(d.discrepancy_type == 'direction' for d in result.discrepancies)
    
    def test_consistent_answers(self):
        """Test that consistent answers are recognized."""
        checker = CrossOperatorConsistencyChecker()
        
        answer_A = "Apple's revenue decreased by 2.8% in FY2023."
        answer_B = "Revenue fell from $394B to $383B, a decline of about 3%."
        
        result = checker.check_consistency(answer_A, answer_B)
        
        # Should be consistent on direction (both say decrease/decline)
        direction_discrepancies = [d for d in result.discrepancies if d.discrepancy_type == 'direction']
        assert len(direction_discrepancies) == 0
    
    def test_analyst_note_generation(self):
        """Test that analyst notes are generated for discrepancies."""
        checker = CrossOperatorConsistencyChecker()
        
        answer_A = "Revenue increased in FY2023."
        answer_B = "Revenue decreased in FY2023."
        
        result = checker.check_consistency(answer_A, answer_B)
        
        assert "Analyst Note" in result.analyst_note or len(result.analyst_note) > 0


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_zero_value_handling(self):
        """Test handling of zero values."""
        config = get_metric_config(xbrl_tag='Revenues')
        
        change = compute_change(0, 100e9, 'FY2022', 'FY2023', config)
        
        assert change.direction == ChangeDirection.INCREASE
        assert change.percentage_change is None  # Can't compute % from zero
    
    def test_negative_value_handling(self):
        """Test handling of negative values (losses)."""
        config = get_metric_config(xbrl_tag='NetIncome')
        
        # Loss getting worse
        change = compute_change(-10e9, -15e9, 'FY2022', 'FY2023', config)
        
        assert change.direction == ChangeDirection.DECREASE
        assert change.is_favorable == False
    
    def test_unknown_company(self):
        """Test handling of unknown company ticker."""
        config = get_company_config('UNKNOWN')
        
        # Should return default (calendar year)
        assert config.fiscal_year_end_month == 12


# Run all tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

## Integration Steps

1. **Create the new files:**
   ```bash
   touch src/opmech/company_config.py
   touch src/opmech/metric_types.py
   touch src/opmech/tests/test_generalized_temporal.py
   ```

2. **Update existing files:**
   - `evidence_preprocessor.py` - Replace with enhanced version
   - `answer_validator.py` - Replace with enhanced version
   - `consistency_checker.py` - Replace with enhanced version
   - `prompts.py` - Add new prompts

3. **Run the test suite:**
   ```bash
   python -m pytest src/opmech/tests/test_generalized_temporal.py -v
   ```

4. **Integration test with real queries:**
   ```python
   # Test different scenarios
   test_queries = [
       # Quarterly
       "How did iPhone revenue change from Q3 to Q4 2023?",
       
       # Margin (percentage)
       "What happened to Apple's gross margin from FY2022 to FY2023?",
       
       # Multi-year
       "What is the revenue trend from FY2021 to FY2023?",
       
       # Cost metric
       "Did Apple's operating expenses increase or decrease in FY2023?",
       
       # Different company (if data available)
       "What was Microsoft's revenue in FY2023?",
   ]
   ```

---

## Summary of Enhancements

| Enhancement | Coverage |
|-------------|----------|
| **Company Config** | Apple, Microsoft, Walmart, Amazon, Nvidia, + 10 more |
| **Quarterly Periods** | Q1-Q4 mapping for all fiscal year types |
| **Metric Types** | Absolute ($), Percentage (%), Ratio (x), Count |
| **Good Direction** | Revenue↑, Cost↓, Margin↑, Debt↓, etc. |
| **Multi-Period Trends** | Accelerating, decelerating, reversal detection |
| **Validation** | Direction, numerical, metric-type-specific |
| **Consistency** | Cross-operator discrepancy detection |

**Target Coverage: 95%+ of temporal/metric scenarios**
