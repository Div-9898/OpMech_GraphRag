#!/usr/bin/env python3
"""
Run a query through the Unified OpMech Pipeline.

This uses the ground-truth-first architecture that fixes the core problem:
- OLD: LLM generates answer -> Ground truth validates/corrects AFTER
- NEW: Ground truth retrieved FIRST -> Injected as mandatory facts -> LLM generates WITH the facts

Usage:
    python scripts/run_unified_query.py "What is Apple's services revenue?"
    python scripts/run_unified_query.py --interactive
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.unified_system import UnifiedOpMechSystem


def run_query(query: str, system: UnifiedOpMechSystem) -> None:
    """Run a single query and display results."""
    print("=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)
    print()

    result = system.query(query)

    print("ANSWER:")
    print("-" * 70)
    print(result.answer)
    print("-" * 70)
    print()

    print("METRICS:")
    print(f"  Confidence: {result.confidence:.1%}")
    print(f"  Mode: {result.mode}")
    print(f"  Ground Truth Used: {result.ground_truth_used}")
    print(f"  XBRL Evidence Count: {result.xbrl_evidence_count}")
    print(f"  Validations Passed: {result.validations_passed}")
    print(f"  Validations Failed: {result.validations_failed}")
    print()

    if result.confidence_explanation:
        print("CONFIDENCE EXPLANATION:")
        print(f"  {result.confidence_explanation}")
        print()


def interactive_mode(system: UnifiedOpMechSystem) -> None:
    """Run in interactive mode."""
    print("=" * 70)
    print("UNIFIED OPMECH SYSTEM - Interactive Mode")
    print("=" * 70)
    print("Using ground-truth-first architecture.")
    print("Type 'quit' or 'exit' to stop.")
    print()

    while True:
        try:
            query = input("Enter query: ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            run_query(query, system)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Run queries through the Unified OpMech Pipeline"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="The query to process"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--vllm-url",
        default="http://localhost:8001/v1",
        help="vLLM server URL"
    )

    args = parser.parse_args()

    # Initialize system
    print("Initializing Unified OpMech System...")
    system = UnifiedOpMechSystem(
        vllm_url=args.vllm_url,
    )
    print("System initialized.")
    print()

    if args.interactive:
        interactive_mode(system)
    elif args.query:
        run_query(args.query, system)
    else:
        # Default: run example queries
        example_queries = [
            "What is Apple's services business like?",
            "What was iPhone revenue in FY2024?",
            "How did Apple's revenue change from FY2023 to FY2024?",
            "What is the gross margin trend?",
        ]

        print("Running example queries:")
        print()

        for query in example_queries:
            run_query(query, system)
            print()


if __name__ == "__main__":
    main()
