"""
Fiscal Period Model - Type-safe period handling.

CRITICAL: This replaces all string-based period handling.

COMPANY-AGNOSTIC: Supports any company's fiscal year configuration.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
from datetime import date
import re
from enum import Enum


class PeriodType(Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


# Company fiscal year configurations
# Key is company ticker or "DEFAULT" for calendar year companies
FISCAL_CONFIGS: Dict[str, Dict] = {
    # Apple: Fiscal year ends in September
    # Q1: Oct-Dec, Q2: Jan-Mar, Q3: Apr-Jun, Q4: Jul-Sep
    "AAPL": {
        "year_end_month": 9,
        "quarter_end_months": {1: 12, 2: 3, 3: 6, 4: 9}
    },
    # Microsoft: Fiscal year ends in June
    # Q1: Jul-Sep, Q2: Oct-Dec, Q3: Jan-Mar, Q4: Apr-Jun
    "MSFT": {
        "year_end_month": 6,
        "quarter_end_months": {1: 9, 2: 12, 3: 3, 4: 6}
    },
    # Walmart: Fiscal year ends in January
    "WMT": {
        "year_end_month": 1,
        "quarter_end_months": {1: 4, 2: 7, 3: 10, 4: 1}
    },
    # Default: Calendar year (December)
    "DEFAULT": {
        "year_end_month": 12,
        "quarter_end_months": {1: 3, 2: 6, 3: 9, 4: 12}
    }
}


def get_fiscal_config(company: str) -> Dict:
    """
    Get fiscal configuration for a company.

    Args:
        company: Company ticker or None for default

    Returns:
        Fiscal configuration dict with year_end_month and quarter_end_months
    """
    if not company:
        return FISCAL_CONFIGS["DEFAULT"]
    return FISCAL_CONFIGS.get(company.upper(), FISCAL_CONFIGS["DEFAULT"])


def register_fiscal_config(company: str, year_end_month: int) -> None:
    """
    Register a company's fiscal year configuration.

    Args:
        company: Company ticker
        year_end_month: Month when fiscal year ends (1-12)
    """
    # Calculate quarter end months based on year end
    q1_end = (year_end_month % 12) + 3
    if q1_end > 12:
        q1_end -= 12
    q2_end = (q1_end % 12) + 3
    if q2_end > 12:
        q2_end -= 12
    q3_end = (q2_end % 12) + 3
    if q3_end > 12:
        q3_end -= 12

    FISCAL_CONFIGS[company.upper()] = {
        "year_end_month": year_end_month,
        "quarter_end_months": {1: q1_end, 2: q2_end, 3: q3_end, 4: year_end_month}
    }


@dataclass(frozen=True)
class FiscalPeriod:
    """
    Immutable fiscal period representation.

    CRITICAL INVARIANTS:
    1. year is always the fiscal year (e.g., 2024 for FY2024)
    2. quarter is 1-4 for quarterly, None for annual
    3. Labels are ALWAYS explicit: "FY2024" or "Q1-FY2024"
    4. Two periods with same label are the SAME period

    COMPANY-AGNOSTIC: Works with any company's fiscal year configuration.
    """
    year: int
    quarter: Optional[int] = None
    company: str = None  # None means use default config

    # Legacy constant for backwards compatibility
    APPLE_FISCAL_CONFIG = FISCAL_CONFIGS.get("AAPL", FISCAL_CONFIGS["DEFAULT"])

    def __post_init__(self):
        """Validate period"""
        if self.year < 2000 or self.year > 2030:
            raise ValueError(f"Invalid fiscal year: {self.year}")
        if self.quarter is not None and self.quarter not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid quarter: {self.quarter}")

    @property
    def period_type(self) -> PeriodType:
        return PeriodType.QUARTERLY if self.quarter else PeriodType.ANNUAL

    @property
    def label(self) -> str:
        """
        Generate UNIQUE, UNAMBIGUOUS label.

        CRITICAL: This label uniquely identifies the period.
        Never returns generic labels like "FY1" or "Period1".
        """
        if self.quarter:
            return f"Q{self.quarter}-FY{self.year}"
        return f"FY{self.year}"

    @property
    def sort_key(self) -> Tuple[int, int]:
        """Key for chronological sorting"""
        return (self.year, self.quarter or 5)  # Annual comes after Q4

    def __lt__(self, other: 'FiscalPeriod') -> bool:
        return self.sort_key < other.sort_key

    def __le__(self, other: 'FiscalPeriod') -> bool:
        return self.sort_key <= other.sort_key

    def __gt__(self, other: 'FiscalPeriod') -> bool:
        return self.sort_key > other.sort_key

    def __ge__(self, other: 'FiscalPeriod') -> bool:
        return self.sort_key >= other.sort_key

    def __str__(self) -> str:
        return self.label

    def __repr__(self) -> str:
        return f"FiscalPeriod({self.label})"

    def __hash__(self) -> int:
        return hash((self.year, self.quarter, self.company))

    @classmethod
    def from_date(cls, d: date, company: str = None) -> 'FiscalPeriod':
        """
        Convert calendar date to fiscal period.

        COMPANY-AGNOSTIC: Works with any company's fiscal year configuration.

        Example for Apple (Sep year-end):
        - Oct 2023 - Sep 2024 = FY2024
        - Q1-FY2024 = Oct-Dec 2023
        - Q2-FY2024 = Jan-Mar 2024
        - Q3-FY2024 = Apr-Jun 2024
        - Q4-FY2024 = Jul-Sep 2024

        Example for Microsoft (Jun year-end):
        - Jul 2023 - Jun 2024 = FY2024
        - Q1-FY2024 = Jul-Sep 2023
        - Q2-FY2024 = Oct-Dec 2023
        - Q3-FY2024 = Jan-Mar 2024
        - Q4-FY2024 = Apr-Jun 2024
        """
        config = get_fiscal_config(company)
        year_end_month = config["year_end_month"]
        quarter_end_months = config["quarter_end_months"]

        # Determine fiscal year and quarter based on fiscal year end
        # Fiscal year starts the month after fiscal year end
        fiscal_start_month = (year_end_month % 12) + 1

        # Calculate which fiscal year we're in
        if d.month > year_end_month:
            # We're past the fiscal year end, so we're in next fiscal year
            fiscal_year = d.year + 1
        else:
            fiscal_year = d.year

        # Determine quarter based on quarter end months
        quarter = None
        for q, end_month in quarter_end_months.items():
            # Calculate start month for this quarter
            if q == 1:
                start_month = fiscal_start_month
            else:
                prev_end = quarter_end_months[q - 1]
                start_month = (prev_end % 12) + 1

            # Check if date falls in this quarter
            if end_month >= start_month:
                # Quarter doesn't cross year boundary
                if start_month <= d.month <= end_month:
                    quarter = q
                    break
            else:
                # Quarter crosses year boundary (e.g., Oct-Dec for Apple Q1)
                if d.month >= start_month or d.month <= end_month:
                    quarter = q
                    break

        # Fallback if quarter detection fails
        if quarter is None:
            # Use simple calculation based on months from fiscal start
            months_from_start = (d.month - fiscal_start_month) % 12
            quarter = (months_from_start // 3) + 1

        return cls(year=fiscal_year, quarter=quarter, company=company)

    @classmethod
    def from_string(cls, s: str, company: str = None) -> Optional['FiscalPeriod']:
        """
        Parse fiscal period from string.

        Accepted formats:
        - "FY2024", "FY24", "2024" -> FY2024 (annual)
        - "Q1-FY2024", "Q1 2024", "Q1-2024" -> Q1-FY2024
        - "2024-09-28" -> Infer from date
        """
        if not s:
            return None

        s = s.strip().upper()

        # Annual: FY2024, FY24, 2024
        annual_match = re.match(r'^FY?(\d{2,4})$', s)
        if annual_match:
            year = int(annual_match.group(1))
            if year < 100:
                year += 2000
            return cls(year=year, company=company)

        # Quarterly: Q1-FY2024, Q1FY2024, Q1-2024, Q1 2024
        quarter_match = re.match(r'^Q([1-4])[-\s]?(?:FY)?(\d{2,4})$', s)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            year = int(quarter_match.group(2))
            if year < 100:
                year += 2000
            return cls(year=year, quarter=quarter, company=company)

        # Date format: 2024-09-28
        date_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', s)
        if date_match:
            d = date(
                int(date_match.group(1)),
                int(date_match.group(2)),
                int(date_match.group(3))
            )
            return cls.from_date(d, company)

        return None

    @classmethod
    def from_sec_period(cls, period_str: str, company: str = None) -> Optional['FiscalPeriod']:
        """
        Parse SEC filing period references.

        Handles:
        - "2024-09-28" (period end date)
        - "fiscal 2024"
        - "three months ended December 30, 2023"
        """
        period_str = period_str.strip()

        # Direct date
        if re.match(r'^\d{4}-\d{2}-\d{2}$', period_str):
            return cls.from_string(period_str, company)

        # "fiscal 2024" or "fiscal year 2024"
        fiscal_match = re.search(r'fiscal\s*(?:year\s*)?(\d{4})', period_str, re.IGNORECASE)
        if fiscal_match:
            return cls(year=int(fiscal_match.group(1)), company=company)

        # "three months ended December 30, 2023"
        quarter_end_match = re.search(
            r'(?:three|3)\s*months\s*ended\s*(\w+)\s*(\d{1,2}),?\s*(\d{4})',
            period_str, re.IGNORECASE
        )
        if quarter_end_match:
            month_name = quarter_end_match.group(1)
            day = int(quarter_end_match.group(2))
            year = int(quarter_end_match.group(3))

            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            month = month_map.get(month_name.lower())
            if month:
                d = date(year, month, day)
                return cls.from_date(d, company)

        return None

    def to_annual(self) -> 'FiscalPeriod':
        """Convert quarterly period to its fiscal year."""
        return FiscalPeriod(year=self.year, quarter=None, company=self.company)

    def next_period(self) -> 'FiscalPeriod':
        """Get the next period (quarter or year)."""
        if self.quarter:
            if self.quarter == 4:
                return FiscalPeriod(year=self.year + 1, quarter=1, company=self.company)
            return FiscalPeriod(year=self.year, quarter=self.quarter + 1, company=self.company)
        return FiscalPeriod(year=self.year + 1, company=self.company)

    def prev_period(self) -> 'FiscalPeriod':
        """Get the previous period (quarter or year)."""
        if self.quarter:
            if self.quarter == 1:
                return FiscalPeriod(year=self.year - 1, quarter=4, company=self.company)
            return FiscalPeriod(year=self.year, quarter=self.quarter - 1, company=self.company)
        return FiscalPeriod(year=self.year - 1, company=self.company)


def get_period_between(start: FiscalPeriod, end: FiscalPeriod) -> List[FiscalPeriod]:
    """Get all periods between start and end (inclusive)"""
    periods = []
    current_year = start.year
    current_quarter = start.quarter or 1

    while True:
        if start.quarter:  # Quarterly periods
            p = FiscalPeriod(year=current_year, quarter=current_quarter, company=start.company)
        else:  # Annual periods
            p = FiscalPeriod(year=current_year, company=start.company)

        if p > end:
            break

        periods.append(p)

        if start.quarter:
            current_quarter += 1
            if current_quarter > 4:
                current_quarter = 1
                current_year += 1
        else:
            current_year += 1

    return periods
