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
from dataclasses import dataclass, field
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
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence_adjustment: float = 0.0
    corrected_answer: Optional[str] = None


class AnswerValidator:
    """
    Validates operator answers for factual consistency.

    Catches:
    - Temporal direction errors (claimed increase but numbers show decrease)
    - Numerical mismatches (wrong figures)
    - Period labeling errors (FY2022 vs FY2023 confusion)
    - Metric type errors (percentage points vs percentage change)
    - BUG 1 FIX: Generic period labels (FY1, FY2, etc.)
    """

    # Confidence penalties for different issue types
    SEVERITY_PENALTIES = {
        'critical': 0.20,
        'warning': 0.10,
        'info': 0.02,
    }

    # BUG 1 FIX: Forbidden generic period labels
    FORBIDDEN_GENERIC_LABELS = [
        r'\bFY1\b',
        r'\bFY2\b',
        r'\bFY3\b',
        r'\bFY4\b',
        r'\bFY5\b',
        r'\bPeriod\s*1\b',
        r'\bPeriod\s*2\b',
        r'\bearlier period\b',
        r'\blater period\b',
        r'\bprevious period\b',
        r'\bprior period\b',
    ]

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

        if not answer:
            return ValidationResult(is_valid=True)

        # BUG 1 FIX: Check for forbidden generic period labels
        generic_label_issues = self._check_generic_period_labels(answer)
        issues.extend(generic_label_issues)

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

        # Validate against pre-computed changes in evidence
        evidence_issues = self._validate_against_evidence_changes(answer, evidence)
        issues.extend(evidence_issues)

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
            r'\$?([\d,.]+)\s*[BbMm]?\w*\s+(?:in\s+)?(?:FY)?(\d{4}).*?(?:to|->)\s*\$?([\d,.]+)\s*[BbMm]?\w*\s+(?:in\s+)?(?:FY)?(\d{4})',
            # from $XXX to $YYY (FYxxxx to FYyyyy)
            r'from\s+\$?([\d,.]+)\s*[BbMm]?\s+to\s+\$?([\d,.]+)\s*[BbMm]?.*?(?:FY)?(\d{4}).*?(?:FY)?(\d{4})',
            # XXX% in FYxxxx to YYY% in FYyyyy (percentages)
            r'([\d.]+)\s*%?\s+(?:in\s+)?(?:FY)?(\d{4}).*?(?:to)\s*([\d.]+)\s*%?\s+(?:in\s+)?(?:FY)?(\d{4})',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, answer, re.IGNORECASE):
                groups = match.groups()

                # Parse based on pattern type
                if len(groups) == 4:
                    value1 = self._parse_number(groups[0])
                    value2 = self._parse_number(groups[2] if groups[1].isdigit() else groups[1])

                    year1 = int(groups[1]) if groups[1].isdigit() else int(groups[2])
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

        # Also check for simpler patterns like "increased from $X to $Y"
        simple_pattern = r'(increas\w+|decreas\w+|grew|declined?|fell|rose)\s+(?:from\s+)?\$?([\d,.]+)\s*[BbMm]?\s*(?:to\s+)\$?([\d,.]+)\s*[BbMm]?'

        for match in re.finditer(simple_pattern, answer, re.IGNORECASE):
            direction_word = match.group(1).lower()
            value1 = self._parse_number(match.group(2))
            value2 = self._parse_number(match.group(3))

            claimed_direction = 'increase' if any(w in direction_word for w in ['increas', 'grew', 'rose']) else 'decrease'
            actual_direction = 'increase' if value2 > value1 else 'decrease' if value2 < value1 else 'unchanged'

            claims.append({
                'text': match.group(0),
                'from_value': value1,
                'from_year': None,
                'to_value': value2,
                'to_year': None,
                'claimed_direction': claimed_direction,
                'actual_direction': actual_direction,
                'context': match.group(0),
                'is_percentage': False,
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
                from_fmt = f"${from_val/1e9:.2f}B"
                to_fmt = f"${to_val/1e9:.2f}B"
            elif from_val >= 1e6:  # Millions
                from_fmt = f"${from_val/1e6:.2f}M"
                to_fmt = f"${to_val/1e6:.2f}M"
            else:
                from_fmt = f"${from_val:,.0f}"
                to_fmt = f"${to_val:,.0f}"

            pct_change = ((to_val - from_val) / from_val * 100) if from_val != 0 else 0

            from_year = claim.get('from_year')
            to_year = claim.get('to_year')
            period_str = f"(FY{from_year}) to (FY{to_year})" if from_year and to_year else ""

            issues.append(ValidationIssue(
                issue_type='direction_error',
                description=f"Direction error: Claimed {claimed} but {from_fmt} -> {to_fmt} is actually a {actual} ({pct_change:+.1f}%)",
                severity='critical',
                correction=f"{from_fmt} {period_str} to {to_fmt}, a {actual} of {abs(pct_change):.1f}%",
            ))

        # Check if years might be swapped
        from_year = claim.get('from_year')
        to_year = claim.get('to_year')
        if from_year and to_year and from_year > to_year:
            issues.append(ValidationIssue(
                issue_type='period_order',
                description=f"Period order issue: Earlier period (FY{from_year}) should come before later period (FY{to_year})",
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

    def _check_generic_period_labels(self, answer: str) -> List[ValidationIssue]:
        """
        BUG 1 FIX: Check for forbidden generic period labels.

        These labels are ambiguous and should never appear in answers:
        - FY1, FY2, FY3, FY4, FY5
        - Period1, Period2
        - "earlier period", "later period", "previous period", "prior period"

        Answers should use explicit labels: FY2022, Q1-FY2024, etc.
        """
        issues = []

        for pattern in self.FORBIDDEN_GENERIC_LABELS:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            if matches:
                for match in matches:
                    issues.append(ValidationIssue(
                        issue_type='generic_period_label',
                        description=(
                            f"Generic period label '{match}' used - "
                            f"must use explicit labels like FY2022, Q1-FY2024"
                        ),
                        severity='warning',
                        correction="Replace with explicit fiscal year (e.g., FY2022, FY2023)"
                    ))

        return issues

    def _validate_against_evidence_changes(
        self,
        answer: str,
        evidence: List[Dict]
    ) -> List[ValidationIssue]:
        """Validate answer against pre-computed changes in evidence."""
        issues = []

        for node in evidence:
            if 'computed_change' not in node:
                continue

            change = node['computed_change']

            # Handle both old dict format and new ChangeResult format
            if hasattr(change, 'direction'):
                evidence_direction = change.direction.value.lower()
                percentage = change.percentage_change
            else:
                evidence_direction = change.get('direction', '').lower()
                percentage = change.get('percentage', 0)

            # Check if answer mentions this metric with wrong direction
            content = node.get('content', '') or node.get('text', '')

            # Extract metric keywords
            metric_keywords = []
            if 'revenue' in content.lower():
                metric_keywords.append('revenue')
            if 'sales' in content.lower():
                metric_keywords.append('sales')
            if 'iphone' in content.lower():
                metric_keywords.append('iphone')
            if 'margin' in content.lower():
                metric_keywords.append('margin')

            for keyword in metric_keywords:
                if keyword in answer.lower():
                    # Check if answer has opposite direction
                    answer_lower = answer.lower()
                    keyword_idx = answer_lower.find(keyword)

                    if keyword_idx >= 0:
                        # Look at context around keyword
                        start = max(0, keyword_idx - 100)
                        end = min(len(answer), keyword_idx + 150)
                        context = answer_lower[start:end]

                        answer_direction = self._detect_direction(context)

                        if answer_direction and answer_direction != evidence_direction:
                            pct_str = f"{percentage:+.1f}%" if percentage else ""
                            issues.append(ValidationIssue(
                                issue_type='evidence_mismatch',
                                description=(
                                    f"Direction mismatch for '{keyword}': "
                                    f"Answer claims {answer_direction} but evidence shows {evidence_direction} "
                                    f"({pct_str})"
                                ),
                                severity='critical',
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
