"""Explore/Exploit Controller for OpMech-GraphRAG.

Maps commutator divergence to traversal strategy.

Core principle:
    - Low divergence (Δ < τ_low) → EXPLOIT: shallow, focused, confident
    - High divergence (Δ > τ_high) → EXPLORE: deep, wide, uncertain
    - Medium divergence → ADAPTIVE: adjust based on trajectory

CONFIDENCE INTEGRATION:
    - In EXPLOIT mode: Prefer high-confidence edges (high min_edge_confidence)
    - In EXPLORE mode: Accept lower-confidence edges to find more paths
    - relevance_weight vs confidence_weight shifts based on mode
"""

from typing import List, Optional

from src.opmech.data_classes import CommutatorResult, TraversalStrategy


class ExploreExploitController:
    """
    Maps commutator divergence to traversal strategy.

    Parameter interpolation table:

    Parameter              | Exploit (w=0) | Explore (w=1)
    -----------------------|---------------|---------------
    max_hops               | 2             | 6
    seeds_per_operator     | 3             | 8
    nodes_per_hop          | 5             | 15
    min_edge_confidence    | 0.7           | 0.4
    top_k_evidence         | 10            | 25
    confidence_decay       | 0.95          | 0.85
    relevance_weight       | 0.5           | 0.7
    confidence_weight      | 0.5           | 0.3
    edge_types             | focused (3)   | all (8)
    """

    def __init__(
        self,
        tau_low: float = 0.25,
        tau_high: float = 0.60,
        max_hops: int = 6,
        min_hops: int = 1
    ):
        """
        Initialize the controller.

        Args:
            tau_low: Below this divergence: exploit mode (default 0.25)
            tau_high: Above this divergence: explore mode (default 0.60)
            max_hops: Maximum allowed hops (default 6)
            min_hops: Minimum hops before stopping (default 1)
        """
        self.tau_low = tau_low
        self.tau_high = tau_high
        self.max_hops = max_hops
        self.min_hops = min_hops

    def compute_strategy(
        self,
        commutator: CommutatorResult,
        trajectory: Optional[List[CommutatorResult]] = None
    ) -> TraversalStrategy:
        """
        Compute traversal strategy from commutator result.

        The explore_weight ∈ [0, 1] controls all parameters:
            - 0 = full exploit mode
            - 1 = full explore mode

        Args:
            commutator: Current commutator result
            trajectory: Optional list of previous commutator results

        Returns:
            TraversalStrategy with all parameters set
        """
        divergence = commutator.combined

        # Compute base explore weight from divergence
        if divergence < self.tau_low:
            explore_weight = 0.0
        elif divergence > self.tau_high:
            explore_weight = 1.0
        else:
            # Linear interpolation
            explore_weight = (divergence - self.tau_low) / (self.tau_high - self.tau_low)

        # Adjust based on trajectory (if available)
        if trajectory and len(trajectory) >= 2:
            trend = trajectory[-1].combined - trajectory[-2].combined

            if trend > 0.1:
                # Divergence increasing → need more exploration
                explore_weight = min(1.0, explore_weight + 0.25)
            elif trend < -0.1:
                # Divergence decreasing → converging, can exploit more
                explore_weight = max(0.0, explore_weight - 0.15)

        # Adjust based on operator score difference
        score_diff = abs(commutator.operator_A_score - commutator.operator_B_score)
        if score_diff > 0.3:
            # One operator much better → slight exploration to verify
            explore_weight = max(explore_weight, 0.3)

        # Adjust based on confidence divergence specifically
        if commutator.delta_C > 0.5:
            # High confidence disagreement → explore more
            explore_weight = min(1.0, explore_weight + 0.15)

        return self._build_strategy(explore_weight, commutator.hop)

    def _build_strategy(self, w: float, current_hop: int) -> TraversalStrategy:
        """
        Build concrete strategy from explore weight.

        Parameter interpolation:
            Parameter              | Exploit (w=0) | Explore (w=1)
            -----------------------|---------------|---------------
            max_hops               | 2             | 6
            seeds_per_operator     | 3             | 8
            nodes_per_hop          | 5             | 15
            min_edge_confidence    | 0.7           | 0.4
            top_k_evidence         | 10            | 25
            confidence_decay       | 0.95          | 0.85
            relevance_weight       | 0.5           | 0.7
            confidence_weight      | 0.5           | 0.3
            edge_types             | focused (3)   | all (8)

        KEY INSIGHT:
            - EXPLOIT mode: High min_edge_confidence, balance relevance/confidence equally
            - EXPLORE mode: Low min_edge_confidence (accept weaker edges), prioritize relevance

        Args:
            w: Explore weight in [0, 1]
            current_hop: Current hop number

        Returns:
            Fully configured TraversalStrategy
        """
        # Interpolate parameters
        max_hops = int(2 + w * 4)                    # 2 → 6
        seeds_per_operator = int(3 + w * 5)          # 3 → 8
        nodes_per_hop = int(5 + w * 10)              # 5 → 15
        min_edge_confidence = 0.7 - w * 0.3          # 0.7 → 0.4
        top_k_evidence = int(10 + w * 15)            # 10 → 25

        # Confidence-related parameters
        confidence_decay = 0.95 - w * 0.10           # 0.95 → 0.85
        relevance_weight = 0.5 + w * 0.2             # 0.5 → 0.7 (more relevance in explore)
        confidence_weight = 0.5 - w * 0.2            # 0.5 → 0.3 (less confidence in explore)

        # Edge type selection for Operator A (Structure-First)
        if w < 0.3:
            edge_types_A = ["TEMPORAL_NEXT", "EXPLAINS_LINE_ITEM"]
        elif w < 0.7:
            edge_types_A = ["TEMPORAL_NEXT", "EXPLAINS_LINE_ITEM", "REFERS_TO"]
        else:
            edge_types_A = [
                "TEMPORAL_NEXT", "EXPLAINS_LINE_ITEM", "REFERS_TO",
                "DISCUSSES", "SEMANTICALLY_SIMILAR"
            ]

        # Edge type selection for Operator B (Narrative-First)
        if w < 0.3:
            edge_types_B = ["CAUSED_BY", "DISCUSSES"]
        elif w < 0.7:
            edge_types_B = ["CAUSED_BY", "DISCUSSES", "MENTIONS_ENTITY", "REFERS_TO"]
        else:
            edge_types_B = [
                "CAUSED_BY", "DISCUSSES", "MENTIONS_ENTITY", "REFERS_TO",
                "SEMANTICALLY_SIMILAR", "ENTITY_RELATED_TO", "LEADS_TO"
            ]

        # Output mode
        if w < 0.3:
            output_mode = "exploit"
        elif w < 0.7:
            output_mode = "adaptive"
        else:
            output_mode = "explore"

        return TraversalStrategy(
            max_hops=max_hops,
            current_hop=current_hop,
            seeds_per_operator=seeds_per_operator,
            nodes_per_hop=nodes_per_hop,
            edge_types_A=edge_types_A,
            edge_types_B=edge_types_B,
            min_edge_confidence=min_edge_confidence,
            top_k_evidence=top_k_evidence,
            confidence_decay=confidence_decay,
            relevance_weight=relevance_weight,
            confidence_weight=confidence_weight,
            output_mode=output_mode,
            tau_low=self.tau_low,
            tau_high=self.tau_high,
            explore_weight=w
        )

    def get_initial_strategy(self) -> TraversalStrategy:
        """
        Get an initial balanced strategy for the first hop.

        Returns:
            TraversalStrategy with balanced (w=0.5) parameters
        """
        return self._build_strategy(0.5, current_hop=1)
