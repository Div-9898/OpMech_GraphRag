"""
Financial Value Model - Type-safe currency handling.
CRITICAL: This prevents confusion between years and dollar amounts.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
import re

from src.financial_models.fiscal_period import FiscalPeriod


@dataclass(frozen=True)
class FinancialValue:
    """
    Immutable financial value.

    CRITICAL INVARIANTS:
    1. amount is always stored in base units (dollars, not billions)
    2. source tracks where this value came from
    3. confidence indicates reliability (1.0 = XBRL verified)
    4. Can NEVER be confused with a year or period
    """
    amount: Decimal  # Always in base units (dollars)
    currency: str = "USD"
    period: Optional[FiscalPeriod] = None
    source: Optional[str] = None  # "XBRL", "10-K text", etc.
    confidence: float = 1.0

    @property
    def in_millions(self) -> Decimal:
        return self.amount / Decimal("1000000")

    @property
    def in_billions(self) -> Decimal:
        return self.amount / Decimal("1000000000")

    def format(self, precision: int = 2) -> str:
        """
        Format for display.
        ALWAYS includes $ to distinguish from other numbers.
        """
        billions = float(self.in_billions)
        if abs(billions) >= 1:
            return f"${billions:,.{precision}f}B"

        millions = float(self.in_millions)
        if abs(millions) >= 1:
            return f"${millions:,.{precision}f}M"

        return f"${float(self.amount):,.{precision}f}"

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return f"FinancialValue({self.format()}, period={self.period})"

    def __hash__(self) -> int:
        return hash((self.amount, self.currency, self.period, self.source))

    def __add__(self, other: 'FinancialValue') -> 'FinancialValue':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} vs {other.currency}")
        return FinancialValue(
            amount=self.amount + other.amount,
            currency=self.currency,
            source=f"{self.source or 'unknown'}+{other.source or 'unknown'}",
            confidence=min(self.confidence, other.confidence)
        )

    def __sub__(self, other: 'FinancialValue') -> 'FinancialValue':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} vs {other.currency}")
        return FinancialValue(
            amount=self.amount - other.amount,
            currency=self.currency,
            source=f"{self.source or 'unknown'}-{other.source or 'unknown'}",
            confidence=min(self.confidence, other.confidence)
        )

    @classmethod
    def from_billions(
        cls,
        amount: float,
        period: Optional[FiscalPeriod] = None,
        source: Optional[str] = None,
        confidence: float = 1.0
    ) -> 'FinancialValue':
        """Create from billions (e.g., 383.29 for $383.29B)"""
        return cls(
            amount=Decimal(str(amount)) * Decimal("1000000000"),
            period=period,
            source=source,
            confidence=confidence
        )

    @classmethod
    def from_millions(
        cls,
        amount: float,
        period: Optional[FiscalPeriod] = None,
        source: Optional[str] = None,
        confidence: float = 1.0
    ) -> 'FinancialValue':
        """Create from millions (e.g., 383290 for $383.29B)"""
        return cls(
            amount=Decimal(str(amount)) * Decimal("1000000"),
            period=period,
            source=source,
            confidence=confidence
        )

    @classmethod
    def from_raw(
        cls,
        amount: float,
        period: Optional[FiscalPeriod] = None,
        source: Optional[str] = None,
        confidence: float = 1.0
    ) -> 'FinancialValue':
        """Create from raw dollar amount"""
        return cls(
            amount=Decimal(str(amount)),
            period=period,
            source=source,
            confidence=confidence
        )

    @classmethod
    def parse(cls, text: str, period: Optional[FiscalPeriod] = None) -> Optional['FinancialValue']:
        """
        Parse financial value from text.

        CRITICAL: Only parses things that look like money.
        Will NOT parse bare years like "2023" or "2024".

        Accepted formats:
        - "$383.29B", "$383.29 billion"
        - "$383,290M", "$383,290 million"
        - "$383,290,000,000"
        - "383.29B" (with B/M suffix, no $)
        """
        if not text:
            return None

        text = text.strip()

        # Pattern 1: $X.XXB or $X.XX billion
        billions_match = re.search(
            r'\$?\s*([\d,]+\.?\d*)\s*(?:B|billion|bn)\b',
            text, re.IGNORECASE
        )
        if billions_match:
            amount_str = billions_match.group(1).replace(',', '')
            try:
                return cls.from_billions(float(amount_str), period=period)
            except (ValueError, TypeError):
                pass

        # Pattern 2: $X.XXM or $X.XX million
        millions_match = re.search(
            r'\$?\s*([\d,]+\.?\d*)\s*(?:M|million|mn)\b',
            text, re.IGNORECASE
        )
        if millions_match:
            amount_str = millions_match.group(1).replace(',', '')
            try:
                return cls.from_millions(float(amount_str), period=period)
            except (ValueError, TypeError):
                pass

        # Pattern 3: $X,XXX,XXX,XXX (full dollar amount with $)
        # MUST have $ to avoid parsing years
        dollars_match = re.search(
            r'\$\s*([\d,]+\.?\d*)\b',
            text
        )
        if dollars_match:
            amount_str = dollars_match.group(1).replace(',', '')
            try:
                amount = Decimal(amount_str)
                # Sanity check: if it looks like a year, reject it
                if 1900 <= float(amount) <= 2100:
                    return None
                return cls(amount=amount, period=period)
            except (ValueError, TypeError):
                pass

        return None


@dataclass
class FinancialChange:
    """
    Represents a change between two periods.
    Pre-computed to avoid LLM calculation errors.
    """
    metric_name: str
    from_period: FiscalPeriod
    to_period: FiscalPeriod
    from_value: FinancialValue
    to_value: FinancialValue

    @property
    def absolute_change(self) -> Decimal:
        """Change in base units"""
        return self.to_value.amount - self.from_value.amount

    @property
    def absolute_change_formatted(self) -> str:
        """Formatted absolute change"""
        change_value = FinancialValue(amount=abs(self.absolute_change))
        return change_value.format()

    @property
    def percentage_change(self) -> Optional[float]:
        """Percentage change"""
        if self.from_value.amount == 0:
            return None
        return float(
            (self.to_value.amount - self.from_value.amount)
            / self.from_value.amount * 100
        )

    @property
    def direction(self) -> str:
        """
        Direction of change.
        CRITICAL: Computed from actual values, not inferred from text.
        """
        diff = self.absolute_change
        if diff > 0:
            return "INCREASE"
        elif diff < 0:
            return "DECREASE"
        return "UNCHANGED"

    @property
    def is_significant(self) -> bool:
        """Whether the change is significant (> 1%)"""
        pct = self.percentage_change
        if pct is None:
            return False
        return abs(pct) > 1.0

    @property
    def is_favorable(self) -> Optional[bool]:
        """Whether change is favorable (for revenue/profit metrics)"""
        favorable_increase = ['revenue', 'sales', 'profit', 'income', 'margin', 'eps']
        favorable_decrease = ['cost', 'expense', 'loss', 'debt']

        name_lower = self.metric_name.lower()

        if any(f in name_lower for f in favorable_increase):
            return self.direction == "INCREASE"
        if any(f in name_lower for f in favorable_decrease):
            return self.direction == "DECREASE"
        return None

    def format(self) -> str:
        """
        Format change for display.
        This is the AUTHORITATIVE description - LLM should use this verbatim.
        """
        pct = self.percentage_change
        pct_str = f" ({pct:+.1f}%)" if pct is not None else ""

        abs_change = FinancialValue(amount=abs(self.absolute_change))

        favorable_str = ""
        if self.is_favorable is not None:
            favorable_str = " [FAVORABLE]" if self.is_favorable else " [UNFAVORABLE]"

        return (
            f"{self.metric_name}: {self.direction} of {abs_change.format()}{pct_str}\n"
            f"  {self.from_period.label}: {self.from_value.format()}\n"
            f"  {self.to_period.label}: {self.to_value.format()}{favorable_str}"
        )

    def format_concise(self) -> str:
        """Concise one-line format"""
        pct = self.percentage_change
        pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
        sign = "+" if self.absolute_change > 0 else ""
        abs_change = FinancialValue(amount=abs(self.absolute_change))

        return (
            f"{self.metric_name}: {self.from_period.label} {self.from_value.format()} -> "
            f"{self.to_period.label} {self.to_value.format()} "
            f"({sign}{abs_change.format()}{pct_str}, {self.direction})"
        )

    def __str__(self) -> str:
        return self.format_concise()

    def __repr__(self) -> str:
        return f"FinancialChange({self.metric_name}, {self.from_period} -> {self.to_period}, {self.direction})"
