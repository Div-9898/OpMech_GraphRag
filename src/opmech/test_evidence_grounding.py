"""
Evidence Grounding Diagnostic Tests for 7B Models

For 7B models like Qwen 2.5 7B, the primary risk is HALLUCINATION, not memorization.
These tests verify that answers are properly grounded in evidence.

Key insight: If a 7B model produces correct specific figures (like $383.29B),
those figures almost certainly came from the evidence, not training data.

Usage:
    python -m src.opmech.test_evidence_grounding
"""

import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class GroundingResult:
    """Result of evidence grounding check."""
    aligned_figures: List[str]
    unaligned_figures: List[str]
    alignment_score: float
    potential_hallucinations: List[str]
    is_grounded: bool
    details: str


def extract_numbers_from_text(text: str) -> Set[str]:
    """
    Extract financial numbers from text.

    Handles formats like:
    - $383.29B
    - 383.29 billion
    - $383,285,000,000
    - 42.3%
    """
    patterns = [
        r'\$?[\d,]+\.?\d*\s*[BMK](?:illion)?',  # $383.29B, 383 billion
        r'\$[\d,]+(?:\.\d+)?',                    # $383,285,000
        r'[\d,]+(?:\.\d+)?\s*(?:billion|million|thousand)',  # 383.29 billion
        r'\d+(?:\.\d+)?%',                        # 42.3%
    ]

    numbers = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Normalize the number
            normalized = match.replace(',', '').replace('$', '').strip().lower()
            numbers.add(normalized)
            numbers.add(match)  # Also keep original

    return numbers


def normalize_number(num_str: str) -> float:
    """
    Normalize a number string to a float for comparison.

    Handles:
    - 383.29B -> 383.29
    - 383 billion -> 383
    - $383,285,000,000 -> 383.285 (in billions)
    """
    num_str = num_str.replace(',', '').replace('$', '').strip().lower()

    # Handle billions/millions suffix
    if 'billion' in num_str or num_str.endswith('b'):
        num_str = re.sub(r'[^\d.]', '', num_str)
        try:
            return float(num_str)
        except:
            return 0.0

    if 'million' in num_str or num_str.endswith('m'):
        num_str = re.sub(r'[^\d.]', '', num_str)
        try:
            return float(num_str) / 1000  # Convert to billions
        except:
            return 0.0

    # Handle raw large numbers
    num_str = re.sub(r'[^\d.]', '', num_str)
    try:
        val = float(num_str)
        # If very large, convert to billions
        if val > 1e9:
            return val / 1e9
        elif val > 1e6:
            return val / 1e9  # Assume it's in full form
        return val
    except:
        return 0.0


def check_evidence_answer_alignment(
    answer: str,
    evidence_A: List,
    evidence_B: List,
    tolerance: float = 0.01
) -> GroundingResult:
    """
    Check if specific numbers in the answer exist in the evidence.

    For 7B models: verify answer figures come from evidence.
    7B models have limited memorization, so if they produce
    specific figures, those figures came from the context.

    Args:
        answer: The generated answer
        evidence_A: Evidence nodes from Operator A
        evidence_B: Evidence nodes from Operator B
        tolerance: Tolerance for number matching (default 1%)

    Returns:
        GroundingResult with alignment details
    """
    # Extract numbers from evidence
    evidence_numbers = set()
    evidence_text = ""
    for node in evidence_A + evidence_B:
        content = node.content if hasattr(node, 'content') else str(node)
        evidence_text += " " + content
        numbers = extract_numbers_from_text(content)
        evidence_numbers.update(numbers)

    # Extract numbers from answer
    answer_numbers = extract_numbers_from_text(answer)

    # Check alignment
    aligned = []
    unaligned = []

    for num in answer_numbers:
        # Direct match
        if num in evidence_numbers:
            aligned.append(num)
            continue

        # Normalized comparison
        num_val = normalize_number(num)
        if num_val == 0:
            continue

        found = False
        for ev_num in evidence_numbers:
            ev_val = normalize_number(ev_num)
            if ev_val == 0:
                continue

            # Check if within tolerance
            if abs(num_val - ev_val) < tolerance * max(num_val, ev_val):
                aligned.append(f"{num} (matches {ev_num})")
                found = True
                break

        if not found:
            unaligned.append(num)

    # Calculate score
    total = len(aligned) + len(unaligned)
    alignment_score = len(aligned) / total if total > 0 else 1.0

    # Determine if grounded
    is_grounded = alignment_score >= 0.8 and len(unaligned) == 0

    details = f"Aligned: {aligned}, Unaligned: {unaligned}"

    return GroundingResult(
        aligned_figures=aligned,
        unaligned_figures=unaligned,
        alignment_score=alignment_score,
        potential_hallucinations=unaligned,  # Unaligned figures are potential hallucinations
        is_grounded=is_grounded,
        details=details
    )


