"""
Edge Case Testing for Hybrid Query Classification

Tests classification accuracy on various query types including:
1. Edge cases (ambiguous, short, complex)
2. Revenue variations (same intent, different phrasing)
3. Comprehensive mode testing (EXPLOIT/EXPLORE/ADAPTIVE)
"""

from src.opmech.query_classifier import HybridQueryClassifier, QueryType


def test_edge_cases():
    """Test edge cases that might confuse the classifier."""
    classifier = HybridQueryClassifier()

    edge_cases = [
        # Simple factual (should be EXPLOIT -> NUMERICAL)
        ("What was Apple's net income in FY2023?", "numerical"),
        ("What is Apple's gross margin percentage?", "numerical"),

        # Ambiguous (interesting to see classification)
        ("Tell me about Apple's revenue", "descriptive"),  # vague, descriptive
        ("Apple's margin situation", "descriptive"),  # vague, could be opinion

        # Complex opinion (should be EXPLORE -> OPINION)
        ("Should I invest in Apple stock?", "opinion"),
        ("Is Apple overvalued?", "opinion"),

        # Comparison (might be ADAPTIVE or EXPLORE -> COMPARATIVE)
        ("How does Apple's R&D compare to Microsoft?", "comparative"),
    ]

    print("=" * 70)
    print("EDGE CASE TESTING")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, expected_type in edge_cases:
        result = classifier.classify(query)
        actual_type = result.query_type.value
        match = actual_type == expected_type

        status = "[PASS]" if match else "[FAIL]"
        if match:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} Query: {query}")
        print(f"       Expected: {expected_type}, Actual: {actual_type}")
        print(f"       Complexity: {result.complexity}, Confidence: {result.confidence:.2f}")
        print(f"       Method: {result.classification_method}")
        if result.pattern_scores:
            top_scores = sorted(result.pattern_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            scores_str = ", ".join(f"{k}={v:.1f}" for k, v in top_scores if v > 0)
            if scores_str:
                print(f"       Top scores: {scores_str}")

    print(f"\n{'=' * 70}")
    print(f"Edge Cases: {passed}/{passed + failed} passed")
    return passed, failed


def test_revenue_variations():
    """Test that different phrasings of the same revenue query classify consistently."""
    classifier = HybridQueryClassifier()

    revenue_variations = [
        "What was Apple's total revenue in FY2023?",  # Original
        "Apple's FY2023 revenue?",  # Shorter
        "How much revenue did Apple make in fiscal 2023?",  # Different phrasing
        "Total sales for Apple in 2023",  # "sales" instead of "revenue"
    ]

    print("\n" + "=" * 70)
    print("REVENUE VARIATION TESTING")
    print("=" * 70)
    print("(All should be NUMERICAL)")

    all_numerical = True

    for query in revenue_variations:
        result = classifier.classify(query)

        is_numerical = result.query_type == QueryType.NUMERICAL
        status = "[PASS]" if is_numerical else "[FAIL]"
        if not is_numerical:
            all_numerical = False

        print(f"\n{status} Query: {query}")
        print(f"       Type: {result.query_type.value}, Expects number: {result.expects_number}")
        print(f"       Complexity: {result.complexity}, Confidence: {result.confidence:.2f}")

    result_str = "PASS" if all_numerical else "FAIL"
    print(f"\n{'=' * 70}")
    print(f"Revenue Variations: {result_str}")
    return 4 if all_numerical else 0, 0 if all_numerical else 4


def test_comprehensive_mode_queries():
    """Test comprehensive set of queries with expected modes."""
    classifier = HybridQueryClassifier()

    # Map expected mode to expected query type
    mode_to_type = {
        "EXPLOIT": [QueryType.NUMERICAL],
        "EXPLORE": [QueryType.OPINION, QueryType.COMPARATIVE],
        "ADAPTIVE": [QueryType.CAUSAL, QueryType.DESCRIPTIVE],
    }

    COMPREHENSIVE_TEST_QUERIES = [
        # EXPLOIT candidates (NUMERICAL)
        ("What was Apple's total revenue in FY2023?", "EXPLOIT"),
        ("What was net income in FY2023?", "EXPLOIT"),
        ("How many employees does Apple have?", "EXPLOIT"),

        # EXPLORE candidates (OPINION)
        ("Is Apple's margin pressure cyclical or structural?", "EXPLORE"),
        ("Should Apple increase dividends?", "EXPLORE"),
        ("Is Apple's growth sustainable?", "EXPLORE"),

        # ADAPTIVE candidates (CAUSAL/DESCRIPTIVE)
        ("What factors drove iPhone revenue changes?", "ADAPTIVE"),
        ("Why did services revenue grow?", "ADAPTIVE"),
        ("What are the main risk factors?", "ADAPTIVE"),
    ]

    print("\n" + "=" * 70)
    print("COMPREHENSIVE MODE TESTING")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, expected_mode in COMPREHENSIVE_TEST_QUERIES:
        result = classifier.classify(query)
        actual_type = result.query_type

        # Check if the type matches expected mode's types
        expected_types = mode_to_type.get(expected_mode, [])
        match = actual_type in expected_types

        # Special case: ADAPTIVE can also include TEMPORAL
        if expected_mode == "ADAPTIVE" and actual_type == QueryType.TEMPORAL:
            match = True

        status = "[PASS]" if match else "[WARN]"
        if match:
            passed += 1
        else:
            failed += 1

        expected_types_str = "/".join(t.value for t in expected_types)

        print(f"\n{status} Query: {query}")
        print(f"       Expected mode: {expected_mode} (types: {expected_types_str})")
        print(f"       Actual type: {actual_type.value}, Complexity: {result.complexity}")
        print(f"       Confidence: {result.confidence:.2f}")

    print(f"\n{'=' * 70}")
    print(f"Comprehensive Test: {passed}/{passed + failed} passed")
    return passed, failed


def test_complexity_detection():
    """Test that complexity is properly detected."""
    classifier = HybridQueryClassifier()

    complexity_tests = [
        # Simple queries
        ("What was Apple's revenue?", "simple"),
        ("How many employees?", "simple"),

        # Moderate queries
        ("What factors contributed to revenue growth in FY2023?", "moderate"),
        ("Why did Apple's margin decline last quarter?", "moderate"),

        # Complex queries
        ("Is Apple's margin pressure cyclical or structural given macroeconomic trends?", "complex"),
        ("Analyze the factors that drove the decline in iPhone revenue and evaluate their long-term implications for market share", "complex"),
    ]

    print("\n" + "=" * 70)
    print("COMPLEXITY DETECTION TESTING")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, expected_complexity in complexity_tests:
        result = classifier.classify(query)
        actual_complexity = result.complexity
        match = actual_complexity == expected_complexity

        status = "[PASS]" if match else "[FAIL]"
        if match:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} Query: {query[:60]}...")
        print(f"       Expected: {expected_complexity}, Actual: {actual_complexity}")
        print(f"       Type: {result.query_type.value}")

    print(f"\n{'=' * 70}")
    print(f"Complexity Detection: {passed}/{passed + failed} passed")
    return passed, failed


