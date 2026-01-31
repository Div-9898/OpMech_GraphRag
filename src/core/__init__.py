"""
Core module - Unified pipeline architecture.
This replaces the fragmented operator/synthesizer approach.

The key architectural change:
- OLD: LLM generates answer -> Ground truth validates/corrects AFTER
- NEW: Ground truth retrieved FIRST -> Injected as mandatory facts -> LLM generates WITH the facts
"""

from src.core.unified_pipeline import (
    UnifiedPipeline,
    answer_query,
    QueryType,
    AnalyzedQuery,
    GroundTruth,
    MandatoryFacts,
    FinalAnswer,
)

from src.core.unified_system import (
    UnifiedOpMechSystem,
    UnifiedQueryResult,
    create_unified_system,
)

__all__ = [
    # Pipeline components
    'UnifiedPipeline',
    'answer_query',
    'QueryType',
    'AnalyzedQuery',
    'GroundTruth',
    'MandatoryFacts',
    'FinalAnswer',
    # System integration
    'UnifiedOpMechSystem',
    'UnifiedQueryResult',
    'create_unified_system',
]
