"""OpMech-GraphRAG: Commutator-Guided Explore/Exploit GraphRAG System.

Production System Components:
- Type-safe data models (FiscalPeriod, FinancialValue)
- Evidence extraction with proper type separation
- Temporal intelligence with pre-computed changes
- Robust consistency checking

These components prevent bugs like FY2023 being parsed as $2,023.
"""

from src.opmech.data_classes import (
    BeliefState,
    CommutatorResult,
    Edge,
    Node,
    OutputMode,
    QueryResult,
    TraversalStrategy,
    TraversedNode,
)
from src.opmech.commutator import (
    compute_answer_divergence,
    compute_commutator,
    compute_confidence_divergence,
    compute_evidence_divergence,
    compute_operator_score,
    compute_structural_divergence,
)
from src.opmech.controller import ExploreExploitController
from src.opmech.graph_interface import KnowledgeGraphInterface
from src.opmech.operators import OperatorA, OperatorB
from src.opmech.llm_interface import LLMInterface
from src.opmech.system import OpMechGraphRAG
from src.opmech.visualization import export_trajectory_json, print_trajectory
from src.opmech.constants import (
    MARGIN_XBRL_CONCEPTS,
    QUERY_TO_XBRL_MAP,
    NUMERICAL_ASPECT_TERMS,
    FINANCIAL_TERM_MAPPINGS,
)

# Production System - Type-Safe Components
from src.opmech.type_safe_models import (
    FiscalPeriod,
    FinancialValue,
    Direction,
    Severity,
    DiscrepancyType,
    EvidenceNode,
    ComputedChange,
    Discrepancy,
    ConsistencyReport,
    OperatorOutput,
)
from src.opmech.evidence_extractor import (
    EvidenceExtractor,
    EvidenceSet,
    create_evidence_extractor,
)
from src.opmech.temporal_intelligence import (
    TemporalIntelligence,
    XBRLGroundTruth,
    create_temporal_intelligence,
)
from src.opmech.robust_consistency_checker import (
    RobustConsistencyChecker,
    ConsistencyValidator,
    check_operator_consistency,
)
from src.opmech.production_pipeline import (
    ProductionPipeline,
    ProductionEnhancedOpMech,
    create_production_pipeline,
    EnrichedEvidence,
    ValidationResult,
    FinalAnswer,
)

__all__ = [
    # Data classes
    "Node",
    "Edge",
    "TraversedNode",
    "BeliefState",
    "TraversalStrategy",
    "CommutatorResult",
    "QueryResult",
    "OutputMode",
    # Commutator
    "compute_evidence_divergence",
    "compute_structural_divergence",
    "compute_answer_divergence",
    "compute_confidence_divergence",
    "compute_commutator",
    "compute_operator_score",
    # Controller
    "ExploreExploitController",
    # Graph
    "KnowledgeGraphInterface",
    # Operators
    "OperatorA",
    "OperatorB",
    # LLM
    "LLMInterface",
    # Main system
    "OpMechGraphRAG",
    # Visualization
    "print_trajectory",
    "export_trajectory_json",
    # Constants
    "MARGIN_XBRL_CONCEPTS",
    "QUERY_TO_XBRL_MAP",
    "NUMERICAL_ASPECT_TERMS",
    "FINANCIAL_TERM_MAPPINGS",
    # ========================================
    # Production System - Type-Safe Components
    # ========================================
    # Type-safe models (prevent year/dollar confusion)
    "FiscalPeriod",
    "FinancialValue",
    "Direction",
    "Severity",
    "DiscrepancyType",
    "EvidenceNode",
    "ComputedChange",
    "Discrepancy",
    "ConsistencyReport",
    "OperatorOutput",
    # Evidence extraction
    "EvidenceExtractor",
    "EvidenceSet",
    "create_evidence_extractor",
    # Temporal intelligence
    "TemporalIntelligence",
    "XBRLGroundTruth",
    "create_temporal_intelligence",
    # Robust consistency checking
    "RobustConsistencyChecker",
    "ConsistencyValidator",
    "check_operator_consistency",
    # Production pipeline
    "ProductionPipeline",
    "ProductionEnhancedOpMech",
    "create_production_pipeline",
    "EnrichedEvidence",
    "ValidationResult",
    "FinalAnswer",
]
