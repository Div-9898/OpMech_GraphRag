"""
Type-Safe Data Models for OpMech Production System

This module provides immutable, type-safe data structures that CANNOT be confused:
- FiscalPeriod: Represents time periods (years, quarters) - NEVER a dollar amount
- FinancialValue: Represents money (Decimal-based) - NEVER a year
- Direction: Enum for change direction with ground truth validation

KEY PRINCIPLE: These types are distinct and cannot be compared or interchanged.
This prevents bugs like "FY2023" being parsed as "$2,023".
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Optional, List, Tuple, Any
from enum import Enum
import re


class Direction(Enum):
    """Direction of change - validated against actual values."""
    INCREASE = "increase"
    DECREASE = "decrease"
    UNCHANGED = "unchanged"


class Severity(Enum):
    """Severity of discrepancies."""
    CRITICAL = "critical"  # Must be resolved
    MAJOR = "major"        # Significant difference
    MINOR = "minor"        # Small difference


class DiscrepancyType(Enum):
    """Types of discrepancies between operators."""
    DIRECTION = "direction"      # A says increase, B says decrease
    NUMERICAL = "numerical"      # Different numbers
    FACTUAL = "factual"          # Different facts
    INTERPRETATION = "interpretation"  # Different conclusions


@dataclass(frozen=True)
class FiscalPeriod:
    """
    Immutable fiscal period - CANNOT be confused with a dollar amount.

    Key invariant: A FiscalPeriod always represents time, never money.
    """
    year: int
    quarter: Optional[int] = None
    company: str = "AAPL"

    # Company-specific fiscal year end months
    FISCAL_YEAR_ENDS = {
        "AAPL": (9, "last_saturday"),   # Apple: September (last Saturday)
        "MSFT": (6, 30),                 # Microsoft: June 30
        "WMT": (1, 31),                  # Walmart: January 31
        "GOOGL": (12, 31),               # Google: December 31
        "AMZN": (12, 31),                # Amazon: December 31
        "META": (12, 31),                # Meta: December 31
        "NVDA": (1, 31),                 # NVIDIA: January 31
    }

    def __post_init__(self):
        """Validate fiscal period data."""
        if self.year < 1900 or self.year > 2100:
            raise ValueError(f"Invalid year: {self.year}. Must be between 1900 and 2100.")
        if self.quarter is not None and (self.quarter < 1 or self.quarter > 4):
            raise ValueError(f"Invalid quarter: {self.quarter}. Must be 1-4.")

    @property
    def label(self) -> str:
        """Human-readable label - NEVER a dollar amount."""
        if self.quarter:
            return f"Q{self.quarter}-FY{self.year}"
        return f"FY{self.year}"

    @property
    def is_annual(self) -> bool:
        """Check if this is an annual (full year) period."""
        return self.quarter is None

    @property
    def sort_key(self) -> Tuple[int, int]:
        """Key for chronological sorting."""
        return (self.year, self.quarter if self.quarter else 5)  # Annual comes after Q4

    @classmethod
    def from_string(cls, s: str, company: str = "AAPL") -> Optional['FiscalPeriod']:
        """
        Parse fiscal period from string.

        CRITICAL: This returns a FiscalPeriod object, NOT a string.
        Will NOT parse dollar amounts.

        Supported formats:
        - FY2023, FY23, 2023
        - Q1-2024, Q1-FY2024, Q1FY2024, Q1 2024
        - fiscal year 2023
        """
        if not s:
            return None

        s = s.upper().strip()

        # CRITICAL: Reject anything that looks like a dollar amount
        if '$' in s or s.endswith('B') or s.endswith('M') or 'BILLION' in s or 'MILLION' in s:
            return None

        # Full year patterns: FY2023, FY23, 2023, fiscal year 2023
        fy_patterns = [
            r'^FY\s*(\d{4})$',                    # FY2023 or FY 2023
            r'^FY\s*(\d{2})$',                    # FY23
            r'^(\d{4})$',                         # 2023 (bare year)
            r'FISCAL\s*(?:YEAR\s*)?(\d{4})$',    # fiscal year 2023
        ]

        for pattern in fy_patterns:
            match = re.match(pattern, s)
            if match:
                year = int(match.group(1))
                if year < 100:
                    year += 2000
                return cls(year=year, company=company)

        # Quarter patterns: Q1-2024, Q1-FY2024, Q1FY2024, Q1 2024
        q_patterns = [
            r'^Q([1-4])\s*[-\s]?\s*(?:FY\s*)?(\d{4})$',  # Q1-2024, Q1-FY2024, Q1 FY2024
            r'^Q([1-4])\s*[-\s]?\s*(?:FY\s*)?(\d{2})$',  # Q1-24, Q1-FY24
        ]

        for pattern in q_patterns:
            match = re.match(pattern, s)
            if match:
                quarter = int(match.group(1))
                year = int(match.group(2))
                if year < 100:
                    year += 2000
                return cls(year=year, quarter=quarter, company=company)

        return None

    def __str__(self) -> str:
        return self.label

    def __repr__(self) -> str:
        return f"FiscalPeriod({self.label}, company={self.company})"

    def __lt__(self, other: 'FiscalPeriod') -> bool:
        if not isinstance(other, FiscalPeriod):
            return NotImplemented
        return self.sort_key < other.sort_key

    def __le__(self, other: 'FiscalPeriod') -> bool:
        if not isinstance(other, FiscalPeriod):
            return NotImplemented
        return self.sort_key <= other.sort_key

    def __gt__(self, other: 'FiscalPeriod') -> bool:
        if not isinstance(other, FiscalPeriod):
            return NotImplemented
        return self.sort_key > other.sort_key

    def __ge__(self, other: 'FiscalPeriod') -> bool:
        if not isinstance(other, FiscalPeriod):
            return NotImplemented
        return self.sort_key >= other.sort_key


@dataclass(frozen=True)
class FinancialValue:
    """
    Immutable financial value - CANNOT be confused with a year.

    Key invariant: A FinancialValue always represents money.
    A FiscalPeriod always represents time.
    They can NEVER be compared or confused.
    """
    amount: Decimal
    currency: str = "USD"
    scale: str = "units"  # units, thousands, millions, billions
    period: Optional[FiscalPeriod] = None
    source: Optional[str] = None
    confidence: float = 1.0

    SCALES = {
        "units": Decimal("1"),
        "thousands": Decimal("1000"),
        "millions": Decimal("1000000"),
        "billions": Decimal("1000000000"),
    }

    def __post_init__(self):
        """Validate financial value data."""
        if self.scale not in self.SCALES:
            raise ValueError(f"Invalid scale: {self.scale}. Must be one of {list(self.SCALES.keys())}")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError(f"Invalid confidence: {self.confidence}. Must be between 0 and 1.")

    @property
    def normalized_amount(self) -> Decimal:
        """Get amount in base units (dollars)."""
        return self.amount * self.SCALES.get(self.scale, Decimal("1"))

    @property
    def in_billions(self) -> Decimal:
        """Get amount in billions."""
        return self.normalized_amount / Decimal("1000000000")

    @property
    def in_millions(self) -> Decimal:
        """Get amount in millions."""
        return self.normalized_amount / Decimal("1000000")

    def format(self, precision: int = 2) -> str:
        """
        Format for display - ALWAYS includes $ sign.

        CRITICAL: The output is always clearly a dollar amount, never a year.
        """
        billions = float(self.in_billions)
        if abs(billions) >= 1:
            return f"${billions:,.{precision}f}B"

        millions = float(self.in_millions)
        if abs(millions) >= 1:
            return f"${millions:,.{precision}f}M"

        amount = float(self.normalized_amount)
        if abs(amount) >= 1000:
            return f"${amount:,.0f}"

        return f"${amount:,.{precision}f}"

    @classmethod
    def parse(cls, text: str, period: Optional[FiscalPeriod] = None) -> Optional['FinancialValue']:
        """
        Parse financial value from text.

        CRITICAL: Only parses things that look like money (have $ or B/M suffix).
        Will NOT parse bare years like "2023".
        """
        if not text:
            return None

        text = text.strip()
        original_text = text
        text_upper = text.upper()

        # CRITICAL: Reject anything that looks like a fiscal year
        fy_indicators = ['FY', 'FISCAL', 'QUARTER', 'Q1', 'Q2', 'Q3', 'Q4']
        if any(ind in text_upper for ind in fy_indicators):
            return None

        # Pattern 1: $ followed by number with optional scale
        # $383.3B, $383.3 billion, $383,290,000,000
        pattern_dollar = r'\$\s*([\d,]+\.?\d*)\s*(B|BILLION|M|MILLION|K|THOUSAND)?'
        match = re.search(pattern_dollar, text, re.IGNORECASE)

        if match:
            amount_str = match.group(1).replace(',', '')
            scale_str = (match.group(2) or "").upper()

            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                return None

            scale_map = {
                "B": "billions", "BILLION": "billions",
                "M": "millions", "MILLION": "millions",
                "K": "thousands", "THOUSAND": "thousands",
                "": "units"
            }
            scale = scale_map.get(scale_str, "units")

            return cls(amount=amount, scale=scale, period=period, source=original_text)

        # Pattern 2: Number with scale suffix (without $)
        # 383.3B, 383.3 billion, 383.3M
        # IMPORTANT: Must have a scale indicator to be recognized as money
        pattern_scale = r'^([\d,]+\.?\d*)\s*(B|BILLION|M|MILLION)\b'
        match = re.search(pattern_scale, text, re.IGNORECASE)

        if match:
            amount_str = match.group(1).replace(',', '')
            scale_str = match.group(2).upper()

            # Additional check: reject if number looks like a year (1900-2100)
            try:
                amount = Decimal(amount_str)
                if Decimal("1900") <= amount <= Decimal("2100") and scale_str == "":
                    return None  # Looks like a year, not money
            except (InvalidOperation, ValueError):
                return None

            scale_map = {
                "B": "billions", "BILLION": "billions",
                "M": "millions", "MILLION": "millions",
            }
            scale = scale_map.get(scale_str, "units")

            return cls(amount=amount, scale=scale, period=period, source=original_text)

        return None  # NOT a financial value

    @classmethod
    def from_raw(
        cls,
        amount: float,
        scale: str = "units",
        period: Optional[FiscalPeriod] = None,
        source: Optional[str] = None
    ) -> 'FinancialValue':
        """Create from raw numeric value (for programmatic use)."""
        return cls(
            amount=Decimal(str(amount)),
            scale=scale,
            period=period,
            source=source
        )

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return f"FinancialValue({self.format()}, period={self.period})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FinancialValue):
            return False
        # Compare normalized amounts with tolerance for floating point
        return abs(self.normalized_amount - other.normalized_amount) < Decimal("0.01")

    def __lt__(self, other: 'FinancialValue') -> bool:
        if not isinstance(other, FinancialValue):
            return NotImplemented
        return self.normalized_amount < other.normalized_amount

    def __sub__(self, other: 'FinancialValue') -> 'FinancialValue':
        """Subtract two financial values."""
        if not isinstance(other, FinancialValue):
            return NotImplemented
        diff = self.normalized_amount - other.normalized_amount
        return FinancialValue(amount=diff, scale="units")

    def __add__(self, other: 'FinancialValue') -> 'FinancialValue':
        """Add two financial values."""
        if not isinstance(other, FinancialValue):
            return NotImplemented
        total = self.normalized_amount + other.normalized_amount
        return FinancialValue(amount=total, scale="units")


@dataclass
class EvidenceNode:
    """
    A single piece of evidence with typed values.

    Contains both raw content and extracted typed values.
    """
    id: str
    content: str
    source_document: str
    node_type: str = "text"  # text, xbrl, table, note

    # Extracted typed values
    periods: List[FiscalPeriod] = None
    values: List[FinancialValue] = None

    # Pre-computed changes (set by TemporalIntelligence)
    computed_changes: List['ComputedChange'] = None

    # Metadata
    confidence: float = 1.0
    xbrl_tag: Optional[str] = None

    def __post_init__(self):
        if self.periods is None:
            self.periods = []
        if self.values is None:
            self.values = []
        if self.computed_changes is None:
            self.computed_changes = []


@dataclass
class ComputedChange:
    """
    Pre-computed change between two periods.

    This is computed BEFORE the LLM sees the data, so the LLM
    doesn't have to compute directions itself (and can't get it wrong).
    """
    metric_name: str
    from_period: FiscalPeriod
    to_period: FiscalPeriod
    from_value: FinancialValue
    to_value: FinancialValue
    direction: Direction
    absolute_change: FinancialValue
    percentage_change: Optional[float] = None
    is_favorable: Optional[bool] = None

    def format(self) -> str:
        """Format for display."""
        pct_str = f" ({self.percentage_change:+.1f}%)" if self.percentage_change else ""
        fav_str = ""
        if self.is_favorable is not None:
            fav_str = " [Favorable]" if self.is_favorable else " [Unfavorable]"

        return (
            f"{self.metric_name}: {self.direction.value.upper()} "
            f"from {self.from_period.label} to {self.to_period.label}\n"
            f"  {self.from_value.format()} -> {self.to_value.format()}\n"
            f"  Change: {self.absolute_change.format()}{pct_str}{fav_str}"
        )


@dataclass
class Discrepancy:
    """A single, well-formed discrepancy between operators."""
    discrepancy_type: DiscrepancyType
    severity: Severity
    metric: Optional[str] = None
    period: Optional[FiscalPeriod] = None

    # Operator values - MUST be same type
    operator_a_value: Any = None
    operator_b_value: Any = None

    # Resolution
    resolved: bool = False
    correct_value: Any = None
    resolution_source: Optional[str] = None

    def format(self) -> str:
        """Format discrepancy for clean display."""
        period_str = self.period.label if self.period else "N/A"

        if self.discrepancy_type == DiscrepancyType.DIRECTION:
            return (
                f"[{self.severity.value.upper()}] Direction discrepancy for {self.metric} "
                f"({period_str}): A={self.operator_a_value}, B={self.operator_b_value}"
            )
        elif self.discrepancy_type == DiscrepancyType.NUMERICAL:
            a_formatted = self._format_value(self.operator_a_value)
            b_formatted = self._format_value(self.operator_b_value)
            return (
                f"[{self.severity.value.upper()}] Numerical discrepancy for {self.metric}: "
                f"A={a_formatted}, B={b_formatted}"
            )
        return f"[{self.severity.value.upper()}] {self.discrepancy_type.value}: A != B"

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, FinancialValue):
            return value.format()
        if isinstance(value, FiscalPeriod):
            return value.label
        if isinstance(value, Direction):
            return value.value
        if isinstance(value, (int, float, Decimal)):
            if abs(float(value)) >= 1e9:
                return f"${float(value)/1e9:,.2f}B"
            elif abs(float(value)) >= 1e6:
                return f"${float(value)/1e6:,.2f}M"
            elif abs(float(value)) >= 1000:
                return f"${float(value):,.0f}"
            return str(value)
        return str(value)


@dataclass
class ConsistencyReport:
    """Report from consistency checking."""
    discrepancies: List[Discrepancy]
    analyst_notes: str = ""
    is_consistent: bool = True
    trust_score: float = 1.0

    def __post_init__(self):
        self.is_consistent = len(self.discrepancies) == 0
        if self.discrepancies:
            # Compute trust score based on discrepancy severity
            critical_count = sum(1 for d in self.discrepancies if d.severity == Severity.CRITICAL)
            major_count = sum(1 for d in self.discrepancies if d.severity == Severity.MAJOR)
            minor_count = sum(1 for d in self.discrepancies if d.severity == Severity.MINOR)

            # Reduce trust score based on discrepancies
            self.trust_score = max(0.0, 1.0 - (critical_count * 0.3) - (major_count * 0.1) - (minor_count * 0.02))


@dataclass
class OperatorOutput:
    """Output from a single operator."""
    operator_name: str  # "A" or "B"
    strategy: str       # "structure-first" or "narrative-first"
    raw_answer: str
    confidence: float
    evidence_nodes: List[EvidenceNode] = None

    def __post_init__(self):
        if self.evidence_nodes is None:
            self.evidence_nodes = []


# Type guard functions
def is_fiscal_period(value: Any) -> bool:
    """Check if value is a FiscalPeriod."""
    return isinstance(value, FiscalPeriod)


def is_financial_value(value: Any) -> bool:
    """Check if value is a FinancialValue."""
    return isinstance(value, FinancialValue)


def is_direction(value: Any) -> bool:
    """Check if value is a Direction."""
    return isinstance(value, Direction)
