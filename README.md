# OpMech-GraphRAG: Operator Mechanics for Financial Document Analysis

A novel Graph-based Retrieval Augmented Generation (GraphRAG) system for analyzing SEC financial filings using dual-operator architecture and commutator-based consistency checking.

## Overview

OpMech-GraphRAG introduces a unique approach to financial document understanding by treating information retrieval as a physics-inspired operator mechanics problem. The system uses two complementary operators that traverse a knowledge graph from different starting points, with a commutator measuring their divergence to ensure answer consistency.

### Key Innovation: The "Two Detectives" Approach

- **Operator A (Structure-First)**: Starts from quantitative financial data (XBRL tags, financial line items) and traverses toward narrative explanations
- **Operator B (Narrative-First)**: Starts from qualitative text (MD&A, Risk Factors, Notes) and traverses toward supporting numbers
- **Commutator**: Measures divergence between operators - when both "detectives" agree, we have high confidence in the answer

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpMech-GraphRAG System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  SEC EDGAR   │───▶│  ETL Pipeline │───▶│   MoE Graph  │       │
│  │   Filings    │    │  (Ingestion)  │    │   Builder    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                  │               │
│                                                  ▼               │
│                                          ┌──────────────┐       │
│                                          │   Neo4j      │       │
│                                          │  Knowledge   │       │
│                                          │    Graph     │       │
│                                          └──────────────┘       │
│                                                  │               │
│                      ┌───────────────────────────┼───────────┐  │
│                      │                           │           │  │
│                      ▼                           ▼           │  │
│               ┌──────────────┐           ┌──────────────┐    │  │
│               │  Operator A  │           │  Operator B  │    │  │
│               │  (Numbers →  │           │  (Narrative  │    │  │
│               │   Narrative) │           │   → Numbers) │    │  │
│               └──────────────┘           └──────────────┘    │  │
│                      │                           │           │  │
│                      └─────────────┬─────────────┘           │  │
│                                    ▼                         │  │
│                            ┌──────────────┐                  │  │
│                            │  Commutator  │                  │  │
│                            │  (Δ = w_E·Δ_E│                  │  │
│                            │  + w_V·Δ_V   │                  │  │
│                            │  + w_A·Δ_A   │                  │  │
│                            │  + w_C·Δ_C)  │                  │  │
│                            └──────────────┘                  │  │
│                                    │                         │  │
│                                    ▼                         │  │
│                            ┌──────────────┐                  │  │
│                            │    Trust     │                  │  │
│                            │   Decision   │                  │  │
│                            └──────────────┘                  │  │
│                                                              │  │
└──────────────────────────────────────────────────────────────┘  │
```

## Features

### Mixture of Experts (MoE) Graph Construction

Five specialized experts discover different types of relationships in financial documents:

| Expert | Edge Types | Description |
|--------|-----------|-------------|
| **TemporalLinker** | `TEMPORAL_NEXT` | Links same entities across time periods (FY2022 → FY2023 → FY2024) |
| **SemanticBridge** | `SEMANTICALLY_SIMILAR`, `BRIDGE` | Connects semantically related content, ensures graph connectivity |
| **CausalChainBuilder** | `CAUSED_BY`, `LEADS_TO` | Identifies cause-effect relationships ("Revenue increased due to...") |
| **CrossReferenceHunter** | `REFERS_TO`, `EXPLAINS` | Detects explicit cross-references ("See Note 3", "as discussed in Item 7") |
| **TableTextConnector** | `EXPLAINS_LINE_ITEM`, `DISCUSSES` | Links table data to explanatory text |

### Commutator-Based Consistency

The commutator measures divergence between operator outputs:

```
Δ(q, h) = w_E · Δ_E + w_V · Δ_V + w_A · Δ_A + w_C · Δ_C
```

Where:
- **Δ_E** (Evidence Divergence): Jaccard distance between retrieved node sets
- **Δ_V** (Structural Divergence): Difference in document sections/types covered
- **Δ_A** (Answer Divergence): Cosine distance between answer embeddings
- **Δ_C** (Confidence Divergence): Difference in traversal path confidence

Default weights: `w_E = 0.30, w_V = 0.20, w_A = 0.30, w_C = 0.20`

### ETL Pipeline

Complete ingestion pipeline for SEC filings:

1. **SEC Fetcher**: Downloads 10-K and 10-Q filings from EDGAR API
2. **HTML Parser**: Extracts structured content (sections, tables, notes)
3. **XBRL Processor**: Extracts financial line items with US-GAAP tags
4. **Embedding Engine**: Generates FinBERT embeddings for semantic similarity

## Tech Stack

- **Backend**: Python 3.12+, FastAPI
- **Graph Database**: Neo4j
- **Embeddings**: FinBERT (ProsusAI/finbert)
- **LLM**: Qwen2.5-7B-Instruct (via vLLM)
- **Frontend**: Next.js 15, React, TypeScript, Tailwind CSS, Framer Motion
- **3D Visualization**: Three.js / React Three Fiber

## Installation

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- CUDA-capable GPU (recommended for embeddings and LLM)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Div-9898/OpMech_GraphRag.git
   cd OpMech_GraphRag
   ```

