"""vLLM client for LLM-based extraction tasks."""

import json
from typing import Any

from loguru import logger
from openai import OpenAI

from src.config import settings


class LLMClient:
    """Client for interacting with vLLM server."""

    def __init__(
        self,
        api_base: str = None,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ):
        self.api_base = api_base or settings.vllm_api_base
        self.model = model or settings.vllm_model
        self.max_tokens = max_tokens or settings.vllm_max_tokens
        self.temperature = temperature or settings.vllm_temperature

        self.client = OpenAI(
            api_key="EMPTY",  # vLLM doesn't require a real key
            base_url=self.api_base,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def extract_causal_relations(
        self,
        text: str,
        max_relations: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Extract causal relations from text using LLM.

        Args:
            text: Input text to analyze
            max_relations: Maximum number of relations to extract

        Returns:
            List of causal relations with cause, effect, and confidence
        """
        system_prompt = """You are an expert at extracting causal relationships from financial text.
Your task is to identify cause-effect relationships in SEC filings.

For each causal relationship found, output a JSON object with:
- "cause": The cause/driver (brief phrase)
- "effect": The effect/result (brief phrase)
- "evidence": The exact quote from the text showing the relationship
- "confidence": Your confidence score (0.0 to 1.0)
- "direction": Either "forward" (cause leads to effect) or "backward" (effect caused by cause)

Output a JSON array of relationships. If no causal relationships are found, output an empty array [].
Only extract explicit causal relationships, not correlations or coincidences."""

        prompt = f"""Extract causal relationships from this financial text:

---
{text[:2000]}
---

Output up to {max_relations} causal relationships as a JSON array:"""

        try:
            response = self.generate(prompt, system_prompt=system_prompt)

            # Parse JSON from response
            # Try to find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                relations = json.loads(json_str)
                return relations
            else:
                logger.warning(f"No JSON array found in LLM response: {response[:200]}")
                return []

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Causal extraction failed: {e}")
            return []

    def extract_entities(
        self,
        text: str,
        entity_types: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Extract named entities from text using LLM.

        Args:
            text: Input text
            entity_types: Types of entities to extract

        Returns:
            List of entities with name, type, and context
        """
        if entity_types is None:
            entity_types = ["COMPANY", "PRODUCT", "SEGMENT", "PERSON", "LOCATION"]

        system_prompt = f"""You are an expert at extracting named entities from financial text.
Extract entities of these types: {', '.join(entity_types)}

For each entity, output a JSON object with:
- "name": The entity name
- "type": The entity type (one of {entity_types})
- "context": Brief context about the entity from the text

Output a JSON array of entities. If no entities are found, output an empty array []."""

        prompt = f"""Extract named entities from this financial text:

---
{text[:2000]}
---

Output entities as a JSON array:"""

        try:
            response = self.generate(prompt, system_prompt=system_prompt)

            start = response.find("[")
            end = response.rfind("]") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                entities = json.loads(json_str)
                return entities
            else:
                return []

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def extract_cross_references(
        self,
        text: str,
        max_references: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Extract cross-references from text using LLM.

        Args:
            text: Input text to analyze
            max_references: Maximum number of references to extract

        Returns:
            List of references with source_context, target_type, target_id, and confidence
        """
        system_prompt = """You are an expert at identifying cross-references in SEC filings.
Your task is to find explicit references to other parts of the document.

Look for references like:
- "See Note 3" or "refer to Note X"
- "as discussed in Item 7" or "described in Item 1A"
- "see Part II, Item 8"
- "the following table shows" or "see the table below"
- "as described in the Risk Factors section"

For each reference found, output a JSON object with:
- "source_text": The text containing the reference (brief quote)
- "target_type": One of "note", "item", "part", "table", "section"
- "target_id": The specific target (e.g., "3" for Note 3, "7" for Item 7, "Risk Factors")
- "confidence": Your confidence score (0.0 to 1.0)

Output a JSON array. If no references found, output []."""

        prompt = f"""Extract cross-references from this SEC filing text:

---
{text[:2500]}
---

Output up to {max_references} cross-references as a JSON array:"""

        try:
            response = self.generate(prompt, system_prompt=system_prompt)
            return self._parse_json_array(response)
        except Exception as e:
            logger.error(f"Cross-reference extraction failed: {e}")
            return []

    def extract_temporal_links(
        self,
        text1: str,
        text2: str,
        period1: str,
        period2: str,
    ) -> dict[str, Any]:
        """
        Determine if two text sections discuss the same topic across time periods.

        Args:
            text1: Text from first period
            text2: Text from second period
            period1: First period (e.g., "FY2023")
            period2: Second period (e.g., "FY2024")

        Returns:
            Dict with is_related, confidence, and reason
        """
        system_prompt = """You are an expert at analyzing SEC filings across time periods.
Your task is to determine if two text sections discuss the same financial topic or metric.

Consider:
- Same financial metric (revenue, expenses, margins)
- Same business segment
- Same geographic region
- Same accounting treatment or disclosure

Output a JSON object with:
- "is_related": true or false
- "confidence": Your confidence (0.0 to 1.0)
- "reason": Brief explanation of why they are or aren't related
- "topic": The common topic if related (e.g., "iPhone revenue", "Services segment")"""

        prompt = f"""Compare these two SEC filing excerpts from different periods:

PERIOD 1 ({period1}):
{text1[:1000]}

PERIOD 2 ({period2}):
{text2[:1000]}

Are these discussing the same financial topic? Output as JSON:"""

        try:
            response = self.generate(prompt, system_prompt=system_prompt)
            return self._parse_json_object(response)
        except Exception as e:
            logger.error(f"Temporal link extraction failed: {e}")
            return {"is_related": False, "confidence": 0.0, "reason": str(e)}

    def extract_table_text_connections(
        self,
        table_text: str,
        narrative_text: str,
        max_connections: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find connections between table data and explanatory narrative text.

        Args:
            table_text: Text representation of table data
            narrative_text: Narrative text that might explain the table
            max_connections: Maximum connections to find

        Returns:
            List of connections with table_item, explanation, and confidence
        """
        system_prompt = """You are an expert at connecting financial tables to their explanatory text.
Your task is to find which parts of the narrative text explain specific table items.

Look for:
- Specific numbers mentioned in both
- Financial metrics discussed
- Trends or changes explained
- Segment or product details

For each connection found, output a JSON object with:
- "table_item": The specific table item being explained (e.g., "Total Revenue: $383B")
- "explanation": The narrative text that explains it
- "connection_type": One of "numeric_match", "metric_discussion", "trend_explanation"
- "confidence": Your confidence (0.0 to 1.0)

Output a JSON array. If no connections found, output []."""

        prompt = f"""Find connections between this table and narrative text:

TABLE DATA:
{table_text[:1500]}

NARRATIVE TEXT:
{narrative_text[:1500]}

Output connections as a JSON array:"""

        try:
            response = self.generate(prompt, system_prompt=system_prompt)
            return self._parse_json_array(response)
        except Exception as e:
            logger.error(f"Table-text connection extraction failed: {e}")
            return []

    def extract_semantic_relationships(
        self,
        text1: str,
        text2: str,
    ) -> dict[str, Any]:
        """
        Analyze semantic relationship between two text sections.

        Args:
            text1: First text section
            text2: Second text section

        Returns:
            Dict with relationship_type, similarity_score, and explanation
        """
        system_prompt = """You are an expert at analyzing semantic relationships in financial documents.
Your task is to determine how two text sections are related.

Consider relationships like:
- Same topic (discussing the same subject)
- Cause-effect (one explains/causes the other)
- Detail-summary (one provides details for the other)
- Contrast (comparing or contrasting)
- Unrelated

Output a JSON object with:
- "relationship_type": One of "same_topic", "cause_effect", "detail_summary", "contrast", "unrelated"
- "similarity_score": 0.0 to 1.0
- "explanation": Brief explanation of the relationship
- "key_terms": List of common key terms"""

        prompt = f"""Analyze the semantic relationship between these two text sections:

TEXT 1:
{text1[:1000]}

TEXT 2:
{text2[:1000]}

Output the relationship analysis as JSON:"""

        try:
            response = self.generate(prompt, system_prompt=system_prompt)
            return self._parse_json_object(response)
        except Exception as e:
            logger.error(f"Semantic relationship extraction failed: {e}")
            return {"relationship_type": "unrelated", "similarity_score": 0.0, "explanation": str(e)}

    def _parse_json_array(self, response: str) -> list[dict]:
        """Parse JSON array from LLM response."""
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
            return []
        except json.JSONDecodeError:
            return []

    def _parse_json_object(self, response: str) -> dict:
        """Parse JSON object from LLM response."""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
            return {}
        except json.JSONDecodeError:
            return {}

    def is_available(self) -> bool:
        """Check if the vLLM server is available."""
        try:
            # Try to list models
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False


# Global client instance (lazy loaded)
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


# vLLM server startup script content
VLLM_STARTUP_SCRIPT = """#!/bin/bash
# Start vLLM server with Qwen2.5-7B-Instruct or Mistral-7B

MODEL="${1:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${2:-8000}"

echo "Starting vLLM server with model: $MODEL"
echo "Port: $PORT"

python -m vllm.entrypoints.openai.api_server \\
    --model "$MODEL" \\
    --port "$PORT" \\
    --tensor-parallel-size 1 \\
    --gpu-memory-utilization 0.9 \\
    --max-model-len 4096 \\
    --trust-remote-code

# Alternative models:
# - Qwen/Qwen2.5-7B-Instruct (recommended)
# - mistralai/Mistral-7B-Instruct-v0.3
"""


def create_vllm_startup_script(output_path: str = "scripts/start_vllm.sh") -> None:
    """Create the vLLM startup script."""
    from pathlib import Path
    script_path = Path(output_path)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(VLLM_STARTUP_SCRIPT)
    script_path.chmod(0o755)
    logger.info(f"Created vLLM startup script: {script_path}")


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Create startup script
    create_vllm_startup_script()

    # Test client (if server is running)
    client = LLMClient()

    if client.is_available():
        logger.info("vLLM server is available")

        # Test causal extraction
        test_text = """
        Apple's revenue increased by 8% in fiscal 2024, primarily driven by strong iPhone sales
        in emerging markets. The growth in Services revenue was also a significant contributor,
        resulting from higher subscription rates. However, Mac sales declined due to the ongoing
        PC market weakness, which led to lower gross margins in that segment.
        """

        relations = client.extract_causal_relations(test_text)
        logger.info(f"Extracted {len(relations)} causal relations:")
        for rel in relations:
            logger.info(f"  {rel}")
    else:
        logger.warning("vLLM server is not available")
        logger.info("Start the server with: ./scripts/start_vllm.sh")
