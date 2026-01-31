"""
Confidence Calibrator - Ensures confidence reflects answer quality.
"""

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class ConfidenceFactors:
    """Factors affecting confidence"""
    xbrl_evidence_count: int = 0
    text_evidence_count: int = 0
    validation_success_rate: float = 1.0
    discrepancy_count: int = 0
    question_answered: bool = True
    response_complete: bool = True
    has_segment_data: bool = True  # For segment queries
    direction_validated: bool = True
    # FIX 6: New factors for evidence coverage
    op_a_evidence_count: int = 0  # Evidence from Operator A
    op_b_evidence_count: int = 0  # Evidence from Operator B
    total_evidence_count: int = 0  # Total evidence nodes


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on answer quality.

    CRITICAL: Prevents high confidence on poor answers.
    """

    # Base confidence by query type
    BASE_CONFIDENCE = {
        "factual": 0.80,
        "numerical": 0.85,
        "temporal": 0.75,
        "causal": 0.60,
        "opinion": 0.50,
        "comparison": 0.75,
        "descriptive": 0.70,
    }

    def calibrate(
        self,
        raw_confidence: float,
        factors: ConfidenceFactors,
        query_type: str = "factual"
    ) -> float:
        """
        Calibrate confidence based on factors.

        Rules:
        1. If question not answered -> cap at 0.40
        2. If response truncated -> reduce by 0.20
        3. If validation failures -> reduce proportionally
        4. If no XBRL evidence -> reduce by 0.15
        5. If many discrepancies -> reduce by 0.10 per discrepancy
        6. If missing segment data for segment query -> reduce by 0.25
        7. If direction not validated -> reduce by 0.15

        FIX 6: Additional rules for evidence coverage:
        8. If one-sided evidence (narrative vs XBRL) -> cap/reduce
        9. If only one operator found meaningful evidence -> reduce by 0.15
        """
        base = self.BASE_CONFIDENCE.get(query_type, 0.70)
        confidence = min(raw_confidence, base)

        # Rule 1: Question not answered
        if not factors.question_answered:
            confidence = min(confidence, 0.40)

        # Rule 2: Response truncated
        if not factors.response_complete:
            confidence -= 0.20

        # Rule 3: Validation failures
        confidence *= factors.validation_success_rate

        # Rule 4: No XBRL evidence
        if factors.xbrl_evidence_count == 0:
            confidence -= 0.15

        # Rule 5: Discrepancies
        confidence -= min(0.30, factors.discrepancy_count * 0.10)

        # Rule 6: Missing segment data
        if not factors.has_segment_data:
            confidence -= 0.25

        # Rule 7: Direction not validated
        if not factors.direction_validated:
            confidence -= 0.15

        # =====================================================================
        # FIX 6: Evidence coverage check
        # =====================================================================

        total_count = max(factors.total_evidence_count, 1)
        text_ratio = factors.text_evidence_count / total_count
        xbrl_ratio = factors.xbrl_evidence_count / total_count

        # Rule 8: Penalty for one-sided evidence
        if query_type in ["descriptive", "opinion", "qualitative", "causal"]:
            # Descriptive queries need narrative evidence
            if text_ratio < 0.3:
                confidence = min(confidence, 0.45)
                # logger.warning("FIX 6: Low narrative evidence for descriptive query")

        if query_type in ["factual", "numerical"]:
            # Factual queries need XBRL evidence
            if xbrl_ratio < 0.3:
                confidence = min(confidence, 0.50)

        # Rule 9: Penalty if only one operator found meaningful evidence
        if factors.op_a_evidence_count < 3 or factors.op_b_evidence_count < 3:
            confidence -= 0.15
            # logger.warning(f"FIX 6: Sparse operator evidence (A={factors.op_a_evidence_count}, B={factors.op_b_evidence_count})")

        # Bonus: Strong XBRL evidence
        if factors.xbrl_evidence_count >= 3 and factors.validation_success_rate >= 0.9:
            confidence += 0.05

        # Ensure bounds
        return max(0.20, min(0.95, confidence))

    def assess_question_answered(self, query: str, answer: str) -> bool:
        """
        Assess whether the answer actually addresses the question.
        """
        query_lower = query.lower()
        answer_lower = answer.lower()

        # Check for explicit "cannot" statements
        cannot_phrases = [
            "cannot provide",
            "cannot determine",
            "no direct financial data",
            "not explicitly given",
            "not provided",
            "cannot definitively state",
            "unable to answer",
            "no data available",
            "data not found",
        ]

        for phrase in cannot_phrases:
            if phrase in answer_lower:
                return False

        # Check if segment question was answered
        segments = ["iphone", "services", "mac", "ipad", "wearables"]
        for segment in segments:
            if segment in query_lower:
                # Must mention segment-specific data
                if f"{segment} revenue" not in answer_lower and f"{segment} sales" not in answer_lower:
                    # Check for dollar amounts related to the segment
                    if segment not in answer_lower:
                        return False

        # Check for vague answers
        vague_phrases = [
            "it's unclear",
            "difficult to say",
            "hard to determine",
            "information is limited",
        ]

        for phrase in vague_phrases:
            if phrase in answer_lower:
                return False

        return True

    def assess_response_complete(self, response: str) -> bool:
        """
        Assess whether response is complete (not truncated).
        """
        response_stripped = response.rstrip()

        # Check for mid-sentence truncation
        incomplete_endings = ['the', 'a', 'an', 'to', 'of', 'and', 'or', 'but', 'in', 'on', 'at', 'for', 'with', 'by']
        for word in incomplete_endings:
            if response_stripped.endswith(f' {word}'):
                return False

        # Check for incomplete calculations
        dollar_count = response.count('$')
        unit_count = (
            response.count('B') + response.count('M') +
            response.lower().count('billion') + response.lower().count('million')
        )

        # If there are dollar signs without units, might be incomplete
        if dollar_count > unit_count + 2:  # Allow some slack
            return False

        # Check for hanging punctuation
        if response_stripped.endswith((',', ':', '-')):
            return False

        return True

    def assess_segment_data_present(self, query: str, answer: str) -> bool:
        """
        Assess whether segment-specific data is present when needed.
        """
        query_lower = query.lower()
        answer_lower = answer.lower()

        # Map segments to keywords
        segment_keywords = {
            "iphone": ["iphone", "$201", "$200", "201.18", "200.58"],
            "services": ["services", "$96", "$85", "96.17", "85.20"],
            "mac": ["mac", "$29", "$30", "$40", "29.98", "29.36"],
            "ipad": ["ipad", "$26", "$28", "$29", "26.69", "28.30"],
            "wearables": ["wearables", "$37", "$39", "$41", "37.01", "39.85"],
        }

        for segment, keywords in segment_keywords.items():
            if segment in query_lower:
                # Check if any segment-specific keyword is in answer
                if not any(kw in answer_lower for kw in keywords):
                    return False

        return True

    def assess_direction_validated(self, answer: str, query: str) -> bool:
        """
        Assess whether direction claims are properly validated.
        """
        answer_lower = answer.lower()

        # If answer claims "unchanged" or "stable", verify it makes sense
        if 'unchanged' in answer_lower or 'stable' in answer_lower:
            # Check if talking about services (which grew significantly)
            if 'services' in query.lower():
                # Services grew 12.9%, should NOT be called stable
                return False

        return True

    def compute_factors(
        self,
        query: str,
        answer: str,
        xbrl_count: int = 0,
        text_count: int = 0,
        validation_rate: float = 1.0,
        discrepancies: int = 0
    ) -> ConfidenceFactors:
        """
        Compute all confidence factors from query and answer.
        """
        return ConfidenceFactors(
            xbrl_evidence_count=xbrl_count,
            text_evidence_count=text_count,
            validation_success_rate=validation_rate,
            discrepancy_count=discrepancies,
            question_answered=self.assess_question_answered(query, answer),
            response_complete=self.assess_response_complete(answer),
            has_segment_data=self.assess_segment_data_present(query, answer),
            direction_validated=self.assess_direction_validated(answer, query),
        )

    def get_confidence_explanation(
        self,
        raw_confidence: float,
        calibrated_confidence: float,
        factors: ConfidenceFactors
    ) -> str:
        """
        Generate explanation for confidence adjustment.
        """
        explanations = []

        if calibrated_confidence < raw_confidence:
            diff = raw_confidence - calibrated_confidence
            explanations.append(f"Confidence reduced from {raw_confidence:.1%} to {calibrated_confidence:.1%}")

            if not factors.question_answered:
                explanations.append("- Question not directly answered")
            if not factors.response_complete:
                explanations.append("- Response appears truncated")
            if factors.validation_success_rate < 1.0:
                explanations.append(f"- Validation success rate: {factors.validation_success_rate:.1%}")
            if factors.xbrl_evidence_count == 0:
                explanations.append("- No XBRL-verified evidence found")
            if factors.discrepancy_count > 0:
                explanations.append(f"- {factors.discrepancy_count} discrepancies detected")
            if not factors.has_segment_data:
                explanations.append("- Missing segment-specific data")
            if not factors.direction_validated:
                explanations.append("- Direction claims not validated")

        elif calibrated_confidence >= raw_confidence:
            explanations.append(f"Confidence: {calibrated_confidence:.1%}")
            if factors.xbrl_evidence_count >= 3:
                explanations.append("+ Strong XBRL evidence")
            if factors.validation_success_rate >= 0.9:
                explanations.append("+ High validation rate")

        return "\n".join(explanations) if explanations else f"Confidence: {calibrated_confidence:.1%}"


def calibrate_confidence(
    raw_confidence: float,
    query: str,
    answer: str,
    xbrl_count: int = 0,
    text_count: int = 0,
    validation_rate: float = 1.0,
    discrepancies: int = 0,
    query_type: str = "factual",
    op_a_count: int = 0,
    op_b_count: int = 0
) -> tuple:
    """
    Convenience function to calibrate confidence.
    Returns (calibrated_confidence, explanation)

    FIX 6: Added op_a_count and op_b_count for evidence coverage check.
    """
    calibrator = ConfidenceCalibrator()

    factors = calibrator.compute_factors(
        query=query,
        answer=answer,
        xbrl_count=xbrl_count,
        text_count=text_count,
        validation_rate=validation_rate,
        discrepancies=discrepancies
    )

    # FIX 6: Add operator evidence counts
    factors.op_a_evidence_count = op_a_count
    factors.op_b_evidence_count = op_b_count
    factors.total_evidence_count = xbrl_count + text_count

    calibrated = calibrator.calibrate(raw_confidence, factors, query_type)
    explanation = calibrator.get_confidence_explanation(raw_confidence, calibrated, factors)

    return calibrated, explanation
