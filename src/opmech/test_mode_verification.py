"""
Mode Selection Verification Test

Tests three queries designed to trigger each mode:
1. EXPLOIT - Simple factual query (should trust XBRL)
2. EXPLORE - Opinion/speculative query (multiple perspectives)
3. ADAPTIVE - Causal query with nuance (balanced view)
"""

import sys
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<8} | {message}")

from src.opmech.system import OpMechGraphRAG


def run_verification_tests():
    """Run three queries to verify mode selection works correctly."""

    print("\n" + "=" * 80)
    print("MODE SELECTION VERIFICATION TEST")
    print("=" * 80)

    # Initialize system
    print("\nInitializing OpMech-GraphRAG system...")
    system = OpMechGraphRAG(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        vllm_url="http://localhost:8000/v1",
        tau_low=0.25,
        tau_high=0.60,
        max_hops=4
    )

    # Define test queries
    test_queries = [
        {
            "query": "What was Apple's total revenue in FY2023?",
            "expected_mode": "EXPLOIT",
            "description": "Simple numerical query - should trust XBRL data",
        },
        {
            "query": "Is Apple's gross margin pressure cyclical or structural?",
            "expected_mode": "EXPLORE",
            "description": "Opinion/speculative query - multiple perspectives needed",
        },
        {
            "query": "What factors drove iPhone revenue changes in FY2023?",
            "expected_mode": "ADAPTIVE",
            "description": "Causal query - needs balanced analysis",
        },
    ]

    results = []

    for i, test in enumerate(test_queries, 1):
        print("\n" + "=" * 80)
        print(f"TEST {i}/3: {test['expected_mode']} MODE TEST")
        print("=" * 80)
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_mode']}")
        print(f"Description: {test['description']}")
        print("-" * 80)

        try:
            result = system.query(test['query'])

            # Check mode
            actual_mode = result.mode.value.upper()
            mode_match = actual_mode == test['expected_mode']

            print(f"\nRESULT:")
            print(f"  Mode: {actual_mode} {'[CORRECT]' if mode_match else '[MISMATCH - expected ' + test['expected_mode'] + ']'}")
            print(f"  Confidence: {result.confidence:.0%}")
            print(f"  Hops Used: {result.hops_used}")
            print(f"  Reasoning: {result.reasoning}")

            # Show evidence breakdown
            evidence_A_types = {}
            for node in result.evidence_A:
                t = node.type
                evidence_A_types[t] = evidence_A_types.get(t, 0) + 1

            evidence_B_types = {}
            for node in result.evidence_B:
                t = node.type
                evidence_B_types[t] = evidence_B_types.get(t, 0) + 1

            print(f"\n  Evidence A types: {evidence_A_types}")
            print(f"  Evidence B types: {evidence_B_types}")

            # Show divergence
            if result.trajectory:
                final = result.trajectory[-1]
                print(f"\n  Final Divergence:")
                print(f"    Combined: {final.combined:.3f}")
                print(f"    Delta_A (answer): {final.delta_A:.3f}")
                print(f"    Delta_E (evidence): {final.delta_E:.3f}")

            # Show answer (truncated)
            print(f"\n  ANSWER (first 500 chars):")
            print("-" * 40)
            answer_preview = result.answer[:500] if result.answer else "(No answer)"
            print(answer_preview)
            if len(result.answer) > 500:
                print("...")
            print("-" * 40)

            results.append({
                "query": test['query'],
                "expected": test['expected_mode'],
                "actual": actual_mode,
                "match": mode_match,
                "confidence": result.confidence,
            })

        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": test['query'],
                "expected": test['expected_mode'],
                "actual": "ERROR",
                "match": False,
                "error": str(e),
            })

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    correct = sum(1 for r in results if r.get('match', False))
    print(f"\nMode Accuracy: {correct}/{len(results)}")

    for r in results:
        status = "[PASS]" if r.get('match') else "[FAIL]"
        if 'error' in r:
            print(f"{status} {r['query'][:50]}... -> ERROR: {r['error'][:50]}")
        else:
            conf = r.get('confidence', 0)
            print(f"{status} {r['query'][:50]}... -> {r['actual']} (expected {r['expected']}, conf={conf:.0%})")

    # Clean up
    system.close()

    return results


if __name__ == "__main__":
    run_verification_tests()
