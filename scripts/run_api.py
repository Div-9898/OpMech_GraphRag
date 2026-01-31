#!/usr/bin/env python3
"""Run the MoE Graph Builder API server."""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.api import run_server


def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )


def main():
    parser = argparse.ArgumentParser(description="Run MoE Graph Builder API server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    setup_logging()

    logger.info("=" * 60)
    logger.info("MoE Graph Builder API Server")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Reload: {args.reload}")
    logger.info("")
    logger.info("Endpoints:")
    logger.info(f"  API Docs:     http://localhost:{args.port}/docs")
    logger.info(f"  ReDoc:        http://localhost:{args.port}/redoc")
    logger.info(f"  Health:       http://localhost:{args.port}/api/health")
    logger.info(f"  Graph Stats:  http://localhost:{args.port}/api/graph/stats")
    logger.info("=" * 60)

    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
