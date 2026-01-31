"""
OpMech Mode Selection and Operator Reliability System

This module determines:
1. Which mode to use (EXPLOIT/ADAPTIVE/EXPLORE)
2. Which operator to trust when they disagree
3. How confident we are in the final answer

Key insight: The commutator measures DISAGREEMENT, but we also need to
measure RELIABILITY to determine WHO IS RIGHT when operators disagree.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import re
from loguru import logger

# Import the hybrid query classifier
from .query_classifier import (
    HybridQueryClassifier,
    QueryClassification,
    QueryType,
    create_hybrid_classifier,
)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class QueryMode(Enum):
    """Final query mode."""
    EXPLOIT = "EXPLOIT"    # High confidence, clear answer
    ADAPTIVE = "ADAPTIVE"  # Moderate confidence, balanced view
    EXPLORE = "EXPLORE"    # Low confidence, multiple perspectives


class TrustDecision(Enum):
    """Who to trust when operators disagree."""
    TRUST_A = "trust_operator_a"          # Structure-first is more reliable
    TRUST_B = "trust_operator_b"          # Narrative-first is more reliable
    MERGE_EQUAL = "merge_equal"           # Both equally reliable
    MERGE_WEIGHTED = "merge_weighted"     # Merge but weight by reliability
    CONFLICT = "conflict"                 # Irreconcilable conflict, present both


@dataclass
class OperatorReliability:
    """Reliability assessment for one operator."""
    operator_name: str
    reliability_score: float     # 0-1, higher = more reliable for this query
    evidence_quality: float      # Quality of evidence found
    source_authority: float      # Authority of sources (XBRL > narrative)
    query_fit: float            # How well evidence matches query type
    path_confidence: float       # Path confidence from traversal
    evidence_breakdown: Dict[str, int]  # Count by node type
    reasoning: str


@dataclass
class ModeDecision:
    """Complete mode decision with all context."""
    mode: QueryMode
    confidence: float
    trust_decision: TrustDecision
    operator_A_reliability: OperatorReliability
    operator_B_reliability: OperatorReliability
    reliability_gap: float       # |A - B| reliability difference
    reasoning: str
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# OPERATOR RELIABILITY SCORER
# =============================================================================

class OperatorReliabilityScorer:
    """
    Scores how reliable each operator's evidence is for a given query.

    Key insight: Different query types need different evidence:
    - Numerical queries → XBRL/financial data is authoritative
    - Causal queries → Narrative/MD&A is authoritative
    - Mixed queries → Both are valuable
    """

    # Source authority scores by node type
    SOURCE_AUTHORITY = {
        "FINANCIAL_LINE": 1.0,    # XBRL-tagged, audited
        "TABLE_ROW": 0.9,         # Structured data
        "TABLE": 0.85,            # Structured data
        "TEXT_SECTION": 0.6,      # Narrative, may be contextual
        "NOTE": 0.5,              # Explanatory, may reference multiple periods
        "ENTITY": 0.4,            # Entity mentions, need context
    }

    # Query type to preferred evidence mapping
    QUERY_EVIDENCE_FIT = {
        # (query_type, node_type) → fit score
        (QueryType.NUMERICAL, "FINANCIAL_LINE"): 1.0,
        (QueryType.NUMERICAL, "TABLE_ROW"): 0.9,
        (QueryType.NUMERICAL, "TEXT_SECTION"): 0.4,  # Numbers in text may be out of context
        (QueryType.NUMERICAL, "NOTE"): 0.3,

        (QueryType.TEMPORAL, "FINANCIAL_LINE"): 0.9,
        (QueryType.TEMPORAL, "TEXT_SECTION"): 0.7,
        (QueryType.TEMPORAL, "NOTE"): 0.6,

        (QueryType.CAUSAL, "FINANCIAL_LINE"): 0.4,
        (QueryType.CAUSAL, "TEXT_SECTION"): 1.0,     # MD&A explains causes
        (QueryType.CAUSAL, "NOTE"): 0.8,

        (QueryType.DESCRIPTIVE, "TEXT_SECTION"): 1.0,
        (QueryType.DESCRIPTIVE, "NOTE"): 0.9,
        (QueryType.DESCRIPTIVE, "FINANCIAL_LINE"): 0.3,

        (QueryType.OPINION, "TEXT_SECTION"): 0.8,
        (QueryType.OPINION, "NOTE"): 0.7,
        (QueryType.OPINION, "FINANCIAL_LINE"): 0.2,
    }

    def score_operator(
        self,
        operator_name: str,
        evidence_types: Dict[str, int],
        path_confidence: float,
        query_classification: QueryClassification,
    ) -> OperatorReliability:
        """
        Score how reliable an operator's evidence is for this query.
        """

        # Calculate evidence quality (weighted by source authority)
        evidence_quality = self._compute_evidence_quality(evidence_types)

        # Calculate source authority (how authoritative are the sources?)
        source_authority = self._compute_source_authority(evidence_types)

        # Calculate query fit (how well does evidence match query type?)
        query_fit = self._compute_query_fit(evidence_types, query_classification.query_type)

        # Combine into overall reliability
        reliability_score = self._combine_reliability(
            evidence_quality=evidence_quality,
            source_authority=source_authority,
            query_fit=query_fit,
            path_confidence=path_confidence,
            query_classification=query_classification,
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            operator_name, evidence_types, query_classification,
            evidence_quality, source_authority, query_fit, reliability_score
        )

        return OperatorReliability(
            operator_name=operator_name,
            reliability_score=reliability_score,
            evidence_quality=evidence_quality,
            source_authority=source_authority,
            query_fit=query_fit,
            path_confidence=path_confidence,
            evidence_breakdown=evidence_types,
            reasoning=reasoning
        )

    def _compute_evidence_quality(self, evidence_types: Dict[str, int]) -> float:
        """Compute overall evidence quality."""
        if not evidence_types:
            return 0.0

        total = sum(evidence_types.values())
        if total == 0:
            return 0.0

        # Weighted sum by source authority
        weighted_sum = sum(
            count * self.SOURCE_AUTHORITY.get(node_type, 0.5)
            for node_type, count in evidence_types.items()
        )

        return weighted_sum / total

    def _compute_source_authority(self, evidence_types: Dict[str, int]) -> float:
        """Compute authority of sources (higher if more XBRL/structured data)."""
        total = sum(evidence_types.values())
        if total == 0:
            return 0.0

        # Proportion of high-authority sources
        high_authority = evidence_types.get("FINANCIAL_LINE", 0) + evidence_types.get("TABLE_ROW", 0)

        return high_authority / total

    def _compute_query_fit(
        self,
        evidence_types: Dict[str, int],
        query_type: QueryType
    ) -> float:
        """Compute how well evidence matches query type."""
        if not evidence_types:
            return 0.0

        total = sum(evidence_types.values())
        if total == 0:
            return 0.0

        # Weighted sum by query-evidence fit
        weighted_sum = 0.0
        for node_type, count in evidence_types.items():
            fit = self.QUERY_EVIDENCE_FIT.get((query_type, node_type), 0.5)
            weighted_sum += count * fit

        return weighted_sum / total

    def _combine_reliability(
        self,
        evidence_quality: float,
        source_authority: float,
        query_fit: float,
        path_confidence: float,
        query_classification: QueryClassification,
    ) -> float:
        """Combine factors into overall reliability score."""

        # Weights depend on query type
        if query_classification.numerical_expected:
            # For numerical queries, source authority is CRITICAL
            weights = {
                "evidence_quality": 0.15,
                "source_authority": 0.40,  # HIGH weight on XBRL
                "query_fit": 0.30,
                "path_confidence": 0.15,
            }
        elif query_classification.query_type in [QueryType.CAUSAL, QueryType.DESCRIPTIVE]:
            # For narrative queries, query fit matters more
            weights = {
                "evidence_quality": 0.20,
                "source_authority": 0.15,
                "query_fit": 0.45,         # HIGH weight on right evidence type
                "path_confidence": 0.20,
            }
        else:
            # Balanced
            weights = {
                "evidence_quality": 0.25,
                "source_authority": 0.25,
                "query_fit": 0.30,
                "path_confidence": 0.20,
            }

        reliability = (
            weights["evidence_quality"] * evidence_quality +
            weights["source_authority"] * source_authority +
            weights["query_fit"] * query_fit +
            weights["path_confidence"] * path_confidence
        )

        return min(1.0, max(0.0, reliability))

    def _generate_reasoning(
        self,
        operator_name: str,
        evidence_types: Dict[str, int],
        query_classification: QueryClassification,
        evidence_quality: float,
        source_authority: float,
        query_fit: float,
        reliability_score: float,
    ) -> str:
        """Generate human-readable reasoning."""

        parts = []

        # Evidence breakdown
        total = sum(evidence_types.values())
        financial_pct = evidence_types.get("FINANCIAL_LINE", 0) / total * 100 if total > 0 else 0
        narrative_pct = (evidence_types.get("TEXT_SECTION", 0) + evidence_types.get("NOTE", 0)) / total * 100 if total > 0 else 0

        parts.append(f"{operator_name}: {financial_pct:.0f}% financial, {narrative_pct:.0f}% narrative")

        # Query fit assessment
        if query_classification.numerical_expected:
            if source_authority > 0.5:
                parts.append("high XBRL coverage for numerical query")
            else:
                parts.append("low XBRL coverage for numerical query (less reliable)")

        # Overall assessment
        if reliability_score > 0.75:
            parts.append("HIGH reliability")
        elif reliability_score > 0.5:
            parts.append("MODERATE reliability")
        else:
            parts.append("LOW reliability")

        return "; ".join(parts)


# =============================================================================
# MODE SELECTOR
# =============================================================================

class ModeSelector:
    """
    Determines query mode and trust decision.

    Combines:
    1. Commutator (divergence between operators)
    2. Operator reliability (who to trust)
    3. Query classification (what type of query)
    4. Trajectory (how divergence changed over hops)
    """

    def __init__(self, llm_interface=None):
        # Use the new HybridQueryClassifier
        self.query_classifier = HybridQueryClassifier(
            llm_interface=llm_interface,
            enable_llm_fallback=llm_interface is not None
        )
        self.reliability_scorer = OperatorReliabilityScorer()

    def determine_mode(
        self,
        commutator: Any,
        trajectory: List[Any],
        query: str,
        operator_A_evidence_types: Dict[str, int],
        operator_B_evidence_types: Dict[str, int],
        operator_A_path_confidence: float,
        operator_B_path_confidence: float,
    ) -> ModeDecision:
        """
        Complete mode determination with trust decision.
        """

        # Step 1: Classify query
        query_class = self.query_classifier.classify(query)
        logger.debug(f"Query classified as: {query_class.query_type.value}, complexity={query_class.complexity}")

        # Step 2: Score operator reliability
        reliability_A = self.reliability_scorer.score_operator(
            "OperatorA",
            operator_A_evidence_types,
            operator_A_path_confidence,
            query_class
        )

        reliability_B = self.reliability_scorer.score_operator(
            "OperatorB",
            operator_B_evidence_types,
            operator_B_path_confidence,
            query_class
        )

        logger.debug(f"Reliability A: {reliability_A.reliability_score:.3f}, B: {reliability_B.reliability_score:.3f}")

        # Step 3: Compute reliability gap
        reliability_gap = abs(reliability_A.reliability_score - reliability_B.reliability_score)

        # Step 4: Determine trust decision
        trust_decision = self._determine_trust(
            commutator, reliability_A, reliability_B, reliability_gap, query_class
        )

        # Step 5: Determine mode
        mode, confidence = self._determine_mode_and_confidence(
            commutator, trajectory, query_class,
            reliability_A, reliability_B, trust_decision
        )

        # Step 6: Generate warnings if any
        warnings = self._generate_warnings(
            commutator, reliability_A, reliability_B, trust_decision
        )

        # Step 7: Generate reasoning
        reasoning = self._generate_reasoning(
            mode, trust_decision, commutator, query_class,
            reliability_A, reliability_B
        )

        return ModeDecision(
            mode=mode,
            confidence=confidence,
            trust_decision=trust_decision,
            operator_A_reliability=reliability_A,
            operator_B_reliability=reliability_B,
            reliability_gap=reliability_gap,
            reasoning=reasoning,
            warnings=warnings
        )

    def _determine_trust(
        self,
        commutator: Any,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        reliability_gap: float,
        query_class: QueryClassification,
    ) -> TrustDecision:
        """
        Determine which operator to trust.

        CRITICAL: For numerical queries expecting specific figures,
        we MUST trust the operator with more XBRL/financial evidence.
        """

        delta_A = commutator.delta_A  # Answer agreement

        # =========================================================================
        # SPECIAL CASE: Numerical queries with FINANCIAL_LINE dominance
        # =========================================================================
        # For numerical queries, XBRL data is authoritative. If one operator
        # has significantly more FINANCIAL_LINE evidence, trust that operator.
        # This prevents merging to incorrect approximate answers.

        if query_class.numerical_expected and query_class.query_type == QueryType.NUMERICAL:
            # Get FINANCIAL_LINE counts from evidence breakdown
            financial_A = reliability_A.evidence_breakdown.get("FINANCIAL_LINE", 0)
            financial_B = reliability_B.evidence_breakdown.get("FINANCIAL_LINE", 0)

            # Calculate financial evidence ratio
            total_financial = financial_A + financial_B
            if total_financial > 0:
                financial_ratio_A = financial_A / total_financial
                financial_ratio_B = financial_B / total_financial
            else:
                financial_ratio_A = financial_ratio_B = 0.5

            # CRITICAL FIX: For numerical queries, if one operator has
            # significantly more XBRL data (>=55%), trust that operator
            FINANCIAL_DOMINANCE_THRESHOLD = 0.55

            if financial_ratio_A >= FINANCIAL_DOMINANCE_THRESHOLD:
                logger.info(
                    f"TRUST_A: Operator A has {financial_ratio_A:.0%} of FINANCIAL_LINE "
                    f"evidence ({financial_A}/{total_financial}) for numerical query"
                )
                return TrustDecision.TRUST_A

            if financial_ratio_B >= FINANCIAL_DOMINANCE_THRESHOLD:
                logger.info(
                    f"TRUST_B: Operator B has {financial_ratio_B:.0%} of FINANCIAL_LINE "
                    f"evidence ({financial_B}/{total_financial}) for numerical query"
                )
                return TrustDecision.TRUST_B

            # If close to 50/50 but there's answer disagreement, check source authority
            if delta_A > 0.05:  # Answers differ slightly
                # Prefer operator with higher source authority score
                if reliability_A.source_authority > reliability_B.source_authority + 0.1:
                    logger.info(
                        f"TRUST_A: Higher source authority ({reliability_A.source_authority:.2f} vs "
                        f"{reliability_B.source_authority:.2f}) for numerical query with answer discrepancy"
                    )
                    return TrustDecision.TRUST_A
                elif reliability_B.source_authority > reliability_A.source_authority + 0.1:
                    logger.info(
                        f"TRUST_B: Higher source authority ({reliability_B.source_authority:.2f} vs "
                        f"{reliability_A.source_authority:.2f}) for numerical query with answer discrepancy"
                    )
                    return TrustDecision.TRUST_B

        # =========================================================================
        # SPECIAL CASE: Causal queries benefit from weighted merge
        # =========================================================================
        # For causal queries (e.g., "What factors drove..."), both operators
        # may have valuable perspectives. Use weighted merge to combine them
        # based on evidence quality rather than equal weighting.

        if query_class.query_type == QueryType.CAUSAL:
            logger.info(
                f"MERGE_WEIGHTED: Causal query benefits from weighted merge "
                f"(reliability A: {reliability_A.reliability_score:.2f}, "
                f"B: {reliability_B.reliability_score:.2f})"
            )
            return TrustDecision.MERGE_WEIGHTED

        # =========================================================================
        # SPECIAL CASE: Temporal queries need weighted merge for accuracy
        # =========================================================================
        # Temporal queries involving comparisons need careful weighting by
        # evidence quality to ensure correct direction (increase vs decrease).

        if query_class.query_type == QueryType.TEMPORAL:
            logger.info(
                f"MERGE_WEIGHTED: Temporal query requires weighted merge for accuracy"
            )
            return TrustDecision.MERGE_WEIGHTED

        # =========================================================================
        # STANDARD TRUST DECISION LOGIC
        # =========================================================================

        # If answers agree closely, no need to choose
        if delta_A < 0.10:
            return TrustDecision.MERGE_EQUAL

        # If large reliability gap, trust the more reliable one
        RELIABILITY_GAP_THRESHOLD = 0.25

        if reliability_gap > RELIABILITY_GAP_THRESHOLD:
            if reliability_A.reliability_score > reliability_B.reliability_score:
                return TrustDecision.TRUST_A
            else:
                return TrustDecision.TRUST_B

        # Moderate gap - merge but weight by reliability
        if reliability_gap > 0.10:
            return TrustDecision.MERGE_WEIGHTED

        # Small gap - merge equally
        return TrustDecision.MERGE_EQUAL

    def _determine_mode_and_confidence(
        self,
        commutator: Any,
        trajectory: List[Any],
        query_class: QueryClassification,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trust_decision: TrustDecision,
    ) -> Tuple[QueryMode, float]:
        """
        Determine mode with clear boundaries for each mode.

        FIX 2: Rewritten mode selection logic
        - ADAPTIVE is now the DEFAULT (middle ground)
        - Qualitative/descriptive queries can NEVER be EXPLOIT
        - EXPLOIT only for strong agreement on factual queries

        EXPLOIT: We know the answer (factual only, strong agreement)
        ADAPTIVE: Good answer with nuance (DEFAULT)
        EXPLORE: Genuinely uncertain or opinion-based
        """

        delta = commutator.combined
        delta_A = commutator.delta_A
        delta_E = commutator.delta_E

        trajectory_trend = self._analyze_trajectory(trajectory)

        # =========================================================================
        # FIX 2: Rule 1 - Qualitative queries can NEVER be EXPLOIT
        # =========================================================================

        is_qualitative_query = query_class.query_type in [
            QueryType.DESCRIPTIVE, QueryType.OPINION, QueryType.CAUSAL
        ]

        if is_qualitative_query:
            logger.debug(f"FIX 2: Qualitative query type {query_class.query_type.value} - EXPLOIT disabled")
            # For qualitative queries: ADAPTIVE or EXPLORE only
            if delta > 0.65 or trajectory_trend == "diverging":
                mode = QueryMode.EXPLORE
                confidence = self._compute_explore_confidence(
                    commutator, ["qualitative_query"], reliability_A, reliability_B
                )
                logger.info(f"EXPLORE: qualitative query with high divergence (delta={delta:.3f})")
            elif delta < 0.45:
                mode = QueryMode.ADAPTIVE
                confidence = self._compute_adaptive_confidence(
                    commutator, reliability_A, reliability_B, trajectory_trend
                )
                logger.info(f"ADAPTIVE: qualitative query with moderate agreement (delta={delta:.3f})")
            else:
                mode = QueryMode.EXPLORE
                confidence = self._compute_explore_confidence(
                    commutator, ["qualitative_moderate_divergence"], reliability_A, reliability_B
                )
                logger.info(f"EXPLORE: qualitative query (delta={delta:.3f})")
            return mode, confidence

        # =========================================================================
        # FIX 2: Rule 2 - EXPLOIT only for strong agreement on FACTUAL queries
        # =========================================================================

        exploit_conditions = []

        # EXPLOIT requires: factual query + strong agreement + low delta_A
        if query_class.query_type in [QueryType.NUMERICAL, QueryType.TEMPORAL]:
            if delta < 0.30 and delta_A < 0.15:
                exploit_conditions.append("strong_factual_agreement")

            # Additional: clear reliable source with agreement
            if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
                trusted_reliability = (
                    reliability_A.reliability_score
                    if trust_decision == TrustDecision.TRUST_A
                    else reliability_B.reliability_score
                )
                if trusted_reliability > 0.70 and delta_A < 0.20:
                    exploit_conditions.append("clear_reliable_source")

        # =========================================================================
        # FIX 2: Rule 3 - EXPLORE for high disagreement or diverging
        # =========================================================================

        explore_conditions = []

        # High divergence
        if delta > 0.65:
            explore_conditions.append("high_divergence")

        # Diverging trajectory with moderate divergence
        if trajectory_trend == "diverging" and delta > 0.55:
            explore_conditions.append("diverging_trajectory")

        # Both operators unreliable
        if reliability_A.reliability_score < 0.40 and reliability_B.reliability_score < 0.40:
            explore_conditions.append("both_unreliable")

        # Strong answer disagreement with no clear winner
        if delta_A > 0.45 and trust_decision in [TrustDecision.MERGE_EQUAL, TrustDecision.CONFLICT]:
            explore_conditions.append("answer_disagreement_no_winner")

        # =========================================================================
        # FIX 2: Mode Decision - ADAPTIVE is the DEFAULT
        # =========================================================================

        # EXPLORE if any explore condition
        if len(explore_conditions) >= 1:
            mode = QueryMode.EXPLORE
            confidence = self._compute_explore_confidence(
                commutator, explore_conditions, reliability_A, reliability_B
            )
            logger.info(f"EXPLORE triggered by: {explore_conditions}")

        # EXPLOIT only if factual query with strong agreement
        elif len(exploit_conditions) >= 1 and query_class.query_type == QueryType.NUMERICAL:
            mode = QueryMode.EXPLOIT
            confidence = self._compute_exploit_confidence(
                commutator, exploit_conditions, reliability_A, reliability_B, trust_decision
            )
            logger.info(f"EXPLOIT triggered by: {exploit_conditions}")

        # FIX 2: ADAPTIVE is the DEFAULT middle ground
        else:
            mode = QueryMode.ADAPTIVE
            confidence = self._compute_adaptive_confidence(
                commutator, reliability_A, reliability_B, trajectory_trend
            )
            logger.info(f"ADAPTIVE (default): exploit_conditions={exploit_conditions}, explore_conditions={explore_conditions}, delta={delta:.3f}")

        return mode, confidence

    def _compute_exploit_confidence(
        self,
        commutator: Any,
        conditions: List[str],
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trust_decision: TrustDecision,
    ) -> float:
        """Compute confidence for EXPLOIT mode."""

        # Base confidence
        base = 0.75

        # Boost for strong answer agreement
        if "strong_answer_agreement" in conditions:
            base += 0.10

        # Boost for clear reliable source
        if "clear_reliable_source" in conditions:
            trusted_rel = max(reliability_A.reliability_score, reliability_B.reliability_score)
            base += 0.10 * trusted_rel

        # Boost for good convergence
        if "good_convergence" in conditions:
            base += 0.05

        # Adjust by answer agreement
        base -= commutator.delta_A * 0.2

        return max(0.70, min(0.95, base))

    def _compute_adaptive_confidence(
        self,
        commutator: Any,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trajectory_trend: str,
    ) -> float:
        """Compute confidence for ADAPTIVE mode."""

        # Base confidence
        base = 0.60

        # Adjust by answer agreement
        if commutator.delta_A < 0.20:
            base += 0.10
        elif commutator.delta_A > 0.35:
            base -= 0.10

        # Adjust by average reliability
        avg_rel = (reliability_A.reliability_score + reliability_B.reliability_score) / 2
        base += (avg_rel - 0.5) * 0.15

        # Adjust by trajectory
        if trajectory_trend == "converging":
            base += 0.05
        elif trajectory_trend == "oscillating":
            base -= 0.05

        return max(0.50, min(0.75, base))

    def _compute_explore_confidence(
        self,
        commutator: Any,
        conditions: List[str],
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
    ) -> float:
        """Compute confidence for EXPLORE mode."""

        # Base confidence (lower for EXPLORE)
        base = 0.45

        # Further reduce for multiple explore triggers
        base -= 0.05 * (len(conditions) - 1)

        # Adjust by how bad the disagreement is
        base -= commutator.delta_A * 0.15

        # If both unreliable, reduce further
        if "both_unreliable" in conditions:
            base -= 0.10

        return max(0.30, min(0.55, base))

    def _analyze_trajectory(self, trajectory: List[Any]) -> str:
        """Analyze trajectory trend."""
        if len(trajectory) < 2:
            return "stable"

        deltas = [t.combined for t in trajectory]

        improvements = sum(1 for i in range(1, len(deltas)) if deltas[i] < deltas[i-1])
        worsening = sum(1 for i in range(1, len(deltas)) if deltas[i] > deltas[i-1])

        if improvements > worsening:
            return "converging"
        elif worsening > improvements:
            return "diverging"
        elif len(trajectory) > 2:
            direction_changes = sum(
                1 for i in range(2, len(deltas))
                if (deltas[i] - deltas[i-1]) * (deltas[i-1] - deltas[i-2]) < 0
            )
            if direction_changes > len(deltas) // 2:
                return "oscillating"

        return "stable"

    def _generate_warnings(
        self,
        commutator: Any,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
        trust_decision: TrustDecision,
    ) -> List[str]:
        """Generate warnings for edge cases."""
        warnings = []

        # Answer disagreement warning
        if commutator.delta_A > 0.40:
            warnings.append("Significant answer disagreement between operators")

        # Low reliability warning
        if reliability_A.reliability_score < 0.4 and reliability_B.reliability_score < 0.4:
            warnings.append("Both operators have low evidence reliability")

        # Trust decision with uncertainty
        if trust_decision in [TrustDecision.TRUST_A, TrustDecision.TRUST_B]:
            trusted = "A" if trust_decision == TrustDecision.TRUST_A else "B"
            other = "B" if trusted == "A" else "A"
            warnings.append(f"Trusting Operator {trusted} over {other} due to higher reliability for this query type")

        # Zero evidence overlap
        if commutator.delta_E > 0.90:
            warnings.append("Operators found almost completely different evidence")

        return warnings

    def _generate_reasoning(
        self,
        mode: QueryMode,
        trust_decision: TrustDecision,
        commutator: Any,
        query_class: QueryClassification,
        reliability_A: OperatorReliability,
        reliability_B: OperatorReliability,
    ) -> str:
        """Generate reasoning string."""

        parts = [f"Mode: {mode.value}"]

        # Query type
        parts.append(f"Query type: {query_class.query_type.value} ({query_class.complexity})")

        # Trust decision
        if trust_decision == TrustDecision.TRUST_A:
            parts.append(f"Trusting OperatorA (reliability {reliability_A.reliability_score:.2f} vs {reliability_B.reliability_score:.2f})")
        elif trust_decision == TrustDecision.TRUST_B:
            parts.append(f"Trusting OperatorB (reliability {reliability_B.reliability_score:.2f} vs {reliability_A.reliability_score:.2f})")
        elif trust_decision == TrustDecision.MERGE_WEIGHTED:
            parts.append("Merging with reliability weighting")
        else:
            parts.append("Merging equally")

        # Key metrics
        parts.append(f"Delta={commutator.combined:.3f}, Delta_A={commutator.delta_A:.3f}")

        return "; ".join(parts)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_mode_selector(llm_interface=None) -> ModeSelector:
    """Create a configured mode selector.

    Args:
        llm_interface: Optional LLM interface for fallback query classification.
                       If provided, enables LLM-based classification for ambiguous queries.
    """
    return ModeSelector(llm_interface=llm_interface)
