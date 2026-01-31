#!/usr/bin/env python3
"""
Build the knowledge graph from parsed SEC filings.

This script:
1. Loads nodes and embeddings from the data ingestion phase
2. Runs all 5 MoE experts to discover edges
3. Enforces connectivity (single connected component)
4. Exports to Neo4j and saves to files

Usage:
    python scripts/build_graph.py [--use-llm] [--skip-neo4j] [--experts EXPERT1,EXPERT2]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from loguru import logger

from src.config import settings
from src.graph import GraphBuilder, Neo4jClient
from src.models import Node


def setup_logging(verbose: bool = False):
    """Configure logging."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )


def load_all_nodes() -> list[Node]:
    """Load all parsed nodes from data/parsed/."""
    all_nodes = []

    parsed_dir = settings.parsed_dir
    if not parsed_dir.exists():
        logger.error(f"Parsed directory not found: {parsed_dir}")
        logger.info("Run 'python scripts/fetch_filings.py' first to parse filings")
        return []

    for filing_dir in sorted(parsed_dir.iterdir()):
        if not filing_dir.is_dir():
            continue

        nodes_path = filing_dir / "nodes.jsonl"
        if not nodes_path.exists():
            logger.warning(f"No nodes found in {filing_dir}")
            continue

        filing_nodes = []
        with open(nodes_path, "r") as f:
            for line in f:
                node = Node.model_validate_json(line)
                filing_nodes.append(node)

        all_nodes.extend(filing_nodes)
        logger.info(f"Loaded {len(filing_nodes)} nodes from {filing_dir.name}")

    logger.info(f"Total nodes loaded: {len(all_nodes)}")
    return all_nodes


def load_all_embeddings() -> dict[str, np.ndarray]:
    """Load all embeddings from data/embeddings/."""
    all_embeddings = {}

    embeddings_dir = settings.embeddings_dir
    if not embeddings_dir.exists():
        logger.error(f"Embeddings directory not found: {embeddings_dir}")
        logger.info("Run 'python scripts/fetch_filings.py' first to generate embeddings")
        return {}

    for filing_dir in sorted(embeddings_dir.iterdir()):
        if not filing_dir.is_dir():
            continue

        emb_path = filing_dir / "embeddings.npz"
        if not emb_path.exists():
            logger.warning(f"No embeddings found in {filing_dir}")
            continue

        data = np.load(emb_path)
        for key in data.files:
            all_embeddings[key] = data[key]

        logger.info(f"Loaded {len(data.files)} embeddings from {filing_dir.name}")

    logger.info(f"Total embeddings loaded: {len(all_embeddings)}")
    return all_embeddings


def verify_neo4j_connection() -> bool:
    """Verify Neo4j is running and accessible."""
    try:
        client = Neo4jClient()
        if client.verify_connectivity():
            logger.info("Connected to Neo4j successfully")
            return True
        else:
            logger.error("Could not connect to Neo4j")
            return False
    except Exception as e:
        logger.error(f"Neo4j connection error: {e}")
        return False


def print_summary(stats) -> None:
    """Print graph summary."""
    logger.info("\n" + "=" * 60)
    logger.info("GRAPH SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Nodes: {stats.total_nodes}")
    logger.info(f"Total Edges: {stats.total_edges}")
    logger.info(f"Connected Components: {stats.connected_components}")
    logger.info(f"Is Connected: {'YES' if stats.is_connected else 'NO'}")
    logger.info(f"Isolated Nodes: {stats.isolated_nodes}")
    logger.info(f"Bridge Edges: {stats.bridge_edges}")
    logger.info(f"Average Degree: {stats.average_degree:.2f}")

    logger.info("\nNodes by Type:")
    for node_type, count in sorted(stats.nodes_by_type.items()):
        logger.info(f"  {node_type}: {count}")

    logger.info("\nEdges by Expert:")
    for expert, count in sorted(stats.edges_by_expert.items()):
        logger.info(f"  {expert}: {count}")

    logger.info("\nEdges by Type:")
    for edge_type, count in sorted(stats.edges_by_type.items()):
        logger.info(f"  {edge_type}: {count}")

    logger.info("=" * 60)

    # Success check
    if stats.is_connected:
        logger.info("SUCCESS: Graph is fully connected!")
    else:
        logger.warning("WARNING: Graph is NOT fully connected!")


def main():
    parser = argparse.ArgumentParser(description="Build the MoE knowledge graph")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for causal extraction")
    parser.add_argument("--extract-entities", action="store_true", help="Use LLM for entity extraction")
    parser.add_argument("--skip-neo4j", action="store_true", help="Skip Neo4j export")
    parser.add_argument("--experts", type=str, help="Comma-separated list of experts to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--output-dir", type=str, default="data/graph", help="Output directory")
    args = parser.parse_args()

    setup_logging(args.verbose)

    logger.info("Starting graph construction...")

    # Step 1: Load nodes
    nodes = load_all_nodes()
    if not nodes:
        logger.error("No nodes found. Run fetch_filings.py first.")
        return 1

    # Step 2: Load embeddings
    embeddings = load_all_embeddings()
    if not embeddings:
        logger.error("No embeddings found. Run fetch_filings.py first.")
        return 1

    # Verify we have embeddings for all nodes
    nodes_with_embeddings = [n for n in nodes if n.id in embeddings]
    if len(nodes_with_embeddings) < len(nodes):
        logger.warning(
            f"Only {len(nodes_with_embeddings)}/{len(nodes)} nodes have embeddings"
        )

    # Step 3: Build graph
    expert_names = args.experts.split(",") if args.experts else None

    builder = GraphBuilder()
    nodes, edges, stats = builder.build_graph(
        nodes=nodes,
        embeddings=embeddings,
        experts=expert_names,
        use_llm=args.use_llm,
        extract_entities=args.extract_entities,
    )

    # Step 4: Save to files
    output_dir = Path(args.output_dir) / datetime.now().strftime("%Y%m%d_%H%M%S")
    builder.save_graph(nodes, edges, stats, output_dir)
    logger.info(f"Saved graph to {output_dir}")

    # Step 5: Export to Neo4j (if not skipped)
    if not args.skip_neo4j:
        if verify_neo4j_connection():
            builder.export_to_neo4j(nodes, edges, clear_existing=True)
            logger.info("Exported to Neo4j successfully")
        else:
            logger.warning("Skipping Neo4j export (connection failed)")
            logger.info("Start Neo4j with: docker-compose up -d neo4j")

    # Print summary
    print_summary(stats)

    return 0 if stats.is_connected else 1


if __name__ == "__main__":
    sys.exit(main())