def test_context_rules():
    """Test that context rules are properly applied."""
    classifier = HybridQueryClassifier()

    context_rule_tests = [
        # "or" judgment should trigger OPINION
        ("Is Apple's pressure cyclical or structural?", QueryType.OPINION, ["or_judgment"]),
        ("Is growth sustainable or temporary?", QueryType.OPINION, ["is_are_judgment"]),

        # "What was X" + financial ending should trigger NUMERICAL
        ("What was Apple's total revenue?", QueryType.NUMERICAL, ["what_was_amount"]),

        # "What factors" should trigger CAUSAL
        ("What factors drove iPhone revenue?", QueryType.CAUSAL, ["factors_drove"]),

        # Fiscal year ending should boost NUMERICAL
        ("What was revenue in FY2023?", QueryType.NUMERICAL, ["fiscal_year_ending"]),
    ]

    print("\n" + "=" * 70)
    print("CONTEXT RULES TESTING")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, expected_type, expected_rules in context_rule_tests:
        result = classifier.classify(query)

        type_match = result.query_type == expected_type
        # Check if any expected rule was applied (from reasoning)
        rules_applied = any(rule in result.reasoning for rule in expected_rules)

        status = "[PASS]" if type_match else "[FAIL]"
        if type_match:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} Query: {query}")
        print(f"       Expected: {expected_type.value}, Actual: {result.query_type.value}")
        print(f"       Expected rules: {expected_rules}")
        print(f"       Reasoning: {result.reasoning}")

    print(f"\n{'=' * 70}")
    print(f"Context Rules: {passed}/{passed + failed} passed")
    return passed, failed


def run_all_edge_case_tests():
    """Run all edge case tests."""
    print("\n" + "=" * 70)
    print("HYBRID QUERY CLASSIFIER - EDGE CASE TEST SUITE")
    print("=" * 70 + "\n")

    results = []

    # Run all test suites
    results.append(("Edge Cases", test_edge_cases()))
    results.append(("Revenue Variations", test_revenue_variations()))
    results.append(("Comprehensive Mode", test_comprehensive_mode_queries()))
    results.append(("Complexity Detection", test_complexity_detection()))
    results.append(("Context Rules", test_context_rules()))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    for name, (passed, failed) in results:
        total_passed += passed
        total_failed += failed
        status = "PASS" if failed == 0 else "WARN" if failed < passed else "FAIL"
        print(f"  [{status}] {name}: {passed}/{passed + failed}")

    print(f"\n  TOTAL: {total_passed}/{total_passed + total_failed} tests passed")
    print("=" * 70)

    return total_passed, total_failed


if __name__ == "__main__":
    run_all_edge_case_tests()
