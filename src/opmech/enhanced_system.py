"""
Enhanced OpMech-GraphRAG System with Ground Truth Validation.

This module extends the base OpMech system with:
1. Type-safe fiscal period handling
2. Ground truth validation against XBRL data
3. Improved evidence retrieval for segments
4. Confidence calibration
5. Answer synthesis with validation
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from loguru import logger

from src.opmech.system import OpMechGraphRAG
from src.opmech.data_classes import QueryResult, OutputMode

# Import new components
from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue, FinancialChange
from src.data.apple_ground_truth import AppleFinancialLookup, APPLE_FINANCIALS
from src.processing.evidence_retriever import EvidenceRetriever, EvidenceSet
from src.processing.answer_synthesizer import AnswerSynthesizer, OperatorOutput, SynthesizedAnswer
from src.processing.confidence_calibrator import ConfidenceCalibrator, ConfidenceFactors, calibrate_confidence
from src.prompts.operator_prompts import (
    format_operator_a_prompt,
    format_operator_b_prompt,
    format_synthesizer_prompt,
)


@dataclass
class EnhancedQueryResult:
    """Extended query result with validation information."""
    # Base result fields
    answer: str
    confidence: float
    mode: str
    hops_used: int

    # Validation information
    validations_passed: int = 0
    validations_failed: int = 0
    corrections_applied: List[str] = field(default_factory=list)
    ground_truth_used: bool = False

    # Evidence information
    xbrl_evidence_count: int = 0
    segment_data_found: bool = True

    # Operator outputs
    answer_A: str = ""
    answer_B: str = ""

    # Diagnostics
    reasoning: str = ""
    analyst_notes: str = ""
    confidence_explanation: str = ""

    # Original result for reference
    original_result: Optional[QueryResult] = None


class EnhancedOpMechGraphRAG:
    """
    Enhanced OpMech-GraphRAG system with ground truth validation.

    This wraps the base system and adds:
    1. Pre-query evidence retrieval with ground truth
    2. Post-query validation against XBRL data
    3. Confidence calibration
    4. Answer correction when needed
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password123",
        vllm_url: str = "http://localhost:8000/v1",
        company: str = "AAPL",
        **kwargs
    ):
        """
        Initialize enhanced system.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            vllm_url: vLLM server URL
            company: Company ticker for ground truth lookup
            **kwargs: Additional arguments for base system
        """
        logger.info("Initializing Enhanced OpMech-GraphRAG system...")

        self.company = company

        # Initialize base system
        self.base_system = OpMechGraphRAG(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            vllm_url=vllm_url,
            **kwargs
        )

        # Initialize enhanced components
        self.evidence_retriever = EvidenceRetriever(company=company)
        self.answer_synthesizer = AnswerSynthesizer(company=company)
        self.confidence_calibrator = ConfidenceCalibrator()
        self.lookup = AppleFinancialLookup

        logger.info("Enhanced OpMech-GraphRAG system initialized")

    def query(self, query: str) -> EnhancedQueryResult:
        """
        Execute query with enhanced validation.

        Steps:
        1. Retrieve ground truth evidence for query context
        2. Execute base system query
        3. Validate answer against ground truth
        4. Calibrate confidence
        5. Apply corrections if needed

        Args:
            query: User query string

        Returns:
            EnhancedQueryResult with validated answer
        """
        logger.info(f"Processing enhanced query: {query[:50]}...")

        # Step 1: Retrieve ground truth evidence
        ground_truth_evidence = self._retrieve_ground_truth(query)
        ground_truth_context = self.evidence_retriever.format_for_llm(ground_truth_evidence)

        logger.info(f"Ground truth: {len(ground_truth_evidence.nodes)} nodes, "
                   f"{len(ground_truth_evidence.found_metrics)} metrics found")

        # Step 2: Execute base system query
        base_result = self.base_system.query(query)

        # Step 3: Validate answer against ground truth
        is_valid, validation_issues = self.answer_synthesizer.validate_answer_against_ground_truth(
            base_result.answer, query
        )

        # Step 4: Create operator outputs for synthesis
        operator_a = OperatorOutput(
            operator_name="Operator A (Structure-First)",
            raw_answer=base_result.answer_A,
            confidence=base_result.path_confidence_A if hasattr(base_result, 'path_confidence_A') else 0.7
        )

        operator_b = OperatorOutput(
            operator_name="Operator B (Narrative-First)",
            raw_answer=base_result.answer_B,
            confidence=base_result.path_confidence_B if hasattr(base_result, 'path_confidence_B') else 0.5
        )

        # Step 5: Synthesize final answer with validation
        synthesized = self.answer_synthesizer.synthesize(
            operator_a, operator_b, ground_truth_context
        )

        # Step 6: Calibrate confidence
        factors = self._compute_confidence_factors(
            query=query,
            answer=synthesized.answer_text,
            ground_truth_evidence=ground_truth_evidence,
            validation_rate=synthesized.validation_rate
        )

        calibrated_confidence, confidence_explanation = calibrate_confidence(
            raw_confidence=base_result.confidence,
            query=query,
            answer=synthesized.answer_text,
            xbrl_count=factors.xbrl_evidence_count,
            validation_rate=synthesized.validation_rate,
            discrepancies=len(validation_issues),
            query_type=self._infer_query_type(query)
        )

        # Step 7: Determine final answer
        # If synthesized answer has corrections, use it; otherwise use base answer
        if synthesized.has_corrections or not is_valid:
            final_answer = synthesized.answer_text
            corrections = synthesized.corrections_made
        else:
            final_answer = base_result.answer
            corrections = []

        # Step 8: Enhance answer with ground truth data if available
        enhanced_answer = self._enhance_answer_with_ground_truth(
            final_answer, query, ground_truth_evidence
        )

        return EnhancedQueryResult(
            answer=enhanced_answer,
            confidence=calibrated_confidence,
            mode=base_result.mode.value if hasattr(base_result.mode, 'value') else str(base_result.mode),
            hops_used=base_result.hops_used,
            validations_passed=sum(1 for v in synthesized.validations if v.is_valid),
            validations_failed=sum(1 for v in synthesized.validations if not v.is_valid),
            corrections_applied=corrections,
            ground_truth_used=len(ground_truth_evidence.nodes) > 0,
            xbrl_evidence_count=len(ground_truth_evidence.get_xbrl_nodes()),
            segment_data_found=len(ground_truth_evidence.missing_metrics) == 0,
            answer_A=base_result.answer_A,
            answer_B=base_result.answer_B,
            reasoning=base_result.reasoning,
            analyst_notes=synthesized.analyst_notes,
            confidence_explanation=confidence_explanation,
            original_result=base_result
        )

    def _retrieve_ground_truth(self, query: str) -> EvidenceSet:
        """
        Retrieve ground truth evidence for the query.
        """
        # Determine periods to retrieve based on query
        periods = self._infer_periods_from_query(query)

        # Retrieve evidence
        return self.evidence_retriever.retrieve(query, periods)

    def _infer_periods_from_query(self, query: str) -> List[FiscalPeriod]:
        """
        Infer which fiscal periods are relevant for the query.
        """
        query_lower = query.lower()
        periods = []

        # Check for specific year mentions
        import re
        year_matches = re.findall(r'(?:fy)?20(\d{2})', query_lower)

        if year_matches:
            for match in year_matches:
                year = 2000 + int(match)
                if 2020 <= year <= 2024:
                    periods.append(FiscalPeriod(year=year, company=self.company))

        # Default: most recent years
        if not periods:
            periods = [
                FiscalPeriod(year=2024, company=self.company),
                FiscalPeriod(year=2023, company=self.company),
                FiscalPeriod(year=2022, company=self.company),
            ]

        return periods

    def _infer_query_type(self, query: str) -> str:
        """
        Infer query type for confidence calibration.
        """
        query_lower = query.lower()

        if any(word in query_lower for word in ['how much', 'what is the', 'what was', 'value']):
            return "numerical"
        elif any(word in query_lower for word in ['trend', 'change', 'growth', 'performance']):
            return "temporal"
        elif any(word in query_lower for word in ['why', 'cause', 'reason', 'because']):
            return "causal"
        elif any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference']):
            return "comparison"
        elif any(word in query_lower for word in ['think', 'believe', 'should', 'opinion']):
            return "opinion"
        else:
            return "descriptive"

    def _compute_confidence_factors(
        self,
        query: str,
        answer: str,
        ground_truth_evidence: EvidenceSet,
        validation_rate: float
    ) -> ConfidenceFactors:
        """
        Compute confidence factors.
        """
        xbrl_count = len(ground_truth_evidence.get_xbrl_nodes())
        text_count = len(ground_truth_evidence.get_text_nodes())

        return self.confidence_calibrator.compute_factors(
            query=query,
            answer=answer,
            xbrl_count=xbrl_count,
            text_count=text_count,
            validation_rate=validation_rate,
            discrepancies=len(ground_truth_evidence.missing_metrics)
        )

    def _enhance_answer_with_ground_truth(
        self,
        answer: str,
        query: str,
        evidence: EvidenceSet
    ) -> str:
        """
        Enhance answer with ground truth data if the answer seems incomplete.
        """
        query_lower = query.lower()
        answer_lower = answer.lower()

        # Check if answer lacks specific segment revenue data
        segments = ['iphone', 'services', 'mac', 'ipad', 'wearables']
        mentioned_segment = None

        for segment in segments:
            if segment in query_lower:
                mentioned_segment = segment
                break

        if mentioned_segment:
            # Check if the answer contains actual revenue numbers for this segment
            # Look for specific dollar amounts like "$96" or "$85" (billions for services)
            segment_values = {
                'services': ['96.17', '85.20', '78.13', '96', '85', '78'],
                'iphone': ['201', '200', '205', '192'],
                'mac': ['29.98', '29.36', '40.18', '30', '29', '40'],
                'ipad': ['26.69', '28.30', '29.29', '27', '28', '29'],
                'wearables': ['37.01', '39.85', '41.24', '37', '40', '41'],
            }

            has_segment_revenue = False
            for value in segment_values.get(mentioned_segment, []):
                if value in answer:
                    has_segment_revenue = True
                    break

            # If the answer doesn't have specific segment revenue data, add it
            if not has_segment_revenue:
                # Try to add segment data
                segment_changes = []
                for change in evidence.get_all_changes():
                    if mentioned_segment in change.metric_name.lower():
                        segment_changes.append(change)

                if segment_changes:
                    enhancement = f"\n\n**{mentioned_segment.title()} Revenue Data (XBRL Verified):**\n"
                    for change in segment_changes:
                        enhancement += f"- {change.format_concise()}\n"
                    return answer + enhancement

        # Check if answer claims "unchanged" but data shows significant change
        if 'unchanged' in answer.lower() or 'stable' in answer.lower():
            for change in evidence.get_all_changes():
                if change.is_significant:
                    # Add a correction note
                    correction = (
                        f"\n\n**Note:** The data shows {change.metric_name} "
                        f"changed by {change.percentage_change:+.1f}% "
                        f"({change.direction}) from {change.from_period.label} to {change.to_period.label}."
                    )
                    return answer + correction

        return answer

    def get_segment_data(self, segment: str) -> Dict[str, Any]:
        """
        Get detailed segment data.
        """
        evidence = self.evidence_retriever.get_segment_evidence(segment)
        return {
            'segment': segment,
            'values': {
                node.periods[0].label: node.values[0].format()
                for node in evidence.nodes
                if node.periods and node.values
            },
            'changes': [change.format_concise() for change in evidence.get_all_changes()],
            'missing': list(evidence.missing_metrics)
        }

    def validate_claim(
        self,
        metric: str,
        period: str,
        claimed_value: str
    ) -> Dict[str, Any]:
        """
        Validate a specific claim against ground truth.
        """
        period_obj = FiscalPeriod.from_string(period, self.company)
        if not period_obj:
            return {'valid': False, 'error': f'Invalid period: {period}'}

        value_obj = FinancialValue.parse(claimed_value)
        if not value_obj:
            return {'valid': False, 'error': f'Invalid value: {claimed_value}'}

        is_valid, ground_truth, message = self.lookup.validate_claim(
            metric, period_obj, value_obj
        )

        return {
            'valid': is_valid,
            'claimed': claimed_value,
            'actual': ground_truth.format() if ground_truth else None,
            'message': message
        }

    def close(self):
        """Clean up resources."""
        self.base_system.close()
        logger.info("Enhanced OpMech-GraphRAG system closed")


# Convenience function for creating enhanced system
def create_enhanced_system(**kwargs) -> EnhancedOpMechGraphRAG:
    """
    Create an enhanced OpMech-GraphRAG system.
    """
    return EnhancedOpMechGraphRAG(**kwargs)
