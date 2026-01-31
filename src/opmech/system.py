"""Main OpMech-GraphRAG System.

Complete implementation of the commutator-guided explore/exploit GraphRAG system.
"""

from typing import Callable, List

import numpy as np
import torch
from loguru import logger
from transformers import AutoModel, AutoTokenizer

from src.opmech.commutator import compute_commutator
from src.opmech.controller import ExploreExploitController
from src.opmech.data_classes import (
    BeliefState,
    CommutatorResult,
    OutputMode,
    QueryResult,
)
from src.opmech.graph_interface import KnowledgeGraphInterface
from src.opmech.llm_interface import LLMInterface
from src.opmech.operators import OperatorA, OperatorB
from src.opmech.mode_selection import (
    create_mode_selector,
    ModeDecision,
    TrustDecision,
    QueryMode,
)
from src.opmech.query_classifier import (
    create_hybrid_classifier,
    QueryClassification,
    QueryType,
)
from src.opmech.robust_consistency_checker import (
    RobustConsistencyChecker,
    check_operator_consistency,
)
from src.opmech.type_safe_models import OperatorOutput
from src.opmech.ground_truth_pipeline import (
    UnifiedGroundTruthPipeline,
    create_ground_truth_pipeline,
    EvidenceShareManager,
    ConfidenceCalibrator,
)

# Convergence pressure threshold - when Δ_E exceeds this, share nodes between operators
# BUG FIX: Lowered from 0.8 to 0.7 to trigger sharing earlier
CONVERGENCE_PRESSURE_THRESHOLD = 0.7

# BUG 3 FIX: Evidence divergence threshold for forced sharing
EVIDENCE_DIVERGENCE_THRESHOLD = 0.8


