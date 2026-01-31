"""Data ingestion module for SEC filings."""

from src.ingestion.embedding_engine import EmbeddingEngine, compute_cosine_similarity, find_similar_nodes
from src.ingestion.html_parser import HTMLParser, parse_filing
from src.ingestion.sec_fetcher import SECFetcher, fetch_apple_filings
from src.ingestion.xbrl_processor import XBRLProcessor, fetch_and_process_company_facts

__all__ = [
    "SECFetcher",
    "fetch_apple_filings",
    "HTMLParser",
    "parse_filing",
    "XBRLProcessor",
    "fetch_and_process_company_facts",
    "EmbeddingEngine",
    "compute_cosine_similarity",
    "find_similar_nodes",
]
