#!/usr/bin/env python3
"""
Live test for hop termination fixes with real vLLM and Neo4j.
"""

import sys
sys.path.insert(0, '/home/divyansh/AIF_FInal_Project')

from loguru import logger
from src.opmech.system import OpMechGraphRAG

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<level>{time:HH:mm:ss}</level> | <level>{level: <8}</level> | {message}")


def run_live_test():
    """Test hop termination with real queries."""

    logger.info("=" * 70)
    logger.info("LIVE HOP TERMINATION TEST")
    logger.info("=" * 70)

    # Initialize system
    logger.info("Initializing OpMech-GraphRAG system...")
    system = OpMechGraphRAG(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        vllm_url="http://localhost:8000/v1",
        tau_low=0.25,
        tau_high=0.60,
        max_hops=4
    )

    # Test cases
    test_cases = [
        {
            "query": "What was Apple's total revenue in FY2023?",
            "expected_type": "numerical",
            "min_hops": 2,
            "max_hops": 3,
        },
        {
            "query": "Is Apple's gross margin pressure cyclical or structural?",
            "expected_type": "opinion",
            "min_hops": 3,  # Opinion queries must do at least 3 hops
            "max_hops": 5,
        },
        {
            "query": "What factors drove iPhone revenue changes in FY2023?",
            "expected_type": "causal",
            "min_hops": 2,
            "max_hops": 4,
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"TEST {i}/{len(test_cases)}: {test['expected_type'].upper()}")
        logger.info("=" * 70)
        logger.info(f"Query: {test['query']}")
        logger.info(f"Expected hops: {test['min_hops']}-{test['max_hops']}")
        logger.info("-" * 70)

        try:
            result = system.query(test["query"])
            actual_hops = result.hops_used

            # Check if in expected range
            in_range = test["min_hops"] <= actual_hops <= test["max_hops"]

            logger.info("")
            logger.info("-" * 70)
            logger.info(f"RESULT:")
            logger.info(f"  Actual hops: {actual_hops}")
            logger.info(f"  Mode: {result.mode}")
            logger.info(f"  Confidence: {result.confidence:.2%}")
            logger.info(f"  In expected range: {'✓ YES' if in_range else '✗ NO'}")

            # Show trajectory
            logger.info(f"\n  Trajectory:")
            for j, t in enumerate(result.trajectory):
                logger.info(f"    Hop {j+1}: Δ={t.combined:.3f} (E={t.delta_E:.3f}, A={t.delta_A:.3f})")

            # Show answer preview
            answer_preview = result.answer[:200] + "..." if len(result.answer) > 200 else result.answer
            logger.info(f"\n  Answer: {answer_preview}")

            results.append({
                "query": test["query"],
                "expected_type": test["expected_type"],
                "actual_hops": actual_hops,
                "expected_range": (test["min_hops"], test["max_hops"]),
                "in_range": in_range,
                "mode": str(result.mode),
                "confidence": result.confidence
            })

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": test["query"],
                "expected_type": test["expected_type"],
                "error": str(e)
            })

    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)

    passed = sum(1 for r in results if r.get("in_range", False))
    total = len(results)

    for r in results:
        if "error" in r:
            logger.error(f"✗ {r['expected_type']}: Error - {r['error']}")
        elif r["in_range"]:
            logger.info(f"✓ {r['expected_type']}: {r['actual_hops']} hops (expected {r['expected_range'][0]}-{r['expected_range'][1]})")
        else:
            logger.warning(f"✗ {r['expected_type']}: {r['actual_hops']} hops (expected {r['expected_range'][0]}-{r['expected_range'][1]})")

    logger.info("")
    logger.info(f"Passed: {passed}/{total}")
    logger.info("=" * 70)

    system.close()

    return results


if __name__ == "__main__":
    run_live_test()
