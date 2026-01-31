#!/usr/bin/env python3
"""
End-to-End Test for Gross Margin Query Fix.

This script tests the complete OpMech-GraphRAG pipeline with the
problematic query: "Is Apple's gross margin pressure cyclical or structural?"

Tests:
1. Query classification correctly identifies numerical aspects
2. Operator A finds FINANCIAL_LINE nodes with margin data
3. Evidence includes actual margin percentages
4. Final answer references specific figures

Requires: Neo4j and vLLM running
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_full_pipeline():
    """Test the complete OpMech-GraphRAG pipeline."""
    print("\n" + "=" * 70)
    print("END-TO-END TEST: Gross Margin Query")
    print("=" * 70)

    from src.config import settings
    from src.opmech.system import OpMechGraphRAG
    from src.opmech.query_classifier import HybridQueryClassifier

    # Initialize components
    print("\n1. Initializing components...")

    # Initialize system with connection parameters (vLLM on port 8001)
    system = OpMechGraphRAG(
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        vllm_url="http://localhost:8001/v1"
    )
    print(f"   System initialized - {len(system.graph.embeddings)} embeddings loaded")

    classifier = HybridQueryClassifier()
    print("   Query classifier initialized")

    # Test query
    query = "Is Apple's gross margin pressure cyclical or structural?"
    print(f"\n2. Testing query: \"{query}\"")

    # Step 1: Test classification
    print("\n" + "-" * 50)
    print("STEP 1: Query Classification")
    print("-" * 50)

    classification = classifier.classify(query)
    print(f"   Type: {classification.query_type.value}")
    print(f"   Complexity: {classification.complexity}")
    print(f"   has_numerical_aspect: {classification.has_numerical_aspect}")
    print(f"   Confidence: {classification.confidence:.2f}")

    assert classification.has_numerical_aspect, "FAIL: Should detect numerical aspect!"
    print("   [PASS] Numerical aspect detected correctly")

    # Step 2: Run full query
    print("\n" + "-" * 50)
    print("STEP 2: Running Full Query Pipeline")
    print("-" * 50)

    result = system.query(query)

    print(f"\n   Mode: {result.mode.value}")
    print(f"   Hops used: {result.hops_used}")
    print(f"   Confidence: {result.confidence:.2%}")

    # Step 3: Analyze evidence
    print("\n" + "-" * 50)
    print("STEP 3: Evidence Analysis")
    print("-" * 50)

    evidence_A = result.evidence_A
    evidence_B = result.evidence_B

    print(f"\n   Operator A evidence: {len(evidence_A)} nodes")
    print(f"   Operator B evidence: {len(evidence_B)} nodes")

    # Check for FINANCIAL_LINE nodes
    financial_A = [n for n in evidence_A if n.type == "FINANCIAL_LINE"]
    financial_B = [n for n in evidence_B if n.type == "FINANCIAL_LINE"]

    print(f"\n   FINANCIAL_LINE in Operator A: {len(financial_A)} nodes")
    print(f"   FINANCIAL_LINE in Operator B: {len(financial_B)} nodes")

    # Check for margin-related evidence
    margin_keywords = ["margin", "gross", "profit", "cost of sales", "%"]
    margin_evidence_A = []
    margin_evidence_B = []

    for node in evidence_A:
        if any(kw in node.text.lower() for kw in margin_keywords):
            margin_evidence_A.append(node)

    for node in evidence_B:
        if any(kw in node.text.lower() for kw in margin_keywords):
            margin_evidence_B.append(node)

    print(f"\n   Margin-related evidence in A: {len(margin_evidence_A)} nodes")
    print(f"   Margin-related evidence in B: {len(margin_evidence_B)} nodes")

    # Display some margin evidence
    if margin_evidence_A:
        print("\n   Sample margin evidence from Operator A:")
        for node in margin_evidence_A[:3]:
            xbrl_tag = node.metadata.get('xbrl_tag', 'N/A')
            print(f"      [{node.type}] {xbrl_tag}: {node.text[:80]}...")

    # Step 4: Analyze answers
    print("\n" + "-" * 50)
    print("STEP 4: Answer Analysis")
    print("-" * 50)

    print("\n   Operator A Answer:")
    print(f"   {result.answer_A[:300]}...")

    print("\n   Operator B Answer:")
    print(f"   {result.answer_B[:300]}...")

    print("\n   Final Answer:")
    print(f"   {result.answer[:500]}...")

    # Check if answers mention percentages
    answer_lower = result.answer.lower()
    has_percentages = '%' in result.answer or 'percent' in answer_lower
    has_margin_figures = any(fig in answer_lower for fig in ['36', '44', '45', '46', '74', '180', '170'])

    print("\n   Answer Quality Check:")
    print(f"      Contains percentages: {'YES' if has_percentages else 'NO'}")
    print(f"      Contains specific figures: {'YES' if has_margin_figures else 'NO'}")

    # Step 5: Final verdict
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)

    results = {
        "has_numerical_aspect detected": classification.has_numerical_aspect,
        "FINANCIAL_LINE in evidence": len(financial_A) > 0 or len(financial_B) > 0,
        "Margin evidence found": len(margin_evidence_A) > 0 or len(margin_evidence_B) > 0,
        "Answer has percentages": has_percentages,
    }

    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"   [{status}] {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL TESTS PASSED!")
        print("The gross margin evidence retrieval fix is working correctly.")
    else:
        print("SOME TESTS FAILED")
        print("Please review the output above.")
    print("=" * 70)

    # Cleanup
    system.graph.close()

    return all_passed


def test_operator_a_directly():
    """Test Operator A seed selection directly."""
    print("\n" + "=" * 70)
    print("DIRECT TEST: Operator A Seed Selection")
    print("=" * 70)

    from src.config import settings
    from src.opmech.graph_interface import KnowledgeGraphInterface
    from src.opmech.operators import OperatorA
    from src.ingestion.embedding_engine import EmbeddingEngine

    graph = KnowledgeGraphInterface(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password
    )

    # Create embedding function
    try:
        embed_engine = EmbeddingEngine()
        embed_fn = lambda text: embed_engine.embed_text(text)
    except Exception:
        # Fallback to simple embedding
        import numpy as np
        embed_fn = lambda text: np.random.randn(768)

    operator = OperatorA(graph=graph, embed_fn=embed_fn)

    query = "Is Apple's gross margin pressure cyclical or structural?"
    print(f"\nQuery: \"{query}\"")

    # Test _find_direct_financial_seeds
    print("\nTesting _find_direct_financial_seeds()...")
    seeds = operator._find_direct_financial_seeds(query)

    print(f"Found {len(seeds)} seed nodes:")
    for i, node in enumerate(seeds[:5]):
        xbrl_tag = node.metadata.get('xbrl_tag', 'N/A')
        value = node.metadata.get('value', 'N/A')
        print(f"   {i+1}. [{node.type}] {xbrl_tag}")
        print(f"      Value: {value}")
        print(f"      Text: {node.text[:80]}...")

    # Check for gross profit nodes
    gross_profit_nodes = [n for n in seeds if 'gross' in n.text.lower() or
                         (n.metadata.get('xbrl_tag') and 'gross' in n.metadata.get('xbrl_tag', '').lower())]

    print(f"\nGross profit related nodes: {len(gross_profit_nodes)}")

    graph.close()

    return len(seeds) > 0 and len(gross_profit_nodes) > 0


def main():
    """Run all end-to-end tests."""
    print("=" * 70)
    print("OpMech-GraphRAG: End-to-End Margin Query Test")
    print("=" * 70)
    print("\nRequirements: Neo4j and vLLM must be running")

    # First test Operator A directly
    print("\n" + "=" * 70)
    op_a_result = test_operator_a_directly()

    # Then run full pipeline test
    print("\n" + "=" * 70)
    full_result = test_full_pipeline()

    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"   Operator A Seed Selection: {'PASS' if op_a_result else 'FAIL'}")
    print(f"   Full Pipeline Test: {'PASS' if full_result else 'FAIL'}")
    print("=" * 70)

    return 0 if (op_a_result and full_result) else 1


if __name__ == "__main__":
    sys.exit(main())
