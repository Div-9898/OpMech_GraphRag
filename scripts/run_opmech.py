#!/usr/bin/env python3
"""CLI interface for OpMech-GraphRAG system."""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.opmech.system import OpMechGraphRAG
from src.opmech.visualization import print_trajectory, export_trajectory_json


def main():
    parser = argparse.ArgumentParser(
        description="OpMech-GraphRAG: Commutator-Guided Explore/Exploit GraphRAG"
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Query to run (if not provided, enters interactive mode)"
    )

    parser.add_argument(
        "--neo4j-uri",
        default="bolt://localhost:7687",
        help="Neo4j connection URI"
    )

    parser.add_argument(
        "--neo4j-user",
        default="neo4j",
        help="Neo4j username"
    )

    parser.add_argument(
        "--neo4j-password",
        default="password123",
        help="Neo4j password"
    )

    parser.add_argument(
        "--vllm-url",
        default="http://localhost:8000/v1",
        help="vLLM server URL"
    )

    parser.add_argument(
        "--tau-low",
        type=float,
        default=0.25,
        help="Low divergence threshold (default: 0.25)"
    )

    parser.add_argument(
        "--tau-high",
        type=float,
        default=0.60,
        help="High divergence threshold (default: 0.60)"
    )

    parser.add_argument(
        "--max-hops",
        type=int,
        default=6,
        help="Maximum traversal hops (default: 6)"
    )

    parser.add_argument(
        "--export",
        help="Export result to JSON file"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test suite"
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run quick demo with sample queries"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")

    # Run test suite
    if args.test:
        from src.opmech.test_queries import run_tests
        run_tests(verbose=True, export_dir="results/opmech_tests")
        return

    # Run demo
    if args.demo:
        from src.opmech.test_queries import run_quick_demo
        run_quick_demo()
        return

    # Initialize system
    logger.info("Initializing OpMech-GraphRAG...")
    system = OpMechGraphRAG(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        vllm_url=args.vllm_url,
        tau_low=args.tau_low,
        tau_high=args.tau_high,
        max_hops=args.max_hops
    )

    try:
        if args.query:
            # Single query mode
            result = system.query(args.query)
            print_trajectory(result)

            if args.export:
                export_trajectory_json(result, args.export)

        else:
            # Interactive mode
            print("\nOpMech-GraphRAG Interactive Mode")
            print("Type 'exit' or 'quit' to exit")
            print("-" * 50)

            while True:
                try:
                    query = input("\nQuery: ").strip()

                    if query.lower() in ['exit', 'quit', 'q']:
                        break

                    if not query:
                        continue

                    result = system.query(query)
                    print_trajectory(result)

                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break
                except Exception as e:
                    logger.error(f"Query failed: {e}")

    finally:
        system.close()


if __name__ == "__main__":
    main()