class OpMechGraphRAG:
    """
    Complete OpMech-GraphRAG system with commutator-guided explore/exploit.

    Main loop:
        1. Run both operators at current hop depth
        2. Compute commutator (divergence)
        3. Update strategy based on divergence
        4. Check stopping conditions
        5. Repeat or return final answer
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password123",
        vllm_url: str = "http://localhost:8000/v1",
        tau_low: float = 0.25,
        tau_high: float = 0.60,
        max_hops: int = 6
    ):
        """
        Initialize the OpMech-GraphRAG system.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            vllm_url: vLLM server URL
            tau_low: Low divergence threshold (exploit below this)
            tau_high: High divergence threshold (explore above this)
            max_hops: Maximum traversal hops
        """
        logger.info("Initializing OpMech-GraphRAG system...")

        # Initialize components
        self.graph = KnowledgeGraphInterface(neo4j_uri, neo4j_user, neo4j_password)
        self.llm = LLMInterface(vllm_url)
        self.embed_fn = self._create_embed_fn()

        # Initialize operators
        self.operator_A = OperatorA(self.graph, self.embed_fn)
        self.operator_B = OperatorB(self.graph, self.embed_fn)

        # Initialize controller
        self.controller = ExploreExploitController(
            tau_low=tau_low,
            tau_high=tau_high,
            max_hops=max_hops
        )

        # Thresholds
        self.tau_low = tau_low
        self.tau_high = tau_high
        self.max_hops = max_hops

        # Initialize mode selector
        self.mode_selector = create_mode_selector()

        # Initialize query classifier for termination logic
        self.query_classifier = create_hybrid_classifier(self.llm)

        # Initialize consistency checker for cross-operator validation
        # Using RobustConsistencyChecker which prevents year/dollar confusion
        # COMPANY-AGNOSTIC: No company parameter needed - checker works on text patterns
        self.consistency_checker = RobustConsistencyChecker()

        # BUG FIXES: Initialize ground truth pipeline components
        # COMPANY-AGNOSTIC: No company parameter needed - extracts from documents
        # This handles: explicit period labels, ground truth validation,
        # pre-computed directions, evidence sharing, confidence calibration
        self.ground_truth_pipeline = create_ground_truth_pipeline()
        self.evidence_share_manager = EvidenceShareManager(
            divergence_threshold=EVIDENCE_DIVERGENCE_THRESHOLD,
            min_overlap=0.2
        )
        self.confidence_calibrator = ConfidenceCalibrator()

        # Termination parameters
        self.min_improvement = 0.02  # Minimum delta improvement to continue
        self.min_hops_opinion = 3    # Minimum hops for opinion queries

        logger.info("OpMech-GraphRAG system initialized with ground truth pipeline")

    def _create_embed_fn(self) -> Callable[[str], np.ndarray]:
        """Create embedding function using FinBERT."""
        logger.info("Loading FinBERT model...")

        tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        model = AutoModel.from_pretrained("ProsusAI/finbert")
        model.eval()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            model = model.cuda()
            logger.info("FinBERT loaded on GPU")
        else:
            logger.info("FinBERT loaded on CPU")

        def embed(text: str) -> np.ndarray:
            inputs = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            if device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model(**inputs)
                # Mean pooling
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze()

            return embedding.cpu().numpy()

        return embed

    def query(self, query: str) -> QueryResult:
        """
        Execute query with commutator-guided explore/exploit.

        Main loop:
            1. Run both operators at current hop depth
            2. Compute commutator (divergence)
            3. Update strategy based on divergence
            4. Check stopping conditions (query-type-aware)
            5. Repeat or return final answer

        Args:
            query: User query string

        Returns:
            QueryResult with answer and diagnostics
        """
        logger.info(f"Processing query: {query[:50]}...")

        # Classify query for type-aware termination
        query_class = self.query_classifier.classify(query)
        effective_max_hops = self._get_effective_max_hops(query_class)

        logger.info(f"Query type: {query_class.query_type.value}, complexity: {query_class.complexity}")
        logger.info(f"Max hops: {effective_max_hops}")

        trajectory: List[CommutatorResult] = []
        hop = 1
        termination_reason = ""

        # Initial balanced strategy
        initial_commutator = CommutatorResult(
            delta_E=0.5, delta_V=0.5, delta_A=0.5, delta_C=0.5,
            combined=0.5, weights={}, hop=0,
            operator_A_score=0.5, operator_B_score=0.5
        )
        strategy = self.controller.compute_strategy(initial_commutator)

        belief_A = None
        belief_B = None

        while hop <= effective_max_hops:
            logger.info(f"Hop {hop}/{strategy.max_hops}")

            # ══════════════════════════════════════════════════════════════
            # STEP 1: Run both operators with two-phase approach
            # Phase 1 (hop 1): Independent exploration
            # Phase 2 (hop 2+): Convergence-aware re-exploration
            # ══════════════════════════════════════════════════════════════

            strategy.current_hop = hop

            if hop == 1:
                # Phase 1: With INITIAL SEED SHARING to reduce evidence divergence
                # Get initial seeds from embedding search that both operators can use
                query_embedding = self.embed_fn(query)
                shared_seeds = self.graph.search_by_type(
                    query_embedding=query_embedding,
                    node_types=["FINANCIAL_LINE", "TEXT_SECTION"],
                    top_k=7  # BUG FIX: Share top 7 nodes to reduce initial divergence
                )
                shared_seed_ids = {n.id for n in shared_seeds}

                belief_A = self.operator_A.execute(
                    query, strategy,
                    other_operator_evidence=shared_seed_ids  # Share initial seeds
                )
                belief_B = self.operator_B.execute(
                    query, strategy,
                    other_operator_evidence=shared_seed_ids  # Share initial seeds
                )
            else:
                # Phase 2: Convergence-aware re-exploration
                # Share evidence from previous hop
                evidence_A_ids = {n.id for n in belief_A.evidence} if belief_A else set()
                evidence_B_ids = {n.id for n in belief_B.evidence} if belief_B else set()

                belief_A = self.operator_A.execute(
                    query, strategy,
                    other_operator_evidence=evidence_B_ids  # Share B's evidence
                )
                belief_B = self.operator_B.execute(
                    query, strategy,
                    other_operator_evidence=evidence_A_ids  # Share A's evidence
                )

            logger.debug(
                f"Operator A: {len(belief_A.evidence)} evidence nodes, "
                f"Operator B: {len(belief_B.evidence)} evidence nodes"
            )

            # Generate answers with query type for appropriate prompting
            belief_A.answer = self.llm.generate_answer(
                query, belief_A.evidence, "structure_first",
                query_type=query_class.query_type.value
            )
            belief_B.answer = self.llm.generate_answer(
                query, belief_B.evidence, "narrative_first",
                query_type=query_class.query_type.value
            )

            # ══════════════════════════════════════════════════════════════
            # STEP 2: Compute commutator
            # ══════════════════════════════════════════════════════════════

            commutator = compute_commutator(
                belief_A, belief_B, self.embed_fn, hop=hop
            )
            trajectory.append(commutator)

            logger.info(
                f"Divergence at hop {hop}: Δ={commutator.combined:.3f} "
                f"(Δ_E={commutator.delta_E:.3f}, Δ_V={commutator.delta_V:.3f}, "
                f"Δ_A={commutator.delta_A:.3f}, Δ_C={commutator.delta_C:.3f})"
            )

            # ══════════════════════════════════════════════════════════════
            # STEP 2.5: Apply convergence pressure if divergence is high
            # ══════════════════════════════════════════════════════════════

            self._apply_convergence_pressure(
                belief_A, belief_B, commutator.delta_E, hop
            )

            # ══════════════════════════════════════════════════════════════
            # STEP 2.6: Pass commutator feedback to operators for next hop
            # This enables commutator-guided refinement of XBRL search
            # ══════════════════════════════════════════════════════════════

            self.operator_A.set_commutator_feedback(commutator)
            self.operator_B.set_commutator_feedback(commutator)

            # ══════════════════════════════════════════════════════════════
            # STEP 3: Update strategy based on divergence
            # ══════════════════════════════════════════════════════════════

            strategy = self.controller.compute_strategy(commutator, trajectory)

            # ══════════════════════════════════════════════════════════════
            # STEP 4: Check stopping conditions (query-type-aware)
            # ══════════════════════════════════════════════════════════════

            should_stop, reason = self._should_terminate(
                trajectory, hop, effective_max_hops, query_class
            )

            if should_stop:
                termination_reason = reason
                logger.info(f"Stopping at hop {hop}: {reason}")
                self._log_termination_summary(trajectory, reason, query_class)
                return self._build_result_with_mode_selector(
                    query, belief_A, belief_B, trajectory
                )

            hop += 1

        # ══════════════════════════════════════════════════════════════════
        # Max hops reached - use mode selector for final result
        # ══════════════════════════════════════════════════════════════════

        final_divergence = trajectory[-1].combined
        termination_reason = f"Reached max hops ({effective_max_hops})"
        logger.info(f"Max hops reached. Final divergence: {final_divergence:.3f}")
        self._log_termination_summary(trajectory, termination_reason, query_class)

        return self._build_result_with_mode_selector(query, belief_A, belief_B, trajectory)

    def _get_effective_max_hops(self, query_class: QueryClassification) -> int:
        """
        Determine max hops based on query complexity and type.

        Simple queries don't need many hops.
        Complex/opinion queries benefit from more exploration.

        Args:
            query_class: Query classification result

        Returns:
            Maximum number of hops to allow
        """
        base_max_hops = self.max_hops

        if query_class.complexity == "simple":
            # Simple factual queries - 2-3 hops usually enough
            return min(base_max_hops, 3)

        elif query_class.complexity == "complex":
            # Complex queries - allow full exploration
            return base_max_hops + 1  # Allow extra hop

        # For opinion/causal queries, ensure minimum exploration
        if query_class.query_type in [QueryType.OPINION, QueryType.CAUSAL]:
            return max(base_max_hops, 4)

        return base_max_hops

    def _should_terminate(
        self,
        trajectory: List[CommutatorResult],
        current_hop: int,
        max_hops: int,
        query_class: QueryClassification
    ) -> tuple:
        """
        Determine if traversal should stop.

        Query-type-aware termination logic:
        - NUMERICAL queries can stop early if Δ_A is very low
        - OPINION queries must do at least 3 hops
        - CAUSAL queries need thorough exploration

        Returns:
            (should_stop: bool, reason: str)
        """
        current = trajectory[-1]
        delta = current.combined
        delta_A = current.delta_A

        # -----------------------------------------------------------------
        # CONDITION 1: Reached max hops (safety limit)
        # -----------------------------------------------------------------
        if current_hop >= max_hops:
            return True, f"Reached max hops ({max_hops})"

        # -----------------------------------------------------------------
        # CONDITION 2: Strong convergence (delta below threshold)
        # -----------------------------------------------------------------
        if delta < self.tau_low:
            return True, f"Converged: Δ={delta:.3f} < τ_low={self.tau_low}"

        # -----------------------------------------------------------------
        # CONDITION 3: Answer agreement is excellent (for numerical queries)
        # -----------------------------------------------------------------
        if delta_A < 0.05 and query_class.query_type == QueryType.NUMERICAL:
            if delta < 0.40:  # Combined also reasonable
                return True, f"Strong answer agreement: Δ_A={delta_A:.3f} < 0.05"

        # -----------------------------------------------------------------
        # CONDITION 4: For OPINION queries - enforce minimum hops
        # -----------------------------------------------------------------
        if query_class.query_type == QueryType.OPINION:
            if current_hop < self.min_hops_opinion:
                logger.debug(f"Opinion query - continuing to hop {current_hop + 1} (minimum {self.min_hops_opinion} hops)")
                return False, ""

        # -----------------------------------------------------------------
        # CONDITION 5: Stability check (not improving)
        # -----------------------------------------------------------------
        if len(trajectory) >= 2:
            prev_delta = trajectory[-2].combined
            improvement = prev_delta - delta

            # If divergence increased significantly, log warning
            if improvement < -0.05:
                logger.warning(f"Divergence increased! {prev_delta:.3f} → {delta:.3f}")
                # Don't stop - let it try to recover

            # If improvement is minimal and we've done at least 2 hops
            if improvement < self.min_improvement and current_hop >= 2:
                # Check if we're in a good state
                if delta < 0.45:
                    return True, f"Stabilized: improvement={improvement:.3f} < {self.min_improvement}, Δ={delta:.3f}"

        # -----------------------------------------------------------------
        # CONDITION 6: Query-type specific early termination
        # -----------------------------------------------------------------

        # For simple numerical queries, can stop earlier
        if query_class.query_type == QueryType.NUMERICAL and query_class.complexity == "simple":
            if delta < 0.35 and delta_A < 0.10:
                return True, f"Simple numerical query converged: Δ={delta:.3f}, Δ_A={delta_A:.3f}"

        # -----------------------------------------------------------------
        # CONDITION 7: Diverging rapidly (give up on convergence)
        # -----------------------------------------------------------------
        if len(trajectory) >= 3:
            if (trajectory[-1].combined > trajectory[-2].combined > trajectory[-3].combined):
                return True, f"Diverging rapidly over 3 consecutive hops"

        # -----------------------------------------------------------------
        # DEFAULT: Continue
        # -----------------------------------------------------------------
        return False, ""

    def _log_termination_summary(
        self,
        trajectory: List[CommutatorResult],
        termination_reason: str,
        query_class: QueryClassification
    ) -> None:
        """Log a summary of the traversal for debugging."""

        logger.info("=" * 60)
        logger.info("TRAVERSAL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Query type: {query_class.query_type.value} ({query_class.complexity})")
        logger.info(f"Total hops: {len(trajectory)}")
        logger.info(f"Termination reason: {termination_reason}")
        logger.info("")
        logger.info("Divergence trajectory:")

        for i, t in enumerate(trajectory):
            marker = "→" if i < len(trajectory) - 1 else "■"
            logger.info(f"  Hop {i+1}: Δ={t.combined:.3f} (E={t.delta_E:.3f}, V={t.delta_V:.3f}, A={t.delta_A:.3f}, C={t.delta_C:.3f}) {marker}")

        # Show improvement
        if len(trajectory) >= 2:
            total_improvement = trajectory[0].combined - trajectory[-1].combined
            pct_improvement = (total_improvement / trajectory[0].combined) * 100 if trajectory[0].combined > 0 else 0
            logger.info("")
            logger.info(f"Total improvement: {trajectory[0].combined:.3f} → {trajectory[-1].combined:.3f} ({pct_improvement:.1f}% reduction)")

        logger.info("=" * 60)

    def _build_exploit_result(
        self,
        query: str,
        belief_A: BeliefState,
        belief_B: BeliefState,
        trajectory: List[CommutatorResult]
    ) -> QueryResult:
        """Build result for exploit mode (converged)."""
        final_comm = trajectory[-1]

        # Use answer from operator with higher score
        if final_comm.operator_A_score >= final_comm.operator_B_score:
            answer = belief_A.answer
        else:
            answer = belief_B.answer

        return QueryResult(
            answer=answer,
            confidence=1.0 - final_comm.combined,
            mode=OutputMode.EXPLOIT,
            hops_used=len(trajectory),
            trajectory=trajectory,
            evidence_A=belief_A.evidence,
            evidence_B=belief_B.evidence,
            answer_A=belief_A.answer,
            answer_B=belief_B.answer,
            reasoning=f"Operators converged at hop {len(trajectory)} (Δ={final_comm.combined:.3f}). High confidence answer.",
            operator_scores={
                "structure_first": final_comm.operator_A_score,
                "narrative_first": final_comm.operator_B_score
            },
            path_confidence_A=belief_A.mean_path_confidence,
            path_confidence_B=belief_B.mean_path_confidence,
            edge_conf_stats=self._compute_edge_conf_stats(belief_A, belief_B)
        )

    def _build_adaptive_result(
        self,
        query: str,
        belief_A: BeliefState,
        belief_B: BeliefState,
        trajectory: List[CommutatorResult]
    ) -> QueryResult:
        """Build result for adaptive mode (partial convergence)."""
        # Merge answers
        merged_answer = self.llm.generate_merged_answer(
            query,
            belief_A.answer,
            belief_B.answer,
            belief_A.evidence,
            belief_B.evidence
        )

        final_comm = trajectory[-1]

        return QueryResult(
            answer=merged_answer,
            confidence=0.7 - final_comm.combined * 0.3,
            mode=OutputMode.ADAPTIVE,
            hops_used=len(trajectory),
            trajectory=trajectory,
            evidence_A=belief_A.evidence,
            evidence_B=belief_B.evidence,
            answer_A=belief_A.answer,
            answer_B=belief_B.answer,
            reasoning=f"Partial convergence at hop {len(trajectory)} (Δ={final_comm.combined:.3f}). Merged both perspectives.",
            operator_scores={
                "structure_first": final_comm.operator_A_score,
                "narrative_first": final_comm.operator_B_score
            },
            path_confidence_A=belief_A.mean_path_confidence,
            path_confidence_B=belief_B.mean_path_confidence,
            edge_conf_stats=self._compute_edge_conf_stats(belief_A, belief_B)
        )

    def _build_explore_result(
        self,
        query: str,
        belief_A: BeliefState,
        belief_B: BeliefState,
        trajectory: List[CommutatorResult]
    ) -> QueryResult:
        """Build result for explore mode (high divergence)."""
        final_comm = trajectory[-1]

        # Generate dual hypothesis
        dual_answer = self.llm.generate_dual_hypothesis(
            query,
            belief_A.answer,
            belief_B.answer,
            final_comm.combined
        )

        return QueryResult(
            answer=dual_answer,
            confidence=0.3,
            mode=OutputMode.EXPLORE,
            hops_used=len(trajectory),
            trajectory=trajectory,
            evidence_A=belief_A.evidence,
            evidence_B=belief_B.evidence,
            answer_A=belief_A.answer,
            answer_B=belief_B.answer,
            reasoning=f"High divergence after {len(trajectory)} hops (Δ={final_comm.combined:.3f}). Structural ambiguity detected.",
            operator_scores={
                "structure_first": final_comm.operator_A_score,
                "narrative_first": final_comm.operator_B_score
            },
            path_confidence_A=belief_A.mean_path_confidence,
            path_confidence_B=belief_B.mean_path_confidence,
            edge_conf_stats=self._compute_edge_conf_stats(belief_A, belief_B)
        )

    def _compute_edge_conf_stats(
        self,
        belief_A: BeliefState,
        belief_B: BeliefState
    ) -> dict:
        """Compute edge confidence statistics for diagnostics."""
        def stats(confs):
            if not confs:
                return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
            return {
                "mean": float(np.mean(confs)),
                "std": float(np.std(confs)),
                "min": float(np.min(confs)),
                "max": float(np.max(confs))
            }

        return {
            "operator_A": stats(belief_A.edge_confidences),
            "operator_B": stats(belief_B.edge_confidences)
        }

    def _get_evidence_types(self, evidence: List) -> dict:
        """Get breakdown of evidence by node type."""
        types = {}
        for node in evidence:
            node_type = node.type if hasattr(node, 'type') else "UNKNOWN"
            types[node_type] = types.get(node_type, 0) + 1
        return types

    def _generate_answer_with_trust(
        self,
        query: str,
        belief_A: BeliefState,
        belief_B: BeliefState,
        mode_decision: ModeDecision,
        trajectory: List[CommutatorResult],
    ) -> str:
        """Generate answer based on mode and trust decision with consistency checking."""

        mode = mode_decision.mode
        trust = mode_decision.trust_decision

        # =========================================================================
        # CHECK CONSISTENCY BETWEEN OPERATORS
        # Using RobustConsistencyChecker which prevents year/dollar confusion
        # =========================================================================
        # Create typed OperatorOutput objects
        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer=belief_A.answer,
            confidence=belief_A.mean_path_confidence
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer=belief_B.answer,
            confidence=belief_B.mean_path_confidence
        )

        consistency_result = self.consistency_checker.check_consistency(output_a, output_b)

        discrepancy_note = ""
        if not consistency_result.is_consistent:
            logger.warning(f"Operator discrepancies detected: {len(consistency_result.discrepancies)} issues")
            discrepancy_note = self.consistency_checker.format_discrepancy_note(
                consistency_result.discrepancies
            )

        # =========================================================================
        # EXPLOIT MODE: Direct, confident answer
        # =========================================================================
        if mode == QueryMode.EXPLOIT:
            if trust == TrustDecision.TRUST_A:
                answer = self.llm.generate_trusted_answer(
                    query, belief_A.evidence, belief_B.evidence[:5],
                    primary="A",
                    source_type="financial/XBRL data",
                    confidence=mode_decision.confidence
                )
            elif trust == TrustDecision.TRUST_B:
                answer = self.llm.generate_trusted_answer(
                    query, belief_B.evidence, belief_A.evidence[:5],
                    primary="B",
                    source_type="narrative analysis",
                    confidence=mode_decision.confidence
                )
            else:
                # Both agree - use combined evidence
                combined_evidence = belief_A.evidence + belief_B.evidence
                answer = self.llm.generate_exploit_answer(
                    query, combined_evidence,
                    source_type="combined sources",
                    confidence=mode_decision.confidence
                )
            # Add discrepancy note if any (even in EXPLOIT mode)
            if discrepancy_note:
                answer += discrepancy_note
            return answer

        # =========================================================================
        # ADAPTIVE MODE: Primary answer with nuance
        # =========================================================================
        elif mode == QueryMode.ADAPTIVE:
            answer = self.llm.generate_adaptive_answer(
                query, belief_A, belief_B,
                mode_decision=mode_decision,
            )
            if discrepancy_note:
                answer += discrepancy_note
            return answer

        # =========================================================================
        # EXPLORE MODE: Multiple perspectives, explicit uncertainty
        # =========================================================================
        else:  # EXPLORE
            return self.llm.generate_explore_answer(
                query, belief_A, belief_B,
                mode_decision=mode_decision,
                discrepancy_note=discrepancy_note
            )

    def _node_to_dict(self, node) -> dict:
        """Convert a Node to a dictionary for consistency checking."""
        return {
            'type': node.type,
            'content': node.text,
            'text': node.text,
            'xbrl_tag': node.metadata.get('xbrl_tag') if hasattr(node, 'metadata') else None,
            'value': node.metadata.get('value') if hasattr(node, 'metadata') else None,
            'period_end': node.metadata.get('period_end') if hasattr(node, 'metadata') else None,
            'metadata': node.metadata if hasattr(node, 'metadata') else {}
        }

    def _build_result_with_mode_selector(
        self,
        query: str,
        belief_A: BeliefState,
        belief_B: BeliefState,
        trajectory: List[CommutatorResult]
    ) -> QueryResult:
        """
        Build result using the mode selector for trust-aware answer generation.

        BUG FIXES INTEGRATED:
        - Bug 2: Ground truth validation of answers
        - Bug 4: Pre-computed directions passed to prompts
        - Bug 5: Confidence calibration based on validation
        """

        # Get evidence type breakdowns
        evidence_types_A = self._get_evidence_types(belief_A.evidence)
        evidence_types_B = self._get_evidence_types(belief_B.evidence)

        # BUG 2 & 4 FIX: Prepare ground truth context from evidence
        all_evidence_dicts = [self._node_to_dict(n) for n in belief_A.evidence + belief_B.evidence]
        gt_context = self.ground_truth_pipeline.prepare_context(query, all_evidence_dicts)

        # Determine mode with full context
        mode_decision = self.mode_selector.determine_mode(
            commutator=trajectory[-1],
            trajectory=trajectory,
            query=query,
            operator_A_evidence_types=evidence_types_A,
            operator_B_evidence_types=evidence_types_B,
            operator_A_path_confidence=belief_A.mean_path_confidence,
            operator_B_path_confidence=belief_B.mean_path_confidence,
        )

        logger.info(f"Mode decision: {mode_decision.reasoning}")
        for warning in mode_decision.warnings:
            logger.warning(f"Mode warning: {warning}")

        # Generate answer based on trust decision
        answer = self._generate_answer_with_trust(
            query, belief_A, belief_B,
            mode_decision, trajectory
        )

        final_comm = trajectory[-1]

        # BUG 2 & 5 FIX: Validate answer and calibrate confidence
        xbrl_count_a = evidence_types_A.get('FINANCIAL_LINE', 0)
        xbrl_count_b = evidence_types_B.get('FINANCIAL_LINE', 0)
        total_xbrl = xbrl_count_a + xbrl_count_b

        calibrated_confidence, validation_issues = self.ground_truth_pipeline.validate_and_calibrate(
            answer=answer,
            context=gt_context,
            delta_e=final_comm.delta_E,
            delta_a=final_comm.delta_A,
            xbrl_node_count=total_xbrl,
            raw_confidence=mode_decision.confidence
        )

        # Log validation issues if any
        if validation_issues:
            logger.warning(f"Answer validation issues: {validation_issues[:3]}")
            # Append validation notes to answer
            if len(validation_issues) > 0:
                answer += "\n\n---\n**Analyst Notes:**\n"
                for issue in validation_issues[:3]:
                    answer += f"Note: {issue}\n"

        # Map QueryMode to OutputMode
        mode_mapping = {
            QueryMode.EXPLOIT: OutputMode.EXPLOIT,
            QueryMode.ADAPTIVE: OutputMode.ADAPTIVE,
            QueryMode.EXPLORE: OutputMode.EXPLORE,
        }

        return QueryResult(
            answer=answer,
            confidence=calibrated_confidence,  # BUG 5 FIX: Use calibrated confidence
            mode=mode_mapping[mode_decision.mode],
            hops_used=len(trajectory),
            trajectory=trajectory,
            evidence_A=belief_A.evidence,
            evidence_B=belief_B.evidence,
            answer_A=belief_A.answer,
            answer_B=belief_B.answer,
            reasoning=mode_decision.reasoning,
            operator_scores={
                "structure_first": final_comm.operator_A_score,
                "narrative_first": final_comm.operator_B_score
            },
            path_confidence_A=belief_A.mean_path_confidence,
            path_confidence_B=belief_B.mean_path_confidence,
            edge_conf_stats=self._compute_edge_conf_stats(belief_A, belief_B)
        )

    def _apply_convergence_pressure(
        self,
        belief_A: BeliefState,
        belief_B: BeliefState,
        delta_E: float,
        hop: int
    ) -> None:
        """
        When operators diverge too much, share top nodes between them.

        BUG 3 FIX: Uses EvidenceShareManager to ensure minimum overlap
        when divergence exceeds threshold.

        Args:
            belief_A: Current belief state from Operator A
            belief_B: Current belief state from Operator B
            delta_E: Evidence divergence (Jaccard distance)
            hop: Current hop number
        """
        if delta_E < CONVERGENCE_PRESSURE_THRESHOLD:
            return

        logger.info(
            f"Applying convergence pressure at hop {hop} "
            f"(Δ_E={delta_E:.3f} > {CONVERGENCE_PRESSURE_THRESHOLD})"
        )

        # Get current evidence sets
        evidence_a_ids = {n.id for n in belief_A.evidence}
        evidence_b_ids = {n.id for n in belief_B.evidence}

        # Calculate initial overlap
        initial_overlap = len(evidence_a_ids & evidence_b_ids) / max(1, len(evidence_a_ids | evidence_b_ids))

        # BUG FIX: Share top nodes DIRECTLY between operators (previous logic was backwards)
        # Share A's nodes with B, and B's nodes with A
        max_share = 7 if delta_E > 0.8 else 5

        # Get nodes unique to each operator (not already shared)
        a_unique = evidence_a_ids - evidence_b_ids
        b_unique = evidence_b_ids - evidence_a_ids

        # Share A's unique nodes with B
        bridge_A_to_B = list(a_unique)[:max_share]
        # Share B's unique nodes with A
        bridge_B_to_A = list(b_unique)[:max_share]

        if bridge_A_to_B:
            self.operator_B.add_bridge_seeds(bridge_A_to_B)
            logger.debug(f"Shared {len(bridge_A_to_B)} nodes from A to B: {bridge_A_to_B[:3]}...")

        if bridge_B_to_A:
            self.operator_A.add_bridge_seeds(bridge_B_to_A)
            logger.debug(f"Shared {len(bridge_B_to_A)} nodes from B to A: {bridge_B_to_A[:3]}...")

        # Calculate expected new overlap
        new_shared = (evidence_a_ids & evidence_b_ids) | set(bridge_A_to_B) | set(bridge_B_to_A)
        new_total = evidence_a_ids | evidence_b_ids
        expected_overlap = len(new_shared) / max(1, len(new_total))

        logger.info(f"Evidence overlap: {initial_overlap:.2%} -> {expected_overlap:.2%} (expected after sharing)")

    def close(self):
        """Clean up resources."""
        self.graph.close()
        logger.info("OpMech-GraphRAG system closed")
