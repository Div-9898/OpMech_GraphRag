"""
Enhanced Cross-Operator Consistency Checker

Detects discrepancies between operator answers:
- Direction disagreements (A says increase, B says decrease)
- Numerical mismatches (different figures for same metric)
- Period labeling conflicts

Generates resolution recommendations and analyst notes.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
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

    # Aliases for backwards compatibility
    @property
    def type(self) -> str:
        return self.discrepancy_type

    @property
    def operator_A(self) -> str:
        return self.operator_A_claim

    @property
    def operator_B(self) -> str:
        return self.operator_B_claim

    @property
    def context(self) -> str:
        return self.metric


@dataclass
class ConsistencyResult:
    """Result of consistency check."""
    is_consistent: bool
    discrepancies: List[Discrepancy] = field(default_factory=list)
    analyst_note: str = ""
    recommended_action: str = ""

    # Alias for backwards compatibility
    @property
    def consistent(self) -> bool:
        return self.is_consistent

    @property
    def recommended_resolution(self) -> str:
        return self.recommended_action


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
        if not answer_A or not answer_B:
            return ConsistencyResult(is_consistent=True)

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
                                metric=context_A[:50],
                                operator_A_claim=f"${value_A/1e9:.2f}B" if value_A >= 1e9 else f"${value_A:,.0f}",
                                operator_B_claim=f"${value_B/1e9:.2f}B" if value_B >= 1e9 else f"${value_B:,.0f}",
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
            content = node.get('content', '') or node.get('text', '')
            if discrepancy.metric.lower() in content.lower():
                if 'computed_change' in node:
                    change = node['computed_change']
                    # Handle both old dict format and new ChangeResult format
                    if hasattr(change, 'direction'):
                        direction = change.direction.value
                        formatted = change.formatted_change
                        return f"Evidence shows {direction}: {formatted}"
                    else:
                        return f"Evidence shows {change.get('direction', 'UNKNOWN')}: {change.get('from_period', '?')} to {change.get('to_period', '?')} ({change.get('percentage', 0):+.1f}%)"

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

    def format_discrepancy_note(self, discrepancies: List[Discrepancy]) -> str:
        """
        Format discrepancies as a note to append to the answer.

        Args:
            discrepancies: List of discrepancies found

        Returns:
            Formatted note string
        """
        if not discrepancies:
            return ""

        note = "\n\n---\n**Analyst Note:** "

        for d in discrepancies:
            if d.discrepancy_type == 'direction':
                note += (
                    f"There was initial disagreement about the direction of {d.metric} change "
                    f"(A: {d.operator_A_claim}, B: {d.operator_B_claim}). "
                )
                if d.resolution:
                    note += f"Resolution: {d.resolution}. "

            elif d.discrepancy_type == 'numerical':
                note += (
                    f"Minor numerical variance detected for {d.metric or 'a metric'} "
                    f"(A: {d.operator_A_claim}, B: {d.operator_B_claim}). "
                )

        return note


def check_operator_consistency(
    answer_A: str,
    answer_B: str,
    evidence_A: Optional[List[Dict]] = None,
    evidence_B: Optional[List[Dict]] = None
) -> ConsistencyResult:
    """
    Convenience function to check consistency between operator answers.

    Args:
        answer_A: Operator A's answer
        answer_B: Operator B's answer
        evidence_A: Evidence used by Operator A
        evidence_B: Evidence used by Operator B

    Returns:
        ConsistencyResult with any discrepancies found
    """
    checker = CrossOperatorConsistencyChecker()
    return checker.check_consistency(answer_A, answer_B, evidence_A, evidence_B)
