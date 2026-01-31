#!/usr/bin/env python3
"""
Fetch and process Apple SEC filings.

This script downloads all target filings (3x 10-K + 9x 10-Q for 2022-2024),
parses them to extract nodes, and generates embeddings.

Usage:
    python scripts/fetch_filings.py [--skip-download] [--skip-embeddings]
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.config import settings
from src.ingestion.embedding_engine import EmbeddingEngine
from src.ingestion.html_parser import HTMLParser
from src.ingestion.sec_fetcher import SECFetcher
from src.ingestion.xbrl_processor import XBRLProcessor, fetch_and_process_company_facts
from src.models import Node, NodeType


def setup_logging(verbose: bool = False):
    """Configure logging."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


def fetch_filings(skip_download: bool = False) -> list[tuple]:
    """Fetch all target filings from SEC EDGAR."""
    if skip_download:
        logger.info("Skipping download, using cached filings")
        # Load from cache
        results = []
        raw_dir = settings.raw_dir / settings.apple_cik
        if raw_dir.exists():
            for filing_dir in raw_dir.iterdir():
                if filing_dir.is_dir():
                    meta_path = filing_dir / "metadata.json"
                    doc_path = filing_dir / "filing.html"
                    if meta_path.exists() and doc_path.exists():
                        from src.models import Filing
                        filing = Filing.model_validate_json(meta_path.read_text())
                        results.append((filing, doc_path))
        logger.info(f"Found {len(results)} cached filings")
        return results

    logger.info("Fetching filings from SEC EDGAR...")
    fetcher = SECFetcher()
    return fetcher.download_all_filings()


def parse_filings(filings: list[tuple]) -> dict[str, list[Node]]:
    """Parse all filings to extract nodes."""
    logger.info("Parsing filings to extract nodes...")

    all_nodes = {}

    for filing, doc_path in filings:
        filing_id = f"AAPL-{filing.filing_type}-{filing.period.replace('-', '')}"
        logger.info(f"Parsing {filing_id}...")

        # Parse HTML
        parser = HTMLParser(filing_id, filing.period)
        nodes = parser.parse_file(doc_path)

        # Add XBRL financial line items
        xbrl_processor = XBRLProcessor(filing_id, filing.period)

        # Try to load company facts (cached or fresh)
        cache_path = settings.raw_dir / "company_facts.json"
        if cache_path.exists():
            company_facts = json.loads(cache_path.read_text())
            xbrl_nodes = xbrl_processor.process_company_facts(company_facts)
            nodes.extend(xbrl_nodes)

        all_nodes[filing_id] = nodes

        # Log stats
        type_counts = {}
        for node in nodes:
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        logger.info(f"  Extracted {len(nodes)} nodes: {type_counts}")

    return all_nodes


def save_nodes(all_nodes: dict[str, list[Node]]) -> None:
    """Save parsed nodes to JSON files."""
    logger.info("Saving parsed nodes...")

    for filing_id, nodes in all_nodes.items():
        output_dir = settings.parsed_dir / filing_id
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "nodes.jsonl"
        with open(output_path, "w") as f:
            for node in nodes:
                f.write(node.model_dump_json() + "\n")

        logger.info(f"  Saved {len(nodes)} nodes to {output_path}")


def load_nodes(filing_id: str = None) -> dict[str, list[Node]]:
    """Load nodes from JSON files."""
    all_nodes = {}

    if filing_id:
        dirs = [settings.parsed_dir / filing_id]
    else:
        dirs = list(settings.parsed_dir.iterdir())

    for node_dir in dirs:
        if not node_dir.is_dir():
            continue

        nodes_path = node_dir / "nodes.jsonl"
        if not nodes_path.exists():
            continue

        nodes = []
        with open(nodes_path, "r") as f:
            for line in f:
                node = Node.model_validate_json(line)
                nodes.append(node)

        all_nodes[node_dir.name] = nodes

    return all_nodes


def generate_embeddings(all_nodes: dict[str, list[Node]], skip: bool = False) -> dict[str, dict]:
    """Generate embeddings for all nodes."""
    if skip:
        logger.info("Skipping embedding generation")
        return {}

    logger.info("Generating embeddings...")
    engine = EmbeddingEngine()

    all_embeddings = {}

    for filing_id, nodes in all_nodes.items():
        logger.info(f"Generating embeddings for {filing_id} ({len(nodes)} nodes)...")

        embeddings = engine.embed_nodes(nodes, show_progress=True)

        # Save embeddings
        output_path = settings.embeddings_dir / filing_id / "embeddings.npz"
        engine.save_embeddings(embeddings, output_path)

        all_embeddings[filing_id] = embeddings

    # Cleanup
    engine.unload()

    return all_embeddings


def print_summary(all_nodes: dict[str, list[Node]]) -> None:
    """Print summary statistics."""
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    total_nodes = 0
    type_totals = {t: 0 for t in NodeType}

    for filing_id, nodes in sorted(all_nodes.items()):
        total_nodes += len(nodes)
        for node in nodes:
            type_totals[node.type] += 1

        logger.info(f"  {filing_id}: {len(nodes)} nodes")

    logger.info("-" * 60)
    logger.info(f"Total filings: {len(all_nodes)}")
    logger.info(f"Total nodes: {total_nodes}")
    logger.info("\nBy type:")
    for node_type, count in type_totals.items():
        logger.info(f"  {node_type.value}: {count}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Fetch and process Apple SEC filings")
    parser.add_argument("--skip-download", action="store_true", help="Skip downloading filings")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip generating embeddings")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Ensure directories exist
    settings.ensure_dirs()

    # Step 1: Fetch filings
    filings = fetch_filings(skip_download=args.skip_download)

    if not filings:
        logger.error("No filings found!")
        return 1

    # Step 2: Fetch company facts for XBRL data
    logger.info("Fetching XBRL company facts...")
    try:
        fetch_and_process_company_facts("dummy", "dummy")  # Just to cache the data
    except Exception as e:
        logger.warning(f"Could not fetch company facts: {e}")

    # Step 3: Parse filings to extract nodes
    all_nodes = parse_filings(filings)

    # Step 4: Save nodes
    save_nodes(all_nodes)

    # Step 5: Generate embeddings
    generate_embeddings(all_nodes, skip=args.skip_embeddings)

    # Step 6: Print summary
    print_summary(all_nodes)

    logger.info("\nData ingestion complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
