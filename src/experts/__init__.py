"""Expert modules for MoE Graph Builder."""

from src.experts.base import BaseExpert, cosine_similarity, find_top_k_similar
from src.experts.causal import CausalChainBuilder
from src.experts.cross_reference import CrossReferenceHunter
from src.experts.entity_extractor import EntityExtractor
from src.experts.llm_client import LLMClient, get_llm_client
from src.experts.semantic import SemanticBridge
from src.experts.table_text import TableTextConnector
from src.experts.temporal import TemporalLinker

__all__ = [
    "BaseExpert",
    "cosine_similarity",
    "find_top_k_similar",
    "CrossReferenceHunter",
    "CausalChainBuilder",
    "TemporalLinker",
    "TableTextConnector",
    "SemanticBridge",
    "EntityExtractor",
    "LLMClient",
    "get_llm_client",
]

# Expert registry for easy instantiation
EXPERTS = {
    "cross_reference": CrossReferenceHunter,
    "causal": CausalChainBuilder,
    "temporal": TemporalLinker,
    "table_text": TableTextConnector,
    "semantic": SemanticBridge,
    "entity": EntityExtractor,
}


def get_expert(name: str, config: dict = None) -> BaseExpert:
    """Get an expert by name."""
    if name not in EXPERTS:
        raise ValueError(f"Unknown expert: {name}. Available: {list(EXPERTS.keys())}")
    return EXPERTS[name](config)


def get_all_experts(config: dict = None) -> list[BaseExpert]:
    """Get all experts."""
    return [cls(config) for cls in EXPERTS.values()]
