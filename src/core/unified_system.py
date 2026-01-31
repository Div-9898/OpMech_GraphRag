"""
Unified System - Wrapper that integrates UnifiedPipeline with OpMech-GraphRAG.

This module provides a complete replacement for the enhanced system, using
the ground-truth-first architecture from UnifiedPipeline while still leveraging
the graph traversal capabilities of the base OpMech system when needed.
"""

from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field

from loguru import logger

from src.core.unified_pipeline import (
    UnifiedPipeline,
    FinalAnswer,
    QueryType,
    AnalyzedQuery,
    GroundTruth,
)
from src.financial_models.fiscal_period import FiscalPeriod
from src.financial_models.financial_value import FinancialValue


@dataclass
class UnifiedQueryResult:
    """
    Query result from the unified system.
    Compatible with the EnhancedQueryResult interface.
    """
    # Core answer
    answer: str
    confidence: float
    mode: str
    hops_used: int = 1

    # Validation information
    validations_passed: int = 0
    validations_failed: int = 0
    corrections_applied: List[str] = field(default_factory=list)
    ground_truth_used: bool = True

    # Evidence information
    xbrl_evidence_count: int = 0
    segment_data_found: bool = True

    # Operator outputs (for compatibility)
    answer_A: str = ""
    answer_B: str = ""

    # Diagnostics
    reasoning: str = ""
    analyst_notes: str = ""
    confidence_explanation: str = ""

    # Original result for reference
    original_result: Optional[FinalAnswer] = None

    # For API compatibility - trajectory
    trajectory: List[Dict] = field(default_factory=list)

    # Operator reliability (fixed for unified pipeline)
    reliability_A: float = 0.95
    reliability_B: float = 0.95

    # Path confidence (equal for unified pipeline)
    path_confidence_A: float = 0.90
    path_confidence_B: float = 0.90


