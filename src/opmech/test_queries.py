"""Test queries for OpMech-GraphRAG evaluation."""

from typing import Dict, List

from loguru import logger

from src.opmech.system import OpMechGraphRAG
from src.opmech.visualization import print_trajectory, export_trajectory_json

# Test queries with expected modes
TEST_QUERIES = [
    # Expected: EXPLOIT (low divergence, simple fact)
    {
        "query": "What was Apple's total revenue in FY2023?",
        "expected_mode": "exploit",
        "expected_hops": "1-2",
        "notes": "Simple factual query, both operators should find same XBRL data"
    },

    # Expected: EXPLORE (high divergence, ambiguous interpretation)
    {
        "query": "Is Apple's gross margin pressure cyclical or structural?",
        "expected_mode": "explore",
        "expected_hops": "4-6",
        "notes": "Numbers show decline, narrative emphasizes Services growth - fundamental tension"
    },

    # Expected: ADAPTIVE (medium divergence)
    {
        "query": "What drove iPhone revenue changes in FY2023?",
        "expected_mode": "adaptive",
        "expected_hops": "2-4",
        "notes": "Both paths find relevant info, slightly different emphasis"
    },

    # Expected: EXPLORE (risk assessment ambiguity)
    {
        "query": "Are Apple's supply chain risks improving or worsening?",
        "expected_mode": "explore",
        "expected_hops": "4-6",
        "notes": "Risk Factors narrative vs. actual supplier diversity metrics may conflict"
    },

    # Expected: EXPLOIT (temporal comparison)
    {
        "query": "How did R&D expenses change from FY2022 to FY2023?",
        "expected_mode": "exploit",
        "expected_hops": "2-3",
        "notes": "Clear temporal traversal, both operators should align"
    },

    # Expected: ADAPTIVE (causal analysis)
    {
        "query": "What factors contributed to Services revenue growth?",
        "expected_mode": "adaptive",
        "expected_hops": "3-4",
        "notes": "Causal edges important, some subjectivity in attribution"
    },

    # Expected: EXPLORE (strategic interpretation)
    {
        "query": "Is Apple's R&D spending growth-oriented or maintenance-driven?",
        "expected_mode": "explore",
        "expected_hops": "4-6",
        "notes": "Numbers vs. strategic narrative interpretation"
    },

    # Expected: EXPLOIT (specific note reference)
    {
        "query": "What is Apple's revenue recognition policy?",
        "expected_mode": "exploit",
        "expected_hops": "1-2",
        "notes": "Specific to Note section, both operators should converge"
    }
]


def run_single_query(system: OpMechGraphRAG, query: str, verbose: bool = True):
    """
    Run a single query through the system.

    Args:
        system: OpMech-GraphRAG system instance
        query: Query string
        verbose: Whether to print full trajectory

    Returns:
        QueryResult
    """
    result = system.query(query)

    if verbose:
        print_trajectory(result)

    return result


def run_tests(verbose: bool = True, export_dir: str = None) -> List[Dict]:
    """
    Run all test queries and report results.

    Args:
        verbose: Whether to print full trajectories
        export_dir: Optional directory to export results

    Returns:
        List of test result dictionaries
    """
    system = OpMechGraphRAG()
    results = []

    for i, test in enumerate(TEST_QUERIES):
        print(f"\n{'='*70}")
        print(f"TEST {i+1}/{len(TEST_QUERIES)}")
        print(f"QUERY: {test['query']}")
        print(f"Expected: {test['expected_mode']}, {test['expected_hops']} hops")
        print(f"{'='*70}")

        try:
            result = system.query(test['query'])

            # Check if mode matches expectation
            mode_match = result.mode.value == test['expected_mode']

            test_result = {
                "query": test['query'],
                "expected_mode": test['expected_mode'],
                "actual_mode": result.mode.value,
                "mode_match": mode_match,
                "hops_used": result.hops_used,
                "confidence": result.confidence,
                "final_divergence": result.trajectory[-1].combined if result.trajectory else 0
            }
            results.append(test_result)

            if verbose:
                print_trajectory(result)

            # Export if directory specified
            if export_dir:
                import os
                os.makedirs(export_dir, exist_ok=True)
                export_path = os.path.join(export_dir, f"test_{i+1}.json")
                export_trajectory_json(result, export_path)

        except Exception as e:
            logger.error(f"Test failed: {e}")
            results.append({
                "query": test['query'],
                "expected_mode": test['expected_mode'],
                "actual_mode": "error",
                "mode_match": False,
                "error": str(e)
            })

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    correct = sum(1 for r in results if r.get('mode_match', False))
    print(f"\nMode Accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")

    print("\nDetailed Results:")
    for r in results:
        status = "[PASS]" if r.get('mode_match', False) else "[FAIL]"
        if 'error' in r:
            print(f"{status} {r['query'][:50]}... -> ERROR: {r['error']}")
        else:
            print(f"{status} {r['query'][:50]}... -> {r['actual_mode']} (expected {r['expected_mode']})")

    system.close()
    return results


def run_quick_demo():
    """Run a quick demo with one query per mode type."""
    system = OpMechGraphRAG()

    demo_queries = [
        "What was Apple's total revenue in FY2023?",  # Likely EXPLOIT
        "What factors contributed to Services revenue growth?",  # Likely ADAPTIVE
        "Is Apple's R&D spending growth-oriented or maintenance-driven?",  # Likely EXPLORE
    ]

    for query in demo_queries:
        print(f"\n{'='*70}")
        print(f"QUERY: {query}")
        print(f"{'='*70}")

        result = system.query(query)
        print_trajectory(result)

    system.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_quick_demo()
    else:
        run_tests(verbose=True, export_dir="results/opmech_tests")
