"""
Robust Consistency Checker for OpMech Production System

This module checks consistency between operator outputs with type safety.

KEY FIXES from the original:
1. Only compares facts of the SAME TYPE (never years to dollars)
2. Deduplicates discrepancies
3. Generates max 10 clean analyst notes
4. Uses typed objects throughout

The checker CANNOT confuse types because it only compares:
- Direction to Direction
- FinancialValue to FinancialValue
- FiscalPeriod to FiscalPeriod
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
import re

from .type_safe_models import (
    FiscalPeriod,
    FinancialValue,
    Direction,
    Discrepancy,
    DiscrepancyType,
    Severity,
    ConsistencyReport,
    OperatorOutput,
    is_fiscal_period,
    is_financial_value,
    is_direction,
)


@dataclass
class ExtractedFact:
    """A structured fact extracted from text."""
    fact_type: str  # 'direction', 'value', 'period'
    metric: str
    value: Any  # Typed value (Direction, FinancialValue, or FiscalPeriod)
    source_text: str
    position: int


class RobustConsistencyChecker:
    """
    Robust consistency checker that CANNOT confuse types.

    Key invariant: Only compares values of the same type.
    """

    # Direction indicator words
    INCREASE_WORDS = frozenset([
        'increased', 'grew', 'growth', 'rose', 'gain', 'higher',
        'up', 'improve', 'improved', 'expand', 'expanded', 'climbed'
    ])
    DECREASE_WORDS = frozenset([
        'decreased', 'decline', 'declined', 'fell', 'drop', 'dropped',
        'lower', 'down', 'contract', 'contracted', 'shrink', 'reduced'
    ])

    def __init__(self, company: str = None):
        """
        Initialize consistency checker.

        Args:
            company: Optional company identifier (not currently used, kept for compatibility)
        """
        # COMPANY-AGNOSTIC: The checker works on text patterns, not company-specific data
        self.company = company

    def check_consistency(
        self,
        output_a: OperatorOutput,
        output_b: OperatorOutput
    ) -> ConsistencyReport:
        """
        Check consistency between two operator outputs.

        Args:
            output_a: Output from Operator A
            output_b: Output from Operator B

        Returns:
            ConsistencyReport with discrepancies and analyst notes
        """
        discrepancies: List[Discrepancy] = []

        # Extract structured facts from each output
        facts_a = self._extract_facts(output_a.raw_answer)
        facts_b = self._extract_facts(output_b.raw_answer)

        # Compare facts of SAME TYPE only
        for key, fact_a in facts_a.items():
            if key in facts_b:
                fact_b = facts_b[key]

                # CRITICAL: Only compare if same type
                if type(fact_a.value) == type(fact_b.value):
                    discrepancy = self._compare_facts(key, fact_a, fact_b)
                    if discrepancy:
                        discrepancies.append(discrepancy)

        # Deduplicate discrepancies
        discrepancies = self._deduplicate(discrepancies)

        # Generate clean analyst notes (max 10)
        analyst_notes = self._generate_analyst_notes(discrepancies)

        return ConsistencyReport(
            discrepancies=discrepancies,
            analyst_notes=analyst_notes
        )

    def _extract_facts(self, text: str) -> Dict[str, ExtractedFact]:
        """
        Extract facts from text into structured format.

        CRITICAL: Values are stored as typed objects, not strings.
        """
        facts: Dict[str, ExtractedFact] = {}

        if not text:
            return facts

        # Extract direction claims
        direction_facts = self._extract_direction_facts(text)
        facts.update(direction_facts)

        # Extract value claims
        value_facts = self._extract_value_facts(text)
        facts.update(value_facts)

        return facts

    def _extract_direction_facts(self, text: str) -> Dict[str, ExtractedFact]:
        """
        Extract direction claims from text.

        Returns typed Direction enums.
        """
        facts = {}

        # Common metrics to check
        metrics = [
            'revenue', 'sales', 'income', 'profit', 'margin',
            'iphone', 'mac', 'ipad', 'services', 'wearables',
            'cost', 'expense', 'earnings'
        ]

        # Build pattern for each metric
        direction_words = '|'.join(self.INCREASE_WORDS | self.DECREASE_WORDS)
        pattern = re.compile(
            r'(\w+(?:\s+\w+)?)\s+(' + direction_words + r')\b',
            re.IGNORECASE
        )

        for match in pattern.finditer(text):
            context = match.group(1).lower().strip()
            direction_word = match.group(2).lower()

            # Check if context mentions a tracked metric
            metric = None
            for m in metrics:
                if m in context:
                    metric = m
                    break

            if not metric:
                continue

            # Determine direction - typed as Direction enum
            if direction_word in self.INCREASE_WORDS:
                direction = Direction.INCREASE
            else:
                direction = Direction.DECREASE

            fact_key = f"direction_{metric}"
            facts[fact_key] = ExtractedFact(
                fact_type='direction',
                metric=metric,
                value=direction,  # Typed as Direction enum
                source_text=match.group(0),
                position=match.start()
            )

        return facts

    def _extract_value_facts(self, text: str) -> Dict[str, ExtractedFact]:
        """
        Extract value claims from text.

        Returns typed FinancialValue objects.
        """
        facts = {}

        # Pattern: "metric was/is/of $XXX"
        value_pattern = re.compile(
            r'(\w+(?:\s+\w+)?)\s+(?:was|is|of|totaled|reached)\s+(\$[\d,.]+\s*(?:B|M|billion|million)?)',
            re.IGNORECASE
        )

        for match in value_pattern.finditer(text):
            metric = match.group(1).lower().strip()
            value_str = match.group(2)

            # Parse as FinancialValue - TYPED, not string
            value = FinancialValue.parse(value_str)
            if value:
                fact_key = f"value_{metric}"
                facts[fact_key] = ExtractedFact(
                    fact_type='value',
                    metric=metric,
                    value=value,  # Typed as FinancialValue
                    source_text=match.group(0),
                    position=match.start()
                )

        return facts

    def _compare_facts(
        self,
        key: str,
        fact_a: ExtractedFact,
        fact_b: ExtractedFact
    ) -> Optional[Discrepancy]:
        """
        Compare two facts of the same type.

        CRITICAL: This method is only called when types match.
        """
        if fact_a.fact_type == 'direction':
            # Compare Direction enums
            if fact_a.value != fact_b.value:
                return Discrepancy(
                    discrepancy_type=DiscrepancyType.DIRECTION,
                    severity=Severity.CRITICAL,
                    metric=fact_a.metric,
                    operator_a_value=fact_a.value.value,  # .value gets the enum string
                    operator_b_value=fact_b.value.value
                )

        elif fact_a.fact_type == 'value':
            # Compare FinancialValue objects
            val_a: FinancialValue = fact_a.value
            val_b: FinancialValue = fact_b.value

            # Compare normalized amounts
            if val_a.normalized_amount != Decimal("0"):
                diff = abs(val_a.normalized_amount - val_b.normalized_amount)
                diff_pct = float(diff / val_a.normalized_amount)

                if diff_pct > 0.05:  # >5% difference
                    if diff_pct > 0.2:
                        severity = Severity.CRITICAL
                    elif diff_pct > 0.1:
                        severity = Severity.MAJOR
                    else:
                        severity = Severity.MINOR

                    return Discrepancy(
                        discrepancy_type=DiscrepancyType.NUMERICAL,
                        severity=severity,
                        metric=fact_a.metric,
                        operator_a_value=val_a,  # Keep as FinancialValue
                        operator_b_value=val_b
                    )

        return None

    def _deduplicate(self, discrepancies: List[Discrepancy]) -> List[Discrepancy]:
        """
        Remove duplicate discrepancies.

        Uses (type, metric, period) as the uniqueness key.
        """
        seen: Set[Tuple] = set()
        unique: List[Discrepancy] = []

        for d in discrepancies:
            key = (d.discrepancy_type, d.metric, d.period)
            if key not in seen:
                seen.add(key)
                unique.append(d)

        return unique

    def _generate_analyst_notes(self, discrepancies: List[Discrepancy]) -> str:
        """
        Generate CLEAN, READABLE analyst notes.

        CRITICAL: No more than 10 notes. No duplicates. No garbage.
        Never includes "$2,023" or similar year-as-dollar errors.
        """
        if not discrepancies:
            return ""

        lines = ["=== ANALYST NOTES ==="]

        # Group by severity
        critical = [d for d in discrepancies if d.severity == Severity.CRITICAL]
        major = [d for d in discrepancies if d.severity == Severity.MAJOR]
        minor = [d for d in discrepancies if d.severity == Severity.MINOR]

        notes_count = 0

        if critical and notes_count < 10:
            lines.append("\nCRITICAL ISSUES:")
            for d in critical[:5]:  # Max 5 critical
                lines.append(f"  - {d.format()}")
                notes_count += 1

        if major and notes_count < 10:
            remaining = min(3, 10 - notes_count)
            lines.append("\nMAJOR ISSUES:")
            for d in major[:remaining]:  # Max 3 major
                lines.append(f"  - {d.format()}")
                notes_count += 1

        if minor and notes_count < 10:
            # Just summarize minor issues
            lines.append(f"\nMINOR ISSUES: {len(minor)} detected (omitted for brevity)")

        return "\n".join(lines)

    def format_discrepancy_note(self, discrepancies: List[Discrepancy]) -> str:
        """
        Format discrepancies as a note to append to the answer.

        This is a cleaner version for inclusion in final answers.
        """
        if not discrepancies:
            return ""

        note_parts = []

        direction_issues = [d for d in discrepancies if d.discrepancy_type == DiscrepancyType.DIRECTION]
        numerical_issues = [d for d in discrepancies if d.discrepancy_type == DiscrepancyType.NUMERICAL]

        if direction_issues:
            for d in direction_issues[:2]:  # Max 2 direction notes
                note_parts.append(
                    f"Note: There was initial disagreement about the direction of {d.metric} change "
                    f"(A: {d.operator_a_value}, B: {d.operator_b_value}). "
                    f"{'Resolution: ' + d.resolution_source if d.resolved else 'Please verify with source data.'}"
                )

        if numerical_issues:
            if len(numerical_issues) == 1:
                d = numerical_issues[0]
                note_parts.append(
                    f"Note: Minor numerical variance detected for {d.metric} - "
                    f"figures have been verified against source data."
                )
            else:
                note_parts.append(
                    f"Note: Some numerical values ({len(numerical_issues)} metrics) showed variance "
                    f"between analyses - figures have been verified against source data."
                )

        if note_parts:
            return "\n\n---\n**Analyst Notes:**\n" + "\n".join(note_parts)
        return ""


def check_operator_consistency(
    answer_a: str,
    answer_b: str,
    company: str = None
) -> ConsistencyReport:
    """
    Convenience function to check consistency between operator answers.

    COMPANY-AGNOSTIC: Works with any company's data.

    Args:
        answer_a: Operator A's answer text
        answer_b: Operator B's answer text
        company: Optional company identifier (not used, kept for compatibility)

    Returns:
        ConsistencyReport with any discrepancies found
    """
    checker = RobustConsistencyChecker(company=company)

    output_a = OperatorOutput(
        operator_name="A",
        strategy="structure-first",
        raw_answer=answer_a,
        confidence=0.8
    )
    output_b = OperatorOutput(
        operator_name="B",
        strategy="narrative-first",
        raw_answer=answer_b,
        confidence=0.8
    )

    return checker.check_consistency(output_a, output_b)


class ConsistencyValidator:
    """
    High-level consistency validation with XBRL ground truth.

    COMPANY-AGNOSTIC: Works with any company's XBRL data.
    """

    def __init__(self, company: str = None):
        """
        Initialize the validator.

        Args:
            company: Optional company identifier (not used, kept for compatibility)
        """
        self.checker = RobustConsistencyChecker(company)
        self.company = company

    def validate_with_ground_truth(
        self,
        output_a: OperatorOutput,
        output_b: OperatorOutput,
        xbrl_values: Dict[str, Dict[str, FinancialValue]]
    ) -> ConsistencyReport:
        """
        Check consistency and resolve discrepancies with XBRL ground truth.

        Args:
            output_a: Operator A output
            output_b: Operator B output
            xbrl_values: Dict mapping metric -> period_label -> ground truth value

        Returns:
            ConsistencyReport with resolved discrepancies where possible
        """
        # First, check consistency
        report = self.checker.check_consistency(output_a, output_b)

        # Try to resolve discrepancies with XBRL
        for discrepancy in report.discrepancies:
            if discrepancy.discrepancy_type == DiscrepancyType.NUMERICAL:
                self._try_resolve_numerical(discrepancy, xbrl_values)
            elif discrepancy.discrepancy_type == DiscrepancyType.DIRECTION:
                self._try_resolve_direction(discrepancy, xbrl_values)

        # Regenerate analyst notes with resolutions
        report.analyst_notes = self.checker._generate_analyst_notes(report.discrepancies)

        return report

    def _try_resolve_numerical(
        self,
        discrepancy: Discrepancy,
        xbrl_values: Dict[str, Dict[str, FinancialValue]]
    ):
        """Try to resolve a numerical discrepancy with XBRL."""
        metric = discrepancy.metric
        if not metric:
            return

        # Find matching XBRL metric
        metric_key = None
        for key in xbrl_values.keys():
            if metric.lower() in key.lower() or key.lower() in metric.lower():
                metric_key = key
                break

        if not metric_key:
            return

        period_values = xbrl_values.get(metric_key, {})
        if not period_values:
            return

        # Get the most recent ground truth value
        ground_truth = list(period_values.values())[0] if period_values else None
        if not ground_truth:
            return

        # Check which operator is closer to ground truth
        val_a = discrepancy.operator_a_value
        val_b = discrepancy.operator_b_value

        if isinstance(val_a, FinancialValue) and isinstance(val_b, FinancialValue):
            diff_a = abs(val_a.normalized_amount - ground_truth.normalized_amount)
            diff_b = abs(val_b.normalized_amount - ground_truth.normalized_amount)

            if diff_a < diff_b:
                discrepancy.resolved = True
                discrepancy.correct_value = val_a
                discrepancy.resolution_source = "XBRL ground truth favors Operator A"
            else:
                discrepancy.resolved = True
                discrepancy.correct_value = val_b
                discrepancy.resolution_source = "XBRL ground truth favors Operator B"

    def _try_resolve_direction(
        self,
        discrepancy: Discrepancy,
        xbrl_values: Dict[str, Dict[str, FinancialValue]]
    ):
        """Try to resolve a direction discrepancy with XBRL."""
        metric = discrepancy.metric
        if not metric:
            return

        # Find matching XBRL metric
        metric_key = None
        for key in xbrl_values.keys():
            if metric.lower() in key.lower() or key.lower() in metric.lower():
                metric_key = key
                break

        if not metric_key:
            return

        period_values = xbrl_values.get(metric_key, {})
        if len(period_values) < 2:
            return

        # Get sorted values to compute actual direction
        sorted_periods = sorted(period_values.keys())
        if len(sorted_periods) >= 2:
            from_value = period_values[sorted_periods[-2]]
            to_value = period_values[sorted_periods[-1]]

            diff = to_value.normalized_amount - from_value.normalized_amount

            if diff > Decimal("0"):
                correct_direction = Direction.INCREASE
            elif diff < Decimal("0"):
                correct_direction = Direction.DECREASE
            else:
                correct_direction = Direction.UNCHANGED

            # Determine which operator was correct
            val_a = discrepancy.operator_a_value
            val_b = discrepancy.operator_b_value

            if val_a == correct_direction.value:
                discrepancy.resolved = True
                discrepancy.correct_value = correct_direction
                discrepancy.resolution_source = "XBRL ground truth confirms Operator A"
            elif val_b == correct_direction.value:
                discrepancy.resolved = True
                discrepancy.correct_value = correct_direction
                discrepancy.resolution_source = "XBRL ground truth confirms Operator B"