class UnifiedOpMechSystem:
    """
    Unified OpMech system that uses ground-truth-first architecture.

    This replaces the fragmented operator/synthesizer approach with:
    1. Ground truth retrieval BEFORE any LLM call
    2. Mandatory facts injection into LLM context
    3. Validation that CONFIRMS (not corrects) the answer

    The key insight: The old system had LLM generate first, then correct.
    This system retrieves ground truth first, then LLM generates WITH the facts.
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password123",
        vllm_url: str = "http://localhost:8001/v1",
        company: str = "AAPL",
        llm_func: Optional[Callable[[str], str]] = None,
        **kwargs
    ):
        """
        Initialize the unified system.

        Args:
            neo4j_uri: Neo4j connection URI (for future graph integration)
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            vllm_url: vLLM server URL
            company: Company ticker for ground truth lookup
            llm_func: Optional custom LLM function
            **kwargs: Additional arguments
        """
        logger.info("Initializing Unified OpMech System...")

        self.company = company
        self.vllm_url = vllm_url

        # Store credentials for potential graph integration
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password

        # Initialize the unified pipeline
        if llm_func is None:
            llm_func = self._create_llm_func()

        self.pipeline = UnifiedPipeline(
            llm_func=llm_func,
            company=company
        )

        logger.info("Unified OpMech System initialized")

    def _create_llm_func(self) -> Optional[Callable[[str], str]]:
        """
        Create LLM function using vLLM.
        Returns None if vLLM is not available (will use fallback).
        """
        try:
            import requests

            # First, try to get the model name from vLLM
            model_name = None
            try:
                models_response = requests.get(f"{self.vllm_url}/models", timeout=5)
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    if models_data.get("data"):
                        model_name = models_data["data"][0]["id"]
                        logger.info(f"vLLM model detected: {model_name}")
            except Exception as e:
                logger.warning(f"Could not detect vLLM model: {e}")

            if not model_name:
                logger.info("vLLM not available, using fallback generation")
                return None

            def llm_call(prompt: str) -> str:
                """Call vLLM API."""
                try:
                    response = requests.post(
                        f"{self.vllm_url}/chat/completions",
                        json={
                            "model": model_name,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 1024,
                            "temperature": 0.1,
                        },
                        timeout=60
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.warning(f"vLLM returned status {response.status_code}: {response.text[:200]}")
                        return ""
                except Exception as e:
                    logger.warning(f"vLLM call failed: {e}")
                    return ""

            logger.info(f"vLLM available at {self.vllm_url} with model {model_name}")
            return llm_call

        except ImportError:
            logger.info("requests not available, using fallback generation")
            return None

    def query(self, query: str) -> UnifiedQueryResult:
        """
        Execute query using the unified pipeline.

        The key difference from the old system:
        1. Ground truth is retrieved FIRST
        2. LLM receives mandatory facts in its context
        3. Validation confirms, doesn't correct

        Args:
            query: User query string

        Returns:
            UnifiedQueryResult with validated answer
        """
        logger.info(f"Processing unified query: {query[:50]}...")

        # Execute through unified pipeline
        result = self.pipeline.process(query)

        # Build compatible result
        validations_passed = result.facts_found
        validations_failed = result.facts_expected - result.facts_found

        # Determine mode for reasoning
        mode_reason = {
            "EXPLOIT": "High confidence answer based on verified XBRL data",
            "EXPLORE": "Multiple perspectives considered due to query complexity",
            "ADAPTIVE": "Balanced approach with verified data foundation"
        }

        reasoning = (
            f"Query analyzed as {result.mode}. "
            f"Ground truth retrieved first with {result.facts_found} verified facts. "
            f"{mode_reason.get(result.mode, '')}"
        )

        # Build trajectory for API compatibility
        trajectory = [{
            "hop": 1,
            "delta": 0.1 if result.mode == "EXPLOIT" else 0.5,
            "delta_E": 0.05,
            "delta_V": 0.05,
            "delta_A": 0.05,
            "delta_C": 0.05,
            "nodesA": result.facts_found,
            "nodesB": result.facts_found,
            "bridgeSeeds": 0
        }]

        # Confidence explanation
        confidence_explanation = (
            f"Confidence: {result.confidence:.1%} based on "
            f"{result.facts_found}/{result.facts_expected} facts verified against XBRL. "
            f"All facts {'included' if result.all_facts_included else 'partially included'} in answer."
        )

        return UnifiedQueryResult(
            answer=result.answer_text,
            confidence=result.confidence,
            mode=result.mode,
            hops_used=1,
            validations_passed=validations_passed,
            validations_failed=max(0, validations_failed),
            corrections_applied=[],  # No corrections - ground truth is injected first
            ground_truth_used=result.ground_truth_used is not None and result.ground_truth_used.has_data,
            xbrl_evidence_count=result.facts_found,
            segment_data_found=result.facts_expected == result.facts_found,
            answer_A=result.answer_text,  # Same answer for both operators
            answer_B=result.answer_text,
            reasoning=reasoning,
            analyst_notes=result.mandatory_facts if result.mandatory_facts else "No analyst notes",
            confidence_explanation=confidence_explanation,
            original_result=result,
            trajectory=trajectory,
            reliability_A=0.95,
            reliability_B=0.95,
            path_confidence_A=result.confidence,
            path_confidence_B=result.confidence,
        )

    def get_segment_data(self, segment: str) -> Dict[str, Any]:
        """
        Get detailed segment data directly from ground truth.
        """
        from src.data.apple_ground_truth import AppleFinancialLookup, APPLE_FINANCIALS

        segment_map = {
            'iphone': 'iphone_revenue',
            'services': 'services_revenue',
            'mac': 'mac_revenue',
            'ipad': 'ipad_revenue',
            'wearables': 'wearables_revenue',
        }

        metric = segment_map.get(segment.lower(), 'net_sales')

        if metric not in APPLE_FINANCIALS:
            return {'segment': segment, 'error': f'No data for segment: {segment}'}

        values = {}
        for period_label, amount in APPLE_FINANCIALS[metric].items():
            period = FiscalPeriod.from_string(period_label, self.company)
            if period:
                value = AppleFinancialLookup.get_value(metric, period)
                if value:
                    values[period_label] = value.format()

        # Compute changes
        changes = []
        periods = list(APPLE_FINANCIALS[metric].keys())
        for i in range(len(periods) - 1):
            from_period = FiscalPeriod.from_string(periods[i], self.company)
            to_period = FiscalPeriod.from_string(periods[i + 1], self.company)
            if from_period and to_period:
                change = AppleFinancialLookup.get_change(metric, from_period, to_period)
                if change:
                    changes.append(change.format_concise())

        return {
            'segment': segment,
            'metric': metric,
            'values': values,
            'changes': changes,
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
        from src.data.apple_ground_truth import AppleFinancialLookup

        period_obj = FiscalPeriod.from_string(period, self.company)
        if not period_obj:
            return {'valid': False, 'error': f'Invalid period: {period}'}

        value_obj = FinancialValue.parse(claimed_value)
        if not value_obj:
            return {'valid': False, 'error': f'Invalid value: {claimed_value}'}

        is_valid, ground_truth, message = AppleFinancialLookup.validate_claim(
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
        logger.info("Unified OpMech System closed")


# Convenience function
def create_unified_system(**kwargs) -> UnifiedOpMechSystem:
    """
    Create a unified OpMech system.
    """
    return UnifiedOpMechSystem(**kwargs)
