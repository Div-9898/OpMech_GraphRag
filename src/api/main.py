"""FastAPI application for MoE Graph Builder API."""

import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routes import router, set_neo4j_client, query_opmech
from src.api.schemas import QueryRequest, QueryResponse
from src.config import settings
from src.graph.neo4j_client import Neo4jClient


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)


# Global Neo4j client
_neo4j_client: Neo4jClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    global _neo4j_client

    # Startup
    logger.info("Starting MoE Graph Builder API...")

    try:
        _neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        set_neo4j_client(_neo4j_client)
        logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.warning("API will run in degraded mode without database")

    yield

    # Shutdown
    logger.info("Shutting down MoE Graph Builder API...")
    if _neo4j_client:
        _neo4j_client.close()
        logger.info("Closed Neo4j connection")


# Create FastAPI app
app = FastAPI(
    title="MoE Graph Builder API",
    description="""
    API for the Mixture-of-Experts Knowledge Graph Builder.

    This API provides access to a knowledge graph constructed from Apple SEC filings
    using a Mixture-of-Experts architecture with 5 specialized experts:

    - **CrossReferenceHunter**: Detects explicit references (e.g., "See Note 3")
    - **CausalChainBuilder**: Extracts cause-effect relationships
    - **TemporalLinker**: Links the same concepts across time periods
    - **TableTextConnector**: Connects table data with explanatory text
    - **SemanticBridge**: Creates semantic similarity edges

    ## Features

    - Graph exploration with filtering
    - Shortest path finding
    - Text search across nodes
    - Real-time updates via WebSocket
    - Expert-level statistics
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "OpMech-GraphRAG API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "graph_stats": "/api/graph/stats",
        "query": "/query",
    }


# Root-level query endpoint (for frontend compatibility)
@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def root_query(request: QueryRequest) -> QueryResponse:
    """
    Process a query using the OpMech-GraphRAG system.

    This is the main endpoint for the frontend demo.
    """
    return await query_opmech(request)


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """Run the API server."""
    import uvicorn

    logger.info(f"Starting server at http://{host}:{port}")
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run MoE Graph Builder API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()
    run_server(host=args.host, port=args.port, reload=args.reload)
