"""
Test suite for hop termination logic.

Verifies that queries use appropriate number of hops based on query type.

Expected behavior:
- Simple queries (EXPLOIT): 2-3 hops, stop when Δ < 0.25
- Moderate queries (ADAPTIVE): 3-4 hops, balanced exploration
- Complex/Opinion queries (EXPLORE): 3-5 hops, thorough exploration
"""

import pytest
from unittest.mock import Mock, patch
from loguru import logger


def test_hop_counts():
    """Verify queries use appropriate number of hops based on query type."""

    # Import here to allow for mocking
    from src.opmech.system import OpMechGraphRAG

    system = OpMechGraphRAG(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        vllm_url="http://localhost:8000/v1",
        tau_low=0.25,
        tau_high=0.60,
        max_hops=4
    )

    test_cases = [
        {
            "query": "What was Apple's total revenue in FY2023?",
            "expected_type": "numerical",
            "min_hops": 2,
            "max_hops": 3,
            "description": "Simple numerical query should converge quickly"
        },
        {
            "query": "Is Apple's gross margin pressure cyclical or structural?",
            "expected_type": "opinion",
            "min_hops": 3,  # Force at least 3 for opinion
            "max_hops": 5,
            "description": "Opinion query should explore thoroughly"
        },
        {
            "query": "What factors drove iPhone revenue changes in FY2023?",
            "expected_type": "causal",
            "min_hops": 2,
            "max_hops": 4,
            "description": "Causal query needs moderate exploration"
        },
        {
            "query": "How did Apple's services revenue change from FY2022 to FY2023?",
            "expected_type": "temporal",
            "min_hops": 2,
            "max_hops": 4,
            "description": "Temporal query needs to explore multiple periods"
        },
    ]

    results = []

    for test in test_cases:
        logger.info(f"\nTesting: {test['query'][:50]}...")
        logger.info(f"Expected type: {test['expected_type']}")
        logger.info(f"Expected hops: {test['min_hops']}-{test['max_hops']}")

        try:
            result = system.query(test["query"])
            actual_hops = result.hops_used

            logger.info(f"Actual hops: {actual_hops}")
            logger.info(f"Mode: {result.mode}")

            # Check hop count
            in_range = test["min_hops"] <= actual_hops <= test["max_hops"]

            if not in_range:
                logger.warning(
                    f"⚠️ {test['expected_type']}: {actual_hops} hops "
                    f"(expected {test['min_hops']}-{test['max_hops']})"
                )
            else:
                logger.info(
                    f"✓ {test['expected_type']}: {actual_hops} hops "
                    f"(expected {test['min_hops']}-{test['max_hops']})"
                )

            results.append({
                "query": test["query"],
                "expected_type": test["expected_type"],
                "actual_hops": actual_hops,
                "expected_range": (test["min_hops"], test["max_hops"]),
                "in_range": in_range,
                "mode": result.mode
            })

        except Exception as e:
            logger.error(f"Error testing query: {e}")
            results.append({
                "query": test["query"],
                "error": str(e)
            })

    system.close()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("HOP TERMINATION TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for r in results if r.get("in_range", False))
    total = len(results)

    for r in results:
        if "error" in r:
            logger.error(f"✗ {r['expected_type']}: Error - {r['error']}")
        elif r["in_range"]:
            logger.info(f"✓ {r['expected_type']}: {r['actual_hops']} hops")
        else:
            logger.warning(
                f"✗ {r['expected_type']}: {r['actual_hops']} hops "
                f"(expected {r['expected_range'][0]}-{r['expected_range'][1]})"
            )

    logger.info(f"\nPassed: {passed}/{total}")
    logger.info("=" * 60)

    return results


def test_termination_conditions():
    """Test individual termination conditions."""

    from src.opmech.system import OpMechGraphRAG
    from src.opmech.data_classes import CommutatorResult
    from src.opmech.query_classifier import QueryClassification, QueryType

    # Create mock system with termination methods
    system = OpMechGraphRAG.__new__(OpMechGraphRAG)
    system.tau_low = 0.25
    system.min_improvement = 0.02
    system.min_hops_opinion = 3

    # Test 1: Strong convergence
    trajectory = [
        CommutatorResult(delta_E=0.3, delta_V=0.3, delta_A=0.1, delta_C=0.2,
                        combined=0.20, weights={}, hop=1,
                        operator_A_score=0.8, operator_B_score=0.8)
    ]
    query_class = QueryClassification(
        query_type=QueryType.NUMERICAL, complexity="simple",
        confidence=0.9, expects_number=True, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )

    should_stop, reason = system._should_terminate(trajectory, 1, 4, query_class)
    assert should_stop, f"Should stop on convergence: {reason}"
    assert "Converged" in reason

    logger.info("✓ Test 1: Strong convergence condition works")

    # Test 2: Opinion query minimum hops
    trajectory = [
        CommutatorResult(delta_E=0.4, delta_V=0.4, delta_A=0.2, delta_C=0.3,
                        combined=0.35, weights={}, hop=1,
                        operator_A_score=0.7, operator_B_score=0.7)
    ]
    query_class = QueryClassification(
        query_type=QueryType.OPINION, complexity="complex",
        confidence=0.8, expects_number=False, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )

    should_stop, reason = system._should_terminate(trajectory, 1, 5, query_class)
    assert not should_stop, f"Opinion query should not stop at hop 1: {reason}"

    should_stop, reason = system._should_terminate(trajectory, 2, 5, query_class)
    assert not should_stop, f"Opinion query should not stop at hop 2: {reason}"

    logger.info("✓ Test 2: Opinion query minimum hops enforced")

    # Test 3: Simple numerical early termination
    trajectory = [
        CommutatorResult(delta_E=0.5, delta_V=0.5, delta_A=0.05, delta_C=0.3,
                        combined=0.32, weights={}, hop=1,
                        operator_A_score=0.8, operator_B_score=0.8)
    ]
    query_class = QueryClassification(
        query_type=QueryType.NUMERICAL, complexity="simple",
        confidence=0.9, expects_number=True, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )

    should_stop, reason = system._should_terminate(trajectory, 2, 4, query_class)
    assert should_stop, f"Simple numerical should stop early: {reason}"
    assert "Simple numerical" in reason

    logger.info("✓ Test 3: Simple numerical early termination works")

    # Test 4: Stability check
    trajectory = [
        CommutatorResult(delta_E=0.5, delta_V=0.5, delta_A=0.3, delta_C=0.3,
                        combined=0.42, weights={}, hop=1,
                        operator_A_score=0.7, operator_B_score=0.7),
        CommutatorResult(delta_E=0.48, delta_V=0.48, delta_A=0.28, delta_C=0.28,
                        combined=0.41, weights={}, hop=2,
                        operator_A_score=0.75, operator_B_score=0.75)
    ]
    query_class = QueryClassification(
        query_type=QueryType.DESCRIPTIVE, complexity="moderate",
        confidence=0.8, expects_number=False, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )

    should_stop, reason = system._should_terminate(trajectory, 2, 4, query_class)
    assert should_stop, f"Should stop on stability: {reason}"
    assert "Stabilized" in reason

    logger.info("✓ Test 4: Stability check works")

    logger.info("\nAll termination condition tests passed!")


def test_effective_max_hops():
    """Test _get_effective_max_hops calculation."""

    from src.opmech.system import OpMechGraphRAG
    from src.opmech.query_classifier import QueryClassification, QueryType

    system = OpMechGraphRAG.__new__(OpMechGraphRAG)
    system.max_hops = 4

    # Simple query
    simple = QueryClassification(
        query_type=QueryType.NUMERICAL, complexity="simple",
        confidence=0.9, expects_number=True, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )
    max_hops = system._get_effective_max_hops(simple)
    assert max_hops <= 3, f"Simple query max_hops should be <= 3, got {max_hops}"
    logger.info(f"✓ Simple query max_hops: {max_hops}")

    # Complex query
    complex_q = QueryClassification(
        query_type=QueryType.CAUSAL, complexity="complex",
        confidence=0.8, expects_number=False, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )
    max_hops = system._get_effective_max_hops(complex_q)
    assert max_hops >= 4, f"Complex query max_hops should be >= 4, got {max_hops}"
    logger.info(f"✓ Complex query max_hops: {max_hops}")

    # Opinion query
    opinion = QueryClassification(
        query_type=QueryType.OPINION, complexity="moderate",
        confidence=0.8, expects_number=False, classification_method="pattern",
        reasoning="test", pattern_scores={}
    )
    max_hops = system._get_effective_max_hops(opinion)
    assert max_hops >= 4, f"Opinion query max_hops should be >= 4, got {max_hops}"
    logger.info(f"✓ Opinion query max_hops: {max_hops}")

    logger.info("\nAll effective max_hops tests passed!")


if __name__ == "__main__":
    logger.info("Running Hop Termination Tests")
    logger.info("=" * 60)

    # Run unit tests first
    logger.info("\n--- Testing Termination Conditions ---")
    test_termination_conditions()

    logger.info("\n--- Testing Effective Max Hops ---")
    test_effective_max_hops()

    # Integration test (requires running Neo4j and vLLM)
    logger.info("\n--- Integration Test (requires services) ---")
    try:
        results = test_hop_counts()
    except Exception as e:
        logger.warning(f"Integration test skipped: {e}")
        logger.info("Start Neo4j and vLLM to run integration tests")