2. **Create Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate  # Windows
   pip install -e .
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start Neo4j**
   ```bash
   docker-compose up -d neo4j
   ```

5. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

## Usage

### Build the Knowledge Graph

```bash
# Fetch SEC filings for a company
python scripts/fetch_filings.py --ticker AAPL

# Build the graph
python scripts/build_graph.py --ticker AAPL --use-llm
```

### Start the System

```bash
# Start all services
./start_demo.sh

# Or start individually:
# Terminal 1: Start vLLM server
./scripts/start_vllm.sh

# Terminal 2: Start API server
python scripts/run_api.py

# Terminal 3: Start frontend
cd frontend && npm run dev
```

### Query the System

```python
from src.opmech.system import OpMechSystem

system = OpMechSystem()
result = system.query("What drove Apple's revenue growth in FY2024?")

print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
print(f"Commutator Δ: {result.commutator.combined}")
```

## Project Structure

```
OpMech_GraphRag/
├── src/
│   ├── api/              # FastAPI routes and schemas
│   ├── core/             # Core system integration
│   ├── experts/          # MoE expert implementations
│   │   ├── temporal.py   # TemporalLinker
│   │   ├── semantic.py   # SemanticBridge
│   │   ├── causal.py     # CausalChainBuilder
│   │   ├── cross_reference.py  # CrossReferenceHunter
│   │   └── table_text.py # TableTextConnector
│   ├── graph/            # Neo4j client and graph builder
│   ├── ingestion/        # ETL pipeline components
│   │   ├── sec_fetcher.py
│   │   ├── html_parser.py
│   │   ├── xbrl_processor.py
│   │   └── embedding_engine.py
│   ├── opmech/           # Operator mechanics core
│   │   ├── operators.py  # OperatorA and OperatorB
│   │   ├── commutator.py # Divergence computation
│   │   ├── controller.py # Traversal strategy
│   │   └── system.py     # Main system orchestration
│   └── processing/       # Answer synthesis and calibration
├── frontend/             # Next.js frontend application
├── scripts/              # CLI tools and utilities
├── tests/                # Test suite
├── docs/                 # Documentation
└── docker-compose.yml    # Service definitions
```

## Configuration

Key configuration options in `src/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `neo4j_uri` | `bolt://localhost:7687` | Neo4j connection URI |
| `neo4j_password` | `password123` | Neo4j password |
| `vllm_model` | `Qwen/Qwen2.5-7B-Instruct` | LLM model for generation |
| `finbert_model` | `ProsusAI/finbert` | Embedding model |
| `temporal_similarity_threshold` | `0.90` | Threshold for temporal linking |
| `semantic_similarity_threshold` | `0.85` | Threshold for semantic bridges |
| `causal_confidence_threshold` | `0.50` | Threshold for causal edges |

## Limitations

1. **Context Window Constraint**: Maximum 4,096 tokens per evidence context
2. **Fixed Hop Limit**: Maximum 6 hops in graph traversal
3. **Single Company Focus**: Currently optimized for single-company analysis

## Team

- **Divyansh Maiwar Singh** - Lead Developer
- **Dharmik Kothari** - ML Engineer
- **Agastya Shetty** - Research Engineer
- **Dhruvish Shah** - Data Engineer

## Acknowledgments

- SEC EDGAR for providing public access to financial filings
- Hugging Face for the FinBERT model
- The Neo4j team for their excellent graph database

---

**Note**: Source-available for review — all rights reserved until a license is assigned.
