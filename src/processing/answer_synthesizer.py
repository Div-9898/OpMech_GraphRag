"""
Answer Synthesizer - Ensures final answer is consistent with evidence.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import re

from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange
from src.data.apple_ground_truth import AppleFinancialLookup


@dataclass
class OperatorOutput:
    """Output from a single operator"""
    operator_name: str
    raw_answer: str
    confidence: float

    # Extracted claims
    direction_claims: List[Dict] = field(default_factory=list)
    value_claims: List[Dict] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating a claim"""
    claim_text: str
    is_valid: bool
    correction: Optional[str] = None
    source: str = ""


@dataclass
class SynthesizedAnswer:
    """Final synthesized answer"""
    answer_text: str
    confidence: float
    validations: List[ValidationResult]
    analyst_notes: str

    # For debugging
    operator_a_output: str = ""
    operator_b_output: str = ""

    # Corrections applied
    corrections_made: List[str] = field(default_factory=list)

    @property
    def has_corrections(self) -> bool:
        return len(self.corrections_made) > 0

    @property
    def validation_rate(self) -> float:
        if not self.validations:
            return 1.0
        valid_count = sum(1 for v in self.validations if v.is_valid)
        return valid_count / len(self.validations)


class AnswerSynthesizer:
    """
    Synthesizes final answer from operator outputs.

    CRITICAL: Validates all claims against ground truth before finalizing.
    """

    def __init__(self, company: str = "AAPL"):
        self.company = company
        self.lookup = AppleFinancialLookup

    def synthesize(
        self,
        operator_a: OperatorOutput,
        operator_b: OperatorOutput,
        evidence_context: str
    ) -> SynthesizedAnswer:
        """
        Synthesize final answer from operator outputs.

        CRITICAL STEPS:
        1. Extract claims from both operators
        2. Validate claims against ground truth
        3. Resolve discrepancies using ground truth
        4. Generate validated final answer
        """
        # Step 1: Extract claims
        claims_a = self._extract_claims(operator_a.raw_answer)
        claims_b = self._extract_claims(operator_b.raw_answer)

        # Step 2: Validate claims
        validations = []
        validations.extend(self._validate_claims(claims_a, "Operator A"))
        validations.extend(self._validate_claims(claims_b, "Operator B"))

        # Step 3: Identify discrepancies
        discrepancies = self._find_discrepancies(claims_a, claims_b)

        # Step 4: Determine which operator to trust
        a_valid_rate = self._compute_validation_rate(validations, "Operator A")
        b_valid_rate = self._compute_validation_rate(validations, "Operator B")

        # Step 5: Generate final answer
        corrections_made = []

        if a_valid_rate > b_valid_rate + 0.1:
            base_answer = operator_a.raw_answer
            confidence = operator_a.confidence * a_valid_rate
        elif b_valid_rate > a_valid_rate + 0.1:
            base_answer = operator_b.raw_answer
            confidence = operator_b.confidence * b_valid_rate
        else:
            # Merge answers
            base_answer = self._merge_answers(operator_a, operator_b, validations)
            confidence = (operator_a.confidence + operator_b.confidence) / 2 * max(a_valid_rate, b_valid_rate)

        # Step 6: Apply corrections
        corrected_answer, new_corrections = self._apply_corrections(base_answer, validations)
        corrections_made.extend(new_corrections)

        # Step 7: Generate analyst notes
        analyst_notes = self._generate_analyst_notes(validations, discrepancies)

        return SynthesizedAnswer(
            answer_text=corrected_answer,
            confidence=confidence,
            validations=validations,
            analyst_notes=analyst_notes,
            operator_a_output=operator_a.raw_answer,
            operator_b_output=operator_b.raw_answer,
            corrections_made=corrections_made
        )

    def _extract_claims(self, text: str) -> List[Dict]:
        """Extract factual claims from text"""
        claims = []

        # Direction claims: "X increased/decreased"
        direction_pattern = re.compile(
            r'(\w+(?:\s+\w+)?)\s+(increased|decreased|grew|declined|rose|fell|unchanged|stable|remained)',
            re.IGNORECASE
        )
        for match in direction_pattern.finditer(text):
            metric = match.group(1)
            direction_word = match.group(2).lower()

            direction = "INCREASE" if direction_word in ['increased', 'grew', 'rose'] else \
                       "DECREASE" if direction_word in ['decreased', 'declined', 'fell'] else \
                       "UNCHANGED"

            claims.append({
                'type': 'direction',
                'metric': metric,
                'claimed_direction': direction,
                'text': match.group(0)
            })

        # Value claims: "X was $Y in FY20XX"
        value_pattern = re.compile(
            r'(\w+(?:\s+\w+)?)\s+(?:was|is|of|:)\s+(\$[\d,.]+\s*(?:B|M|billion|million)?)\s*(?:in|for)?\s*(FY\d{4}|Q\d-FY\d{4}|\d{4})?',
            re.IGNORECASE
        )
        for match in value_pattern.finditer(text):
            metric = match.group(1)
            value_str = match.group(2)
            period_str = match.group(3)

            value = FinancialValue.parse(value_str)
            period = FiscalPeriod.from_string(period_str, self.company) if period_str else None

            if value:
                claims.append({
                    'type': 'value',
                    'metric': metric,
                    'claimed_value': value,
                    'period': period,
                    'text': match.group(0)
                })

        # Percentage claims: "+X%" or "-X%"
        percentage_pattern = re.compile(
            r'([\+\-]?\d+\.?\d*)\s*%',
            re.IGNORECASE
        )
        for match in percentage_pattern.finditer(text):
            pct_value = float(match.group(1))
            claims.append({
                'type': 'percentage',
                'value': pct_value,
                'text': match.group(0)
            })

        return claims

    def _validate_claims(self, claims: List[Dict], source: str) -> List[ValidationResult]:
        """Validate claims against ground truth"""
        results = []

        for claim in claims:
            if claim['type'] == 'value' and claim.get('period'):
                # Try to resolve the metric
                metric = self.lookup.resolve_metric(claim['metric'])
                if metric:
                    is_valid, ground_truth, message = self.lookup.validate_claim(
                        metric,
                        claim['period'],
                        claim['claimed_value']
                    )

                    correction = None
                    if not is_valid and ground_truth:
                        correction = f"{claim['metric']} for {claim['period'].label} should be {ground_truth.format()}"

                    results.append(ValidationResult(
                        claim_text=f"[{source}] {claim['text']}",
                        is_valid=is_valid,
                        correction=correction,
                        source=source
                    ))

            elif claim['type'] == 'direction':
                # Direction claims need period context to validate
                # Try common period pairs
                period_pairs = [
                    (FiscalPeriod(2023, company=self.company), FiscalPeriod(2024, company=self.company)),
                    (FiscalPeriod(2022, company=self.company), FiscalPeriod(2023, company=self.company)),
                ]

                metric = self.lookup.resolve_metric(claim['metric'])
                if metric:
                    for from_period, to_period in period_pairs:
                        is_valid, actual_direction, message = self.lookup.validate_direction_claim(
                            metric,
                            from_period,
                            to_period,
                            claim['claimed_direction']
                        )

                        if actual_direction:
                            correction = None
                            if not is_valid:
                                correction = f"Direction for {claim['metric']} ({from_period.label} to {to_period.label}) should be {actual_direction}"

                            results.append(ValidationResult(
                                claim_text=f"[{source}] {claim['text']}",
                                is_valid=is_valid,
                                correction=correction,
                                source=source
                            ))
                            break  # Found a matching period pair

        return results

    def _find_discrepancies(self, claims_a: List[Dict], claims_b: List[Dict]) -> List[str]:
        """Find discrepancies between operator claims"""
        discrepancies = []

        # Compare direction claims
        directions_a = {c['metric'].lower(): c['claimed_direction'] for c in claims_a if c['type'] == 'direction'}
        directions_b = {c['metric'].lower(): c['claimed_direction'] for c in claims_b if c['type'] == 'direction'}

        for metric in set(directions_a.keys()) & set(directions_b.keys()):
            if directions_a[metric] != directions_b[metric]:
                discrepancies.append(
                    f"Direction discrepancy for {metric}: A says {directions_a[metric]}, B says {directions_b[metric]}"
                )

        # Compare value claims
        values_a = {}
        for c in claims_a:
            if c['type'] == 'value' and c.get('period'):
                key = (c['metric'].lower(), c['period'].label)
                values_a[key] = c['claimed_value']

        values_b = {}
        for c in claims_b:
            if c['type'] == 'value' and c.get('period'):
                key = (c['metric'].lower(), c['period'].label)
                values_b[key] = c['claimed_value']

        for key in set(values_a.keys()) & set(values_b.keys()):
            val_a = values_a[key]
            val_b = values_b[key]
            if val_a.amount != val_b.amount:
                diff_pct = abs(float(val_a.amount - val_b.amount) / float(val_a.amount)) * 100
                if diff_pct > 1:  # More than 1% difference
                    discrepancies.append(
                        f"Value discrepancy for {key[0]} in {key[1]}: A says {val_a.format()}, B says {val_b.format()}"
                    )

        return discrepancies

    def _compute_validation_rate(self, validations: List[ValidationResult], source: str) -> float:
        """Compute validation rate for an operator"""
        source_validations = [v for v in validations if source in v.source]
        if not source_validations:
            return 0.5

        valid_count = sum(1 for v in source_validations if v.is_valid)
        return valid_count / len(source_validations)

    def _merge_answers(
        self,
        operator_a: OperatorOutput,
        operator_b: OperatorOutput,
        validations: List[ValidationResult]
    ) -> str:
        """Merge answers from both operators"""
        # For now, use operator with fewer validation failures
        a_failures = sum(1 for v in validations if "Operator A" in v.source and not v.is_valid)
        b_failures = sum(1 for v in validations if "Operator B" in v.source and not v.is_valid)

        if a_failures <= b_failures:
            return operator_a.raw_answer
        return operator_b.raw_answer

    def _apply_corrections(
        self,
        answer: str,
        validations: List[ValidationResult]
    ) -> Tuple[str, List[str]]:
        """Apply corrections to answer based on validation"""
        corrected = answer
        corrections_made = []

        for validation in validations:
            if not validation.is_valid and validation.correction:
                corrections_made.append(validation.correction)

        # If there are corrections, append them as a note
        if corrections_made:
            corrected += "\n\n---\n**Data Corrections Applied:**\n"
            for correction in corrections_made[:5]:  # Limit to 5
                corrected += f"- {correction}\n"

        return corrected, corrections_made

    def _generate_analyst_notes(
        self,
        validations: List[ValidationResult],
        discrepancies: List[str]
    ) -> str:
        """Generate clean analyst notes"""
        lines = []

        # Validation issues
        failures = [v for v in validations if not v.is_valid]
        if failures:
            lines.append("=== VALIDATION ISSUES ===")
            for f in failures[:5]:  # Max 5
                lines.append(f"* {f.claim_text}")
                if f.correction:
                    lines.append(f"  -> {f.correction}")

        # Discrepancies
        if discrepancies:
            lines.append("\n=== DISCREPANCIES ===")
            for d in discrepancies[:5]:  # Max 5
                lines.append(f"* {d}")

        return "\n".join(lines) if lines else "No issues detected."

    def validate_answer_against_ground_truth(
        self,
        answer: str,
        query: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate an answer against ground truth.
        Returns (is_valid, list of issues)
        """
        issues = []

        # Extract claims from answer
        claims = self._extract_claims(answer)

        # Validate each claim
        for claim in claims:
            if claim['type'] == 'value' and claim.get('period'):
                metric = self.lookup.resolve_metric(claim['metric'])
                if metric:
                    is_valid, ground_truth, message = self.lookup.validate_claim(
                        metric,
                        claim['period'],
                        claim['claimed_value']
                    )
                    if not is_valid and ground_truth:
                        issues.append(
                            f"Incorrect value: {claim['metric']} for {claim['period'].label} "
                            f"claimed as {claim['claimed_value'].format()}, "
                            f"actual is {ground_truth.format()}"
                        )

            elif claim['type'] == 'direction':
                metric = self.lookup.resolve_metric(claim['metric'])
                if metric:
                    # Check common period transitions
                    for from_year, to_year in [(2023, 2024), (2022, 2023)]:
                        from_period = FiscalPeriod(from_year, company=self.company)
                        to_period = FiscalPeriod(to_year, company=self.company)

                        is_valid, actual, message = self.lookup.validate_direction_claim(
                            metric, from_period, to_period, claim['claimed_direction']
                        )
                        if not is_valid and actual:
                            issues.append(
                                f"Incorrect direction: {claim['metric']} claimed as {claim['claimed_direction']}, "
                                f"actual is {actual} ({from_period.label} to {to_period.label})"
                            )
                            break

        # Check for common errors

        # Error: Saying "unchanged" or "stable" when there's a significant change
        if re.search(r'\b(unchanged|stable|flat)\b', answer, re.IGNORECASE):
            # Check if any metric actually changed significantly
            for metric in ['services_revenue', 'net_sales', 'iphone_revenue']:
                change = self.lookup.get_change(
                    metric,
                    FiscalPeriod(2023, company=self.company),
                    FiscalPeriod(2024, company=self.company)
                )
                if change and change.is_significant:
                    issues.append(
                        f"Warning: Answer says 'unchanged/stable' but {metric} "
                        f"changed by {change.percentage_change:+.1f}%"
                    )

        # Error: Using wrong fiscal year data
        if "$394" in answer and "FY2023" in answer:
            issues.append(
                "Potential error: $394B is FY2022 revenue, not FY2023. "
                "FY2023 revenue was $383.29B"
            )

        return len(issues) == 0, issues
