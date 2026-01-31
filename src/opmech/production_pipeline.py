"""
Production Pipeline for OpMech-GraphRAG System

This module integrates all the production-grade components:
- Type-safe data models (FiscalPeriod, FinancialValue)
- Evidence extraction with proper type separation
- Temporal intelligence with pre-computed changes
- Robust consistency checking

KEY PRINCIPLE: Every step uses typed objects. No string manipulation
that could confuse data types. The LLM receives pre-computed changes
so it doesn't have to compute directions itself.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from decimal import Decimal
import numpy as np
from loguru import logger

from .type_safe_models import (
    FiscalPeriod,
    FinancialValue,
    Direction,
    EvidenceNode,
    ComputedChange,
    OperatorOutput,
    ConsistencyReport,
    Discrepancy,
)
from .evidence_extractor import (
    EvidenceExtractor,
    EvidenceSet,
    create_evidence_extractor,
)
from .temporal_intelligence import (
    TemporalIntelligence,
    XBRLGroundTruth,
    create_temporal_intelligence,
)
from .robust_consistency_checker import (
    RobustConsistencyChecker,
    ConsistencyValidator,
)
from .data_classes import (
    Node,
    TraversedNode,
    BeliefState,
    QueryResult,
    OutputMode,
)
from .metric_types import get_metric_config


@dataclass
class EnrichedEvidence:
    """Evidence that has been enriched with temporal context."""
    nodes: List[EvidenceNode]
    xbrl_ground_truth: Dict[str, Dict[str, FinancialValue]]
    computed_changes: List[ComputedChange]
    formatted_for_llm: str


@dataclass
class ValidationResult:
    """Result of validating an operator output."""
    is_valid: bool
    issues: List[str]
    corrections: Dict[str, Any]
    validated_answer: str


@dataclass
class FinalAnswer:
    """Final answer with full validation and traceability."""
    answer: str
    confidence: float
    mode: OutputMode
    consistency_report: ConsistencyReport
    validation_results: Dict[str, ValidationResult]
    analyst_notes: str
    evidence_summary: str


class ProductionPipeline:
    """
    Main pipeline that orchestrates all production components.

    KEY PRINCIPLE: Every step uses typed objects. No string manipulation
    that could confuse data types.
    """

    def __init__(
        self,
        company: str = "AAPL",
        xbrl_ground_truth: Optional[XBRLGroundTruth] = None
    ):
        """
        Initialize the production pipeline.

        Args:
            company: Company ticker
            xbrl_ground_truth: Optional XBRL ground truth data
        """
        self.company = company
        self.extractor = create_evidence_extractor(company)
        self.temporal = create_temporal_intelligence(company)
        self.consistency_checker = RobustConsistencyChecker(company)
        self.xbrl_ground_truth = xbrl_ground_truth or XBRLGroundTruth()

        logger.info(f"Production pipeline initialized for {company}")

    def enrich_evidence(
        self,
        raw_nodes: List[Node],
        query: str
    ) -> EnrichedEvidence:
        """
        Enrich raw evidence with temporal context and type-safe values.

        This is called BEFORE operators generate answers.

        Args:
            raw_nodes: Raw nodes from graph traversal
            query: User query for context

        Returns:
            EnrichedEvidence with typed values and pre-computed changes
        """
        logger.debug(f"Enriching {len(raw_nodes)} evidence nodes")

        # Convert raw nodes to EvidenceNodes with typed extraction
        evidence_nodes: List[EvidenceNode] = []

        for raw_node in raw_nodes:
            # Extract typed information
            evidence_node = self.extractor.extract_from_text(
                text=raw_node.text,
                source=raw_node.metadata.get('source_file', 'unknown')
            )

            # Copy metadata
            evidence_node.node_type = raw_node.type
            evidence_node.xbrl_tag = raw_node.metadata.get('xbrl_tag')

            # If node has a value, add it properly
            if raw_node.metadata.get('value') is not None:
                try:
                    value = float(raw_node.metadata['value'])
                    scale = self._determine_scale(value)

                    # Get period if available
                    period = None
                    if raw_node.metadata.get('period'):
                        period = FiscalPeriod.from_string(
                            raw_node.metadata['period'],
                            company=self.company
                        )

                    financial_value = FinancialValue(
                        amount=Decimal(str(value / self._get_scale_divisor(scale))),
                        scale=scale,
                        period=period,
                        source=raw_node.metadata.get('xbrl_tag', 'unknown')
                    )
                    evidence_node.values.append(financial_value)

                except (ValueError, TypeError):
                    pass

            evidence_nodes.append(evidence_node)

        # Build XBRL ground truth mapping from evidence
        xbrl_data = self._build_xbrl_mapping(evidence_nodes)

        # Enrich with temporal intelligence
        evidence_nodes = self.temporal.enrich_evidence_nodes(
            evidence_nodes,
            xbrl_data=xbrl_data
        )

        # Collect all computed changes
        all_changes: List[ComputedChange] = []
        for node in evidence_nodes:
            all_changes.extend(node.computed_changes)

        # Deduplicate changes
        seen = set()
        unique_changes = []
        for change in all_changes:
            key = (change.metric_name, change.from_period, change.to_period)
            if key not in seen:
                seen.add(key)
                unique_changes.append(change)

        # Format for LLM
        formatted = self.temporal.format_evidence_for_llm(evidence_nodes)

        return EnrichedEvidence(
            nodes=evidence_nodes,
            xbrl_ground_truth=xbrl_data,
            computed_changes=unique_changes,
            formatted_for_llm=formatted
        )

    def validate_operator_output(
        self,
        output: OperatorOutput,
        enriched_evidence: EnrichedEvidence
    ) -> ValidationResult:
        """
        Validate an operator's output against evidence.

        Checks:
        - Numerical claims against XBRL ground truth
        - Direction claims against computed changes

        Args:
            output: Operator output to validate
            enriched_evidence: Enriched evidence for validation

        Returns:
            ValidationResult with issues and corrections
        """
        issues: List[str] = []
        corrections: Dict[str, Any] = {}

        # Extract claims from the answer
        value_claims = self.extractor.extract_value_claims(output.raw_answer)
        direction_claims = self.extractor.extract_direction_claims(output.raw_answer)

        # Validate direction claims
        for claim in direction_claims:
            claimed_direction = claim['direction']
            metric = claim['metric']

            # Find matching computed change
            for change in enriched_evidence.computed_changes:
                if metric.lower() in change.metric_name.lower():
                    # Validate against pre-computed direction
                    if claimed_direction != change.direction:
                        issues.append(
                            f"Direction error for {metric}: "
                            f"Claimed {claimed_direction.value}, "
                            f"actual is {change.direction.value}"
                        )
                        corrections[f"direction_{metric}"] = change.direction

        # Validate value claims
        for claim in value_claims:
            claimed_value = claim['value']
            metric = claim['metric']

            # Find matching ground truth
            for xbrl_metric, period_values in enriched_evidence.xbrl_ground_truth.items():
                if metric.lower() in xbrl_metric.lower():
                    # Check against most recent period
                    for period_label, ground_truth in period_values.items():
                        if ground_truth.normalized_amount != Decimal("0"):
                            diff_pct = abs(
                                float((claimed_value.normalized_amount - ground_truth.normalized_amount)
                                      / ground_truth.normalized_amount)
                            )
                            if diff_pct > 0.05:  # 5% tolerance
                                issues.append(
                                    f"Value discrepancy for {metric}: "
                                    f"Claimed {claimed_value.format()}, "
                                    f"ground truth is {ground_truth.format()} "
                                    f"({diff_pct*100:.1f}% difference)"
                                )
                                corrections[f"value_{metric}"] = ground_truth

        # Generate validated answer (with corrections if needed)
        validated_answer = output.raw_answer
        if corrections:
            validated_answer = self._apply_corrections(output.raw_answer, corrections)

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            corrections=corrections,
            validated_answer=validated_answer
        )

    def check_consistency(
        self,
        output_a: OperatorOutput,
        output_b: OperatorOutput,
        enriched_evidence: EnrichedEvidence
    ) -> ConsistencyReport:
        """
        Check consistency between operator outputs.

        Uses the robust consistency checker with type safety.

        Args:
            output_a: Output from Operator A
            output_b: Output from Operator B
            enriched_evidence: Enriched evidence for resolution

        Returns:
            ConsistencyReport with discrepancies and analyst notes
        """
        # Use robust consistency checker
        report = self.consistency_checker.check_consistency(output_a, output_b)

        # Try to resolve discrepancies with XBRL ground truth
        validator = ConsistencyValidator(self.company)
        report = validator.validate_with_ground_truth(
            output_a,
            output_b,
            enriched_evidence.xbrl_ground_truth
        )

        return report

    def generate_final_answer(
        self,
        output_a: OperatorOutput,
        output_b: OperatorOutput,
        consistency_report: ConsistencyReport,
        enriched_evidence: EnrichedEvidence,
        mode: OutputMode
    ) -> FinalAnswer:
        """
        Generate the final answer with full validation.

        Args:
            output_a: Validated output from Operator A
            output_b: Validated output from Operator B
            consistency_report: Consistency check results
            enriched_evidence: Enriched evidence
            mode: Output mode (EXPLOIT, ADAPTIVE, EXPLORE)

        Returns:
            FinalAnswer with all validation and traceability
        """
        # Validate both outputs
        validation_a = self.validate_operator_output(output_a, enriched_evidence)
        validation_b = self.validate_operator_output(output_b, enriched_evidence)

        # Select answer based on mode and validation
        if mode == OutputMode.EXPLOIT:
            # Use the more confident answer
            if output_a.confidence >= output_b.confidence:
                answer = validation_a.validated_answer
            else:
                answer = validation_b.validated_answer
        elif mode == OutputMode.ADAPTIVE:
            # Merge answers (simplified - in production, use LLM)
            answer = self._merge_answers(
                validation_a.validated_answer,
                validation_b.validated_answer,
                consistency_report
            )
        else:  # EXPLORE
            # Present both answers with uncertainty
            answer = (
                f"**Analysis A (Structure-First):**\n{validation_a.validated_answer}\n\n"
                f"**Analysis B (Narrative-First):**\n{validation_b.validated_answer}\n\n"
                f"**Note:** These analyses show some divergence. Please consider both perspectives."
            )

        # Generate analyst notes
        analyst_notes = consistency_report.analyst_notes
        if validation_a.issues or validation_b.issues:
            if analyst_notes:
                analyst_notes += "\n\n"
            analyst_notes += "Validation notes:\n"
            for issue in validation_a.issues + validation_b.issues:
                analyst_notes += f"  - {issue}\n"

        # Generate evidence summary
        evidence_summary = self._generate_evidence_summary(enriched_evidence)

        # Calculate confidence
        confidence = consistency_report.trust_score
        if validation_a.issues:
            confidence *= 0.9
        if validation_b.issues:
            confidence *= 0.9

        return FinalAnswer(
            answer=answer,
            confidence=confidence,
            mode=mode,
            consistency_report=consistency_report,
            validation_results={
                "operator_a": validation_a,
                "operator_b": validation_b
            },
            analyst_notes=analyst_notes,
            evidence_summary=evidence_summary
        )

    def _determine_scale(self, value: float) -> str:
        """Determine appropriate scale for a value."""
        abs_value = abs(value)
        if abs_value >= 1e9:
            return "billions"
        elif abs_value >= 1e6:
            return "millions"
        elif abs_value >= 1e3:
            return "thousands"
        return "units"

    def _get_scale_divisor(self, scale: str) -> float:
        """Get divisor for a scale."""
        return {
            "billions": 1e9,
            "millions": 1e6,
            "thousands": 1e3,
            "units": 1
        }.get(scale, 1)

    def _build_xbrl_mapping(
        self,
        nodes: List[EvidenceNode]
    ) -> Dict[str, Dict[str, FinancialValue]]:
        """
        Build XBRL ground truth mapping from evidence nodes.
        """
        mapping: Dict[str, Dict[str, FinancialValue]] = {}

        for node in nodes:
            if not node.xbrl_tag:
                continue

            metric = node.xbrl_tag
            if metric not in mapping:
                mapping[metric] = {}

            for value in node.values:
                if value.period:
                    mapping[metric][value.period.label] = value

        return mapping

    def _apply_corrections(
        self,
        answer: str,
        corrections: Dict[str, Any]
    ) -> str:
        """
        Apply corrections to an answer.

        In production, this would use an LLM to intelligently rewrite.
        Here we add a correction note.
        """
        if not corrections:
            return answer

        correction_note = "\n\n[Corrections applied: "
        correction_parts = []
        for key, value in corrections.items():
            if isinstance(value, Direction):
                correction_parts.append(f"{key} should be {value.value}")
            elif isinstance(value, FinancialValue):
                correction_parts.append(f"{key} is {value.format()}")
        correction_note += ", ".join(correction_parts) + "]"

        return answer + correction_note

    def _merge_answers(
        self,
        answer_a: str,
        answer_b: str,
        consistency_report: ConsistencyReport
    ) -> str:
        """
        Merge two answers into one coherent response.

        In production, this would use an LLM. Here we do simple merging.
        """
        if consistency_report.is_consistent:
            # Answers agree, use first one
            return answer_a

        # Add note about reconciliation
        merged = answer_a
        if consistency_report.analyst_notes:
            merged += f"\n\n{consistency_report.analyst_notes}"

        return merged

    def _generate_evidence_summary(
        self,
        evidence: EnrichedEvidence
    ) -> str:
        """Generate a summary of the evidence used."""
        lines = []

        # Count by type
        xbrl_count = sum(1 for n in evidence.nodes if n.xbrl_tag)
        text_count = sum(1 for n in evidence.nodes if not n.xbrl_tag)

        lines.append(f"Evidence sources: {len(evidence.nodes)} nodes")
        lines.append(f"  - XBRL data: {xbrl_count}")
        lines.append(f"  - Text content: {text_count}")

        # Pre-computed changes
        if evidence.computed_changes:
            lines.append(f"\nPre-computed changes: {len(evidence.computed_changes)}")
            for change in evidence.computed_changes[:5]:  # Show first 5
                lines.append(f"  - {change.metric_name}: {change.direction.value}")

        return "\n".join(lines)


def create_production_pipeline(
    company: str = "AAPL",
    xbrl_data: Optional[Dict[str, Any]] = None
) -> ProductionPipeline:
    """
    Factory function to create a production pipeline.

    Args:
        company: Company ticker
        xbrl_data: Optional XBRL ground truth data

    Returns:
        Configured ProductionPipeline instance
    """
    # Convert xbrl_data to XBRLGroundTruth if provided
    xbrl_ground_truth = None
    if xbrl_data:
        xbrl_ground_truth = XBRLGroundTruth()
        for metric, period_values in xbrl_data.items():
            for period_str, value in period_values.items():
                period = FiscalPeriod.from_string(period_str, company=company)
                if period and isinstance(value, (int, float)):
                    financial_value = FinancialValue(
                        amount=Decimal(str(value)),
                        scale="units"
                    )
                    xbrl_ground_truth.add_value(company, metric, period, financial_value)

    return ProductionPipeline(
        company=company,
        xbrl_ground_truth=xbrl_ground_truth
    )


# Integration with existing OpMech system
class ProductionEnhancedOpMech:
    """
    Wrapper that adds production pipeline to existing OpMech system.

    This class can be used to enhance the existing OpMechGraphRAG
    with the new type-safe components.
    """

    def __init__(
        self,
        opmech_system: Any,  # OpMechGraphRAG instance
        company: str = "AAPL"
    ):
        self.opmech = opmech_system
        self.pipeline = create_production_pipeline(company)
        self.company = company

    def query_with_validation(self, query: str) -> FinalAnswer:
        """
        Execute query with production-grade validation.

        This wraps the existing OpMech query with:
        - Evidence enrichment
        - Type-safe validation
        - Consistency checking

        Args:
            query: User query

        Returns:
            FinalAnswer with full validation
        """
        # Run original OpMech query
        result = self.opmech.query(query)

        # Create operator outputs from results
        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer=result.answer_A,
            confidence=result.operator_scores.get("structure_first", 0.5)
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer=result.answer_B,
            confidence=result.operator_scores.get("narrative_first", 0.5)
        )

        # Convert evidence to Node format
        raw_nodes = []
        for node in result.evidence_A + result.evidence_B:
            raw_nodes.append(Node(
                id=node.id,
                type=node.type,
                text=node.text,
                metadata=node.metadata
            ))

        # Enrich evidence
        enriched = self.pipeline.enrich_evidence(raw_nodes, query)

        # Check consistency
        consistency_report = self.pipeline.check_consistency(
            output_a, output_b, enriched
        )

        # Generate final answer
        return self.pipeline.generate_final_answer(
            output_a,
            output_b,
            consistency_report,
            enriched,
            result.mode
        )
