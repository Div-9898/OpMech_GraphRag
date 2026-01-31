"""
Robust Evidence Extractor for OpMech Production System

This module extracts structured information from raw evidence text.

KEY PRINCIPLE: Everything is typed. Years are FiscalPeriods.
Money is FinancialValues. They can never be confused.

The extractor uses strict pattern separation:
- MONEY_PATTERN only matches dollar amounts (must have $ or B/M suffix)
- FISCAL_YEAR_PATTERN only matches fiscal periods (FY, Q, fiscal year)
- YEAR_ONLY_PATTERN matches standalone years (verified NOT to be money)
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
import re
from decimal import Decimal

from .type_safe_models import (
    FiscalPeriod,
    FinancialValue,
    EvidenceNode,
    Direction,
)
from .company_config import get_company_config, FiscalConfig


class EvidenceExtractor:
    """
    Extracts structured information from raw evidence.

    KEY PRINCIPLE: Everything is typed. Years are FiscalPeriods.
    Money is FinancialValues. They can never be confused.
    """

    # These patterns ONLY match dollar amounts
    MONEY_PATTERN = re.compile(
        r'\$\s*([\d,]+\.?\d*)\s*(billion|million|B|M|bn|mn)?',
        re.IGNORECASE
    )

    # Additional money pattern without $ but WITH required scale
    MONEY_SCALE_PATTERN = re.compile(
        r'([\d,]+\.?\d*)\s*(billion|B|million|M)\b',
        re.IGNORECASE
    )

    # These patterns ONLY match fiscal periods
    FISCAL_YEAR_PATTERN = re.compile(
        r'(?:fiscal\s*(?:year\s*)?|FY\s*)(20\d{2})\b',
        re.IGNORECASE
    )

    # Quarter pattern
    QUARTER_PATTERN = re.compile(
        r'Q([1-4])\s*[-\s]?(?:FY\s*)?(20\d{2})',
        re.IGNORECASE
    )

    # IMPORTANT: This pattern matches years that are NOT dollar amounts
    # The negative lookahead ensures we don't match "2023 billion" etc.
    YEAR_ONLY_PATTERN = re.compile(
        r'\b(20\d{2})\b(?!\s*(?:billion|million|B|M|\$))',
        re.IGNORECASE
    )

    def __init__(self, company: str = "AAPL"):
        """
        Initialize extractor for a specific company.

        Args:
            company: Company ticker for fiscal year configuration
        """
        self.company = company
        self.fiscal_config = get_company_config(company)

    def extract_from_text(self, text: str, source: str = "") -> EvidenceNode:
        """
        Extract structured information from text.

        Args:
            text: Raw text content
            source: Source document identifier

        Returns:
            EvidenceNode with typed periods and values
        """
        node = EvidenceNode(
            id=f"node_{abs(hash(text)) % 100000}",
            content=text,
            source_document=source,
            node_type="text"
        )

        # Extract periods FIRST (so we don't confuse years with money)
        node.periods = self._extract_periods(text)

        # Extract financial values (only things with $ or B/M)
        node.values = self._extract_values(text, node.periods)

        return node

    def _extract_periods(self, text: str) -> List[FiscalPeriod]:
        """
        Extract fiscal periods from text.

        CRITICAL: Returns FiscalPeriod objects, not strings or numbers.
        """
        periods: Set[FiscalPeriod] = set()

        # Match FY2023 style
        for match in self.FISCAL_YEAR_PATTERN.finditer(text):
            year = int(match.group(1))
            periods.add(FiscalPeriod(year=year, company=self.company))

        # Match Q1-2023 style
        for match in self.QUARTER_PATTERN.finditer(text):
            quarter = int(match.group(1))
            year = int(match.group(2))
            periods.add(FiscalPeriod(year=year, quarter=quarter, company=self.company))

        # Match standalone years (but verify they're not dollar amounts)
        for match in self.YEAR_ONLY_PATTERN.finditer(text):
            year_str = match.group(1)
            year = int(year_str)

            # Verify this isn't part of a dollar amount
            start = match.start()
            prefix = text[max(0, start - 5):start]

            # Skip if preceded by $ or looks like money
            if '$' in prefix:
                continue

            # Additional check: look at suffix
            end = match.end()
            suffix = text[end:min(len(text), end + 10)].lower()
            if any(s in suffix for s in ['billion', 'million', ' b', ' m']):
                continue

            # Check if this year appears in context that suggests fiscal year
            context_start = max(0, start - 50)
            context_end = min(len(text), end + 50)
            context = text[context_start:context_end].lower()

            fiscal_indicators = ['fiscal', 'fy', 'year ended', 'quarter', 'annual', 'period']
            if any(ind in context for ind in fiscal_indicators):
                periods.add(FiscalPeriod(year=year, company=self.company))

        return sorted(list(periods), key=lambda p: p.sort_key)

    def _extract_values(
        self,
        text: str,
        periods: List[FiscalPeriod]
    ) -> List[FinancialValue]:
        """
        Extract financial values from text.

        CRITICAL: Uses FinancialValue.parse() which ONLY accepts money formats.
        Will NOT parse bare years like "2023" as money.
        """
        values: List[FinancialValue] = []
        seen_amounts: Set[Decimal] = set()

        # Find all dollar amounts with $
        for match in self.MONEY_PATTERN.finditer(text):
            full_match = match.group(0)
            value = FinancialValue.parse(full_match)

            if value and value.normalized_amount not in seen_amounts:
                seen_amounts.add(value.normalized_amount)

                # Associate with nearest period if available
                if periods:
                    # Find the period mentioned closest to this value
                    nearest_period = self._find_nearest_period(text, match.start(), periods)
                    if nearest_period:
                        # Create new value with period
                        value = FinancialValue(
                            amount=value.amount,
                            scale=value.scale,
                            period=nearest_period,
                            source=full_match,
                            confidence=0.9
                        )

                values.append(value)

        # Find amounts with scale suffix (without $)
        for match in self.MONEY_SCALE_PATTERN.finditer(text):
            # Make sure this isn't already captured by the $ pattern
            start = match.start()
            if start > 0 and text[start - 1] == '$':
                continue

            full_match = match.group(0)

            # Parse the value
            amount_str = match.group(1).replace(',', '')
            scale_str = match.group(2).upper()

            try:
                amount = Decimal(amount_str)

                # CRITICAL: Skip if amount looks like a year
                if Decimal("1900") <= amount <= Decimal("2100"):
                    continue

                scale_map = {
                    "B": "billions", "BILLION": "billions",
                    "M": "millions", "MILLION": "millions",
                }
                scale = scale_map.get(scale_str[:1].upper(), "units")

                value = FinancialValue(
                    amount=amount,
                    scale=scale,
                    source=full_match,
                    confidence=0.8  # Slightly lower confidence without $
                )

                if value.normalized_amount not in seen_amounts:
                    seen_amounts.add(value.normalized_amount)

                    # Associate with nearest period
                    if periods:
                        nearest_period = self._find_nearest_period(text, match.start(), periods)
                        if nearest_period:
                            value = FinancialValue(
                                amount=value.amount,
                                scale=value.scale,
                                period=nearest_period,
                                source=full_match,
                                confidence=0.8
                            )

                    values.append(value)

            except Exception:
                continue

        return values

    def _find_nearest_period(
        self,
        text: str,
        value_position: int,
        periods: List[FiscalPeriod]
    ) -> Optional[FiscalPeriod]:
        """
        Find the fiscal period mentioned nearest to a value position.
        """
        if not periods:
            return None

        # Find all period mentions and their positions
        period_positions: List[Tuple[FiscalPeriod, int]] = []

        for period in periods:
            # Search for this period in text
            patterns = [
                f"FY{period.year}",
                f"FY {period.year}",
                f"fiscal year {period.year}",
                f"fiscal {period.year}",
                str(period.year),
            ]
            if period.quarter:
                patterns.extend([
                    f"Q{period.quarter}-{period.year}",
                    f"Q{period.quarter} {period.year}",
                    f"Q{period.quarter}-FY{period.year}",
                ])

            for pattern in patterns:
                for match in re.finditer(re.escape(pattern), text, re.IGNORECASE):
                    period_positions.append((period, match.start()))

        if not period_positions:
            return periods[0] if periods else None

        # Find nearest period
        nearest = min(period_positions, key=lambda x: abs(x[1] - value_position))
        return nearest[0]

    def extract_direction_claims(self, text: str) -> List[Dict]:
        """
        Extract direction claims from text.

        Returns claims as typed Direction enums with their metrics.
        """
        claims = []

        # Patterns for direction claims
        increase_words = ['increased', 'grew', 'rose', 'gained', 'improved', 'higher', 'up']
        decrease_words = ['decreased', 'declined', 'fell', 'dropped', 'lower', 'down', 'reduced']

        direction_pattern = re.compile(
            r'(\w+(?:\s+\w+)?)\s+(' + '|'.join(increase_words + decrease_words) + r')\b',
            re.IGNORECASE
        )

        for match in direction_pattern.finditer(text):
            metric = match.group(1).lower().strip()
            direction_word = match.group(2).lower()

            # Determine direction
            if direction_word in increase_words:
                direction = Direction.INCREASE
            else:
                direction = Direction.DECREASE

            claims.append({
                'metric': metric,
                'direction': direction,
                'source': match.group(0),
                'position': match.start()
            })

        return claims

    def extract_value_claims(self, text: str) -> List[Dict]:
        """
        Extract value claims (metric = value) from text.
        """
        claims = []

        # Pattern: "metric was/is/of $XXX"
        value_pattern = re.compile(
            r'(\w+(?:\s+\w+)?)\s+(?:was|is|of|totaled|reached)\s+(\$[\d,.]+\s*(?:B|M|billion|million)?)',
            re.IGNORECASE
        )

        for match in value_pattern.finditer(text):
            metric = match.group(1).lower().strip()
            value_str = match.group(2)

            value = FinancialValue.parse(value_str)
            if value:
                claims.append({
                    'metric': metric,
                    'value': value,
                    'source': match.group(0),
                    'position': match.start()
                })

        return claims


class EvidenceSet:
    """
    Collection of evidence nodes with helper methods.
    """

    def __init__(self, nodes: List[EvidenceNode] = None):
        self.nodes = nodes or []

    def add(self, node: EvidenceNode):
        """Add a node to the set."""
        self.nodes.append(node)

    def get_xbrl_nodes(self) -> List[EvidenceNode]:
        """Get nodes that came from XBRL data (ground truth)."""
        return [n for n in self.nodes if n.node_type == "xbrl" or n.xbrl_tag]

    def get_text_nodes(self) -> List[EvidenceNode]:
        """Get nodes that are text content."""
        return [n for n in self.nodes if n.node_type == "text"]

    def get_all_periods(self) -> List[FiscalPeriod]:
        """Get all unique fiscal periods across all nodes."""
        periods: Set[FiscalPeriod] = set()
        for node in self.nodes:
            periods.update(node.periods)
        return sorted(list(periods), key=lambda p: p.sort_key)

    def get_values_for_period(self, period: FiscalPeriod) -> List[FinancialValue]:
        """Get all values associated with a specific period."""
        values = []
        for node in self.nodes:
            for value in node.values:
                if value.period == period:
                    values.append(value)
        return values

    def get_all_computed_changes(self) -> List:
        """Get all pre-computed changes from all nodes."""
        changes = []
        for node in self.nodes:
            changes.extend(node.computed_changes)
        return changes


def create_evidence_extractor(company: str = "AAPL") -> EvidenceExtractor:
    """
    Factory function to create an evidence extractor.

    Args:
        company: Company ticker or name

    Returns:
        Configured EvidenceExtractor instance
    """
    # Map company names to tickers
    name_to_ticker = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "meta": "META",
        "nvidia": "NVDA",
        "walmart": "WMT",
    }

    ticker = name_to_ticker.get(company.lower(), company.upper())
    return EvidenceExtractor(company=ticker)