def detect_hallucinations(
    answer: str,
    evidence_A: List,
    evidence_B: List
) -> List[str]:
    """
    Detect potential hallucinations in the answer.

    7B models may hallucinate plausible-sounding but incorrect details.
    Check for common hallucination patterns.

    Args:
        answer: The generated answer
        evidence_A: Evidence nodes from Operator A
        evidence_B: Evidence nodes from Operator B

    Returns:
        List of potential hallucination strings
    """
    evidence_text = ""
    for node in evidence_A + evidence_B:
        content = node.content if hasattr(node, 'content') else str(node)
        evidence_text += " " + content

    # Known hallucination patterns for financial queries
    hallucination_signals = [
        # Overly precise numbers not in evidence
        (r'\$\d{3}\.\d{3}B', "Overly precise dollar amount"),

        # Round numbers that look made up
        (r'\$\d00\s*billion', "Suspiciously round number"),

        # Unsupported comparisons
        (r'(increased|decreased|grew|declined)\s+by\s+\d+\.?\d*%', "Percentage change"),

        # Specific dates/quarters not in evidence
        (r'Q[1-4]\s+\d{4}', "Specific quarter reference"),

        # Year-over-year claims
        (r'year.over.year\s+\w+\s+of\s+\d+', "YoY claim"),
    ]

    potential_hallucinations = []

    for pattern, description in hallucination_signals:
        matches = re.findall(pattern, answer, re.IGNORECASE)
        for match in matches:
            # Check if this appears in evidence
            if match.lower() not in evidence_text.lower():
                potential_hallucinations.append(f"{match} ({description})")

    return potential_hallucinations


def run_7b_diagnostic(system, query: str = "What was Apple's total revenue in FY2023?"):
    """
    Quick diagnostic for 7B model grounding.

    Runs a query and checks if the answer is properly grounded in evidence.

    Args:
        system: OpMechGraphRAG system instance
        query: Query to test

    Returns:
        Dict with diagnostic results
    """
    logger.info("=" * 60)
    logger.info("7B MODEL GROUNDING DIAGNOSTIC")
    logger.info("=" * 60)

    result = system.query(query)

    logger.info(f"\nQuery: {query}")
    logger.info(f"Answer: {result.answer[:300]}...")
    logger.info(f"\nMode: {result.mode}, Confidence: {result.confidence:.0%}")

    # Check grounding
    grounding = check_evidence_answer_alignment(
        result.answer,
        result.evidence_A,
        result.evidence_B
    )

    logger.info(f"\nAlignment Score: {grounding.alignment_score:.0%}")
    logger.info(f"Aligned figures: {grounding.aligned_figures}")

    if grounding.unaligned_figures:
        logger.warning(f"Unaligned figures (potential issues): {grounding.unaligned_figures}")
    else:
        logger.info("✅ All figures found in evidence")

    # Check for hallucinations
    hallucinations = detect_hallucinations(
        result.answer,
        result.evidence_A,
        result.evidence_B
    )

    if hallucinations:
        logger.warning(f"⚠️ Potential hallucinations detected:")
        for h in hallucinations:
            logger.warning(f"   - {h}")
    else:
        logger.info("✅ No obvious hallucinations detected")

    # Show evidence sample
    logger.info("\n" + "-" * 40)
    logger.info("Evidence Sample (first 3 nodes from each operator):")
    logger.info("-" * 40)

    for i, node in enumerate(result.evidence_A[:3]):
        content = node.content if hasattr(node, 'content') else str(node)
        node_type = node.type if hasattr(node, 'type') else "UNKNOWN"
        logger.info(f"[A-{i+1}] {node_type}: {content[:100]}...")

    for i, node in enumerate(result.evidence_B[:3]):
        content = node.content if hasattr(node, 'content') else str(node)
        node_type = node.type if hasattr(node, 'type') else "UNKNOWN"
        logger.info(f"[B-{i+1}] {node_type}: {content[:100]}...")

    logger.info("=" * 60)

    return {
        "query": query,
        "answer": result.answer,
        "mode": result.mode,
        "confidence": result.confidence,
        "grounding": grounding,
        "hallucinations": hallucinations,
        "is_grounded": grounding.is_grounded and len(hallucinations) == 0
    }


def test_evidence_answer_alignment_batch(system, test_queries: List[str] = None):
    """
    Test evidence-answer alignment for multiple queries.

    Args:
        system: OpMechGraphRAG system instance
        test_queries: List of queries to test

    Returns:
        Dict with batch results
    """
    if test_queries is None:
        test_queries = [
            "What was Apple's total revenue in FY2023?",
            "What was Apple's R&D expense in FY2023?",
            "What was Apple's net income in FY2023?",
            "What was Apple's gross margin in FY2023?",
        ]

    results = []
    total_grounded = 0

    for query in test_queries:
        logger.info(f"\nTesting: {query[:50]}...")

        result = system.query(query)

        grounding = check_evidence_answer_alignment(
            result.answer,
            result.evidence_A,
            result.evidence_B
        )

        logger.info(f"  Evidence numbers: {len(grounding.aligned_figures) + len(grounding.unaligned_figures)} figures")
        logger.info(f"  ✅ Aligned with evidence: {grounding.aligned_figures}")

        if grounding.unaligned_figures:
            logger.warning(f"  ⚠️ Not found in evidence: {grounding.unaligned_figures}")
            logger.warning(f"     (Could be: inference, rounding, or hallucination)")

        logger.info(f"  Alignment score: {grounding.alignment_score:.0%}")

        if grounding.is_grounded:
            total_grounded += 1

        results.append({
            "query": query,
            "grounding": grounding,
            "is_grounded": grounding.is_grounded
        })

    logger.info(f"\n{'=' * 60}")
    logger.info(f"BATCH RESULTS: {total_grounded}/{len(test_queries)} queries properly grounded")
    logger.info(f"{'=' * 60}")

    return {
        "results": results,
        "total_queries": len(test_queries),
        "grounded_queries": total_grounded,
        "grounding_rate": total_grounded / len(test_queries) if test_queries else 0
    }


if __name__ == "__main__":
    # This can be run standalone for testing
    logger.info("Evidence Grounding Diagnostic Tests")
    logger.info("Run with an OpMechGraphRAG instance for full testing")

    # Example usage:
    # from src.opmech.system import OpMechGraphRAG
    # system = OpMechGraphRAG(...)
    # run_7b_diagnostic(system)
