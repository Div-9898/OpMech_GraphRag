"""LLM Interface for OpMech-GraphRAG.

Provides interface to Qwen2.5-7B via vLLM for answer generation.
Includes trust-aware prompts for mode selection.

ENHANCED: Now includes evidence preprocessing for temporal accuracy
and answer validation to catch direction errors.
"""

from typing import List, Any, Dict, TYPE_CHECKING

from loguru import logger
from openai import OpenAI

from src.opmech.data_classes import Node
from src.opmech.evidence_preprocessor import EvidencePreprocessor, create_evidence_preprocessor
from src.opmech.prompts import get_operator_prompt, get_merge_prompt
from src.opmech.answer_validator import validate_and_adjust_answer

if TYPE_CHECKING:
    from src.opmech.data_classes import BeliefState
    from src.opmech.mode_selection import ModeDecision


class LLMInterface:
    """Interface to Qwen2.5-7B via vLLM."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        company: str = "apple"
    ):
        """
        Initialize the LLM interface.

        Args:
            base_url: vLLM server URL
            model: Model name/path
            company: Company name for fiscal year mapping (affects evidence preprocessing)
        """
        self.client = OpenAI(base_url=base_url, api_key="not-needed")
        self.model = model
        self.evidence_preprocessor = create_evidence_preprocessor(company)

    def is_available(self) -> bool:
        """Check if vLLM server is available."""
        try:
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            logger.warning(f"vLLM server not available: {e}")
            return False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.1
    ) -> str:
        """
        Simple text generation for classification and other utility tasks.

        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text string
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Simple generation failed: {e}")
            return ""

    def generate_answer(
        self,
        query: str,
        evidence: List[Node],
        operator_path: str,
        query_type: str = "general"
    ) -> str:
        """
        Generate answer from evidence with temporal accuracy preprocessing.

        Args:
            query: User query
            evidence: List of evidence nodes
            operator_path: "structure_first" or "narrative_first"
            query_type: Query type for prompt selection (numerical, causal, opinion, etc.)

        Returns:
            Generated answer string
        """
        # Convert evidence nodes to dicts for preprocessing
        # Limit to 5 nodes to prevent context overflow with 4096 token models
        evidence_dicts = [self._node_to_dict(n) for n in evidence[:5]]

        # Preprocess evidence to add fiscal year labels and compute changes
        enriched_evidence = self.evidence_preprocessor.preprocess(evidence_dicts)

        # Format evidence with temporal context for LLM
        evidence_text = self.evidence_preprocessor.format_for_llm(enriched_evidence)

        # Get temporal summary
        temporal_summary = self.evidence_preprocessor.get_temporal_summary(enriched_evidence)

        if not evidence_text:
            evidence_text = "(No evidence found)"

        # Use enhanced prompt with temporal verification instructions
        prompt = get_operator_prompt(
            query_type=query_type,
            evidence=evidence_text,
            query=query,
            temporal_summary=temporal_summary
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3
            )
            raw_answer = response.choices[0].message.content

            # Validate answer for temporal consistency
            validated_answer, adjusted_confidence, issues = validate_and_adjust_answer(
                raw_answer,
                enriched_evidence,
                query,
                original_confidence=0.8
            )

            if issues:
                logger.warning(f"Answer validation issues for {operator_path}: {issues[:2]}")

            return validated_answer
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"[Error generating answer: {e}]"

    def _node_to_dict(self, node: Node) -> Dict:
        """Convert Node to dict for evidence preprocessing."""
        return {
            'type': node.type,
            'content': node.text,
            'text': node.text,
            'xbrl_tag': node.metadata.get('xbrl_tag'),
            'value': node.metadata.get('value'),
            'period_end': node.metadata.get('period_end'),
            'period': node.metadata.get('period'),
            'metadata': node.metadata
        }

    def generate_merged_answer(
        self,
        query: str,
        answer_A: str,
        answer_B: str,
        evidence_A: List[Node],
        evidence_B: List[Node],
        reliability_A: float = 0.5,
        reliability_B: float = 0.5
    ) -> str:
        """
        Generate merged answer from both perspectives with consistency checking.

        Args:
            query: User query
            answer_A: Answer from structure-first operator
            answer_B: Answer from narrative-first operator
            evidence_A: Evidence from operator A
            evidence_B: Evidence from operator B
            reliability_A: Reliability score for operator A
            reliability_B: Reliability score for operator B

        Returns:
            Merged answer string
        """
        # Use enhanced merge prompt with fact-checking instructions
        prompt = get_merge_prompt(
            mode="explore",
            answer_A=answer_A,
            answer_B=answer_B,
            query=query,
            reliability_A=reliability_A,
            reliability_B=reliability_B
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM merged generation failed: {e}")
            return f"[Error generating merged answer: {e}]"

    def generate_dual_hypothesis(
        self,
        query: str,
        answer_A: str,
        answer_B: str,
        divergence: float
    ) -> str:
        """
        Generate dual hypothesis answer when divergence is high.

        Args:
            query: User query
            answer_A: Answer from structure-first operator
            answer_B: Answer from narrative-first operator
            divergence: Divergence score

        Returns:
            Dual hypothesis answer string
        """
        return f"""ANALYSIS SHOWS STRUCTURAL AMBIGUITY (Divergence: {divergence:.2f})

The evidence supports two distinct interpretations:

{'='*70}
HYPOTHESIS A - Quantitative View (Structure-First):
{'='*70}
{answer_A}

{'='*70}
HYPOTHESIS B - Qualitative View (Narrative-First):
{'='*70}
{answer_B}

{'='*70}
RECOMMENDATION:
{'='*70}
This question exhibits irreducible ambiguity in Apple's SEC filings.
The quantitative and qualitative evidence lead to different conclusions.
Consider both perspectives when making decisions."""

    def _format_evidence(self, evidence: List[Node], max_items: int = 10) -> str:
        """Format evidence nodes for prompts."""
        if not evidence:
            return "(No evidence found)"

        return "\n\n".join([
            f"[{n.type}] {n.metadata.get('section', 'N/A')} ({n.metadata.get('period', 'N/A')}):\n{n.text[:500]}"
            for n in evidence[:max_items]
        ])

    def generate_trusted_answer(
        self,
        query: str,
        primary_evidence: List[Node],
        secondary_evidence: List[Node],
        primary: str,
        source_type: str,
        confidence: float
    ) -> str:
        """
        Generate answer trusting one operator primarily.

        Args:
            query: User query
            primary_evidence: Evidence from trusted operator
            secondary_evidence: Evidence from secondary operator (for context)
            primary: "A" or "B" indicating which operator is trusted
            source_type: Description of source type (e.g., "financial/XBRL data")
            confidence: Confidence level (0-1)

        Returns:
            Generated answer string
        """
        primary_desc = "XBRL-tagged financial statements (audited, authoritative)" if primary == "A" else "narrative sections (MD&A, notes)"

        prompt = f"""Answer this question based primarily on the authoritative evidence.

Question: {query}

PRIMARY EVIDENCE (from {source_type}):
{self._format_evidence(primary_evidence)}

SECONDARY EVIDENCE (for context only - may contain figures from different periods):
{self._format_evidence(secondary_evidence, max_items=5)}

INSTRUCTIONS:
1. Base your answer primarily on the PRIMARY EVIDENCE
2. The primary evidence comes from {primary_desc}
3. If secondary evidence shows different figures, note this as a potential difference in reporting period or context
4. Provide a clear, direct answer
5. Do NOT say "approximately" or "around" - give the exact figure if available from primary evidence
6. Confidence level: {confidence:.0%}

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM trusted answer generation failed: {e}")
            return f"[Error generating trusted answer: {e}]"

    def generate_exploit_answer(
        self,
        query: str,
        evidence: List[Node],
        source_type: str,
        confidence: float
    ) -> str:
        """
        Generate direct, confident answer for EXPLOIT mode when operators agree.

        Args:
            query: User query
            evidence: Combined evidence from both operators
            source_type: Description of source type
            confidence: Confidence level (0-1)

        Returns:
            Generated answer string
        """
        prompt = f"""Answer this question directly and confidently.

Question: {query}

Evidence (from {source_type}):
{self._format_evidence(evidence)}

INSTRUCTIONS:
1. Give a direct, clear answer
2. Do NOT hedge or present alternatives
3. Do NOT say "approximately" or "around" - give the exact figure if available
4. Be concise
5. Confidence: {confidence:.0%}

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM exploit answer generation failed: {e}")
            return f"[Error generating exploit answer: {e}]"

    def generate_adaptive_answer(
        self,
        query: str,
        belief_A: "BeliefState",
        belief_B: "BeliefState",
        mode_decision: "ModeDecision",
    ) -> str:
        """
        Generate balanced answer with nuance for ADAPTIVE mode.

        Args:
            query: User query
            belief_A: BeliefState from operator A
            belief_B: BeliefState from operator B
            mode_decision: The mode decision with reliability scores

        Returns:
            Generated answer string
        """
        # Determine which to emphasize
        if mode_decision.operator_A_reliability.reliability_score > mode_decision.operator_B_reliability.reliability_score:
            primary_evidence = belief_A.evidence
            secondary_evidence = belief_B.evidence
            primary_source = "financial data"
            secondary_source = "narrative context"
        else:
            primary_evidence = belief_B.evidence
            secondary_evidence = belief_A.evidence
            primary_source = "narrative analysis"
            secondary_source = "financial data"

        prompt = f"""Answer this question with appropriate nuance.

Question: {query}

Primary Evidence ({primary_source}):
{self._format_evidence(primary_evidence)}

Additional Context ({secondary_source}):
{self._format_evidence(secondary_evidence, max_items=5)}

INSTRUCTIONS:
1. Provide the main answer based on primary evidence
2. Add relevant context or nuance from additional evidence
3. If there are different figures, explain possible reasons (different periods, methodologies)
4. Be informative but not overly hedged
5. Confidence: {mode_decision.confidence:.0%}

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM adaptive answer generation failed: {e}")
            return f"[Error generating adaptive answer: {e}]"

    def generate_explore_answer(
        self,
        query: str,
        belief_A: "BeliefState",
        belief_B: "BeliefState",
        mode_decision: "ModeDecision",
        discrepancy_note: str = ""
    ) -> str:
        """
        Generate multi-perspective answer for EXPLORE mode with consistency checking.

        Args:
            query: User query
            belief_A: BeliefState from operator A
            belief_B: BeliefState from operator B
            mode_decision: The mode decision with reliability scores
            discrepancy_note: Optional note about factual discrepancies between operators

        Returns:
            Generated answer string
        """
        # Get reliability scores
        reliability_A = mode_decision.operator_A_reliability.reliability_score
        reliability_B = mode_decision.operator_B_reliability.reliability_score

        # Use enhanced merge prompt that includes fact-checking
        prompt = get_merge_prompt(
            mode="explore",
            answer_A=belief_A.answer,
            answer_B=belief_B.answer,
            query=query,
            reliability_A=reliability_A,
            reliability_B=reliability_B
        )

        # Add confidence instruction
        prompt += f"\n\nConfidence: {mode_decision.confidence:.0%} (lower confidence is appropriate here)"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.4
            )
            answer = response.choices[0].message.content

            # Append discrepancy note if provided
            if discrepancy_note:
                answer += discrepancy_note

            return answer
        except Exception as e:
            logger.error(f"LLM explore answer generation failed: {e}")
            return f"[Error generating explore answer: {e}]"
