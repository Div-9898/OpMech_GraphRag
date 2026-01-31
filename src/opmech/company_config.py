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
        elif self.fiscal_year_end_day == 'last_sunday':
            return self._get_last_weekday_of_month(year, self.fiscal_year_end_month, 6)

        # Default to last day of month
        return self._get_last_day_of_month(year, self.fiscal_year_end_month)

    def _get_last_weekday_of_month(self, year: int, month: int, weekday: int) -> int:
        """Get the last occurrence of a weekday (0=Mon, 5=Sat, 6=Sun) in a month."""
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
