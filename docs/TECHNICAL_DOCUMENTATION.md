# MoE Graph Builder - Technical Documentation

## Overview

The MoE (Mixture-of-Experts) Graph Builder creates a knowledge graph from Apple SEC filings (10-K and 10-Q reports) using specialized expert modules that identify different types of relationships between financial data points.

**Data Source**: 12 Apple SEC filings (2022-2024)
- 3 Annual Reports (10-K): FY2022, FY2023, FY2024
- 9 Quarterly Reports (10-Q): Q1-Q3 for each year

---

## 1. Custom MoE Experts

The system uses **6 custom expert modules** plus a **ConnectivityEnforcer**:

| Expert | Purpose | Algorithm Type |
|--------|---------|----------------|
| CrossReferenceHunter | Detect explicit document references | Regex Pattern Matching |
| CausalChainBuilder | Identify cause-effect relationships | Regex + LLM (optional) |
| TemporalLinker | Connect same metrics across time | XBRL Tag Matching + Embeddings |
| TableTextConnector | Link tables to explanatory text | Numeric Matching + Embeddings |
| SemanticBridge | Connect semantically similar content | Cosine Similarity |
| EntityExtractor | Extract named entities using LLM | LLM-based Extraction |
| ConnectivityEnforcer | Ensure single connected component | BFS + Bridge Edges |

---

## 2. Expert Implementations

### 2.1 CrossReferenceHunter

**Location**: `src/experts/cross_reference.py`

**Purpose**: Detects explicit cross-references in SEC filings like "See Note 3", "refer to Item 7", etc.

**Algorithm**:
1. Regex patterns to detect reference phrases:
   - Note references: `See Note X`, `Refer to Note X`
   - Item references: `See Item X`, `discussed in Item X`
   - Part references: `Part I, Item X`
   - Section references: `as discussed in "X" section`
   - Table references: `see the following table`

2. Resolution: Maps reference to actual target node (same filing preferred)

3. Confidence calculation:
   - Note references: **0.95** (highest - explicit)
   - Item references: **0.90**
   - Section references: **0.75**
   - Table references: **0.70**
   - Same filing bonus: **+0.05**

**Edge Types Created**: `REFERS_TO`, `EXPLAINS`

---

### 2.2 CausalChainBuilder

**Location**: `src/experts/causal.py`

**Purpose**: Identifies cause-effect relationships in financial text.

**Algorithm**:
1. **Pattern-based extraction** (default):
   - Forward causal connectors: "resulted in", "led to", "caused", "drove", "contributed to"
   - Backward causal connectors: "due to", "because of", "driven by", "attributed to"

2. **LLM-based extraction** (optional):
   - Uses Qwen2.5-7B to extract complex causal relationships
   - Returns structured JSON with cause, effect, evidence, confidence

3. Sentence splitting at causal connectors to identify cause/effect spans

**Edge Types Created**: `CAUSED_BY`, `LEADS_TO`

**Confidence**: 0.75 (pattern-based), variable (LLM-based)

---

### 2.3 TemporalLinker

**Location**: `src/experts/temporal.py`

**Purpose**: Connects the same financial metrics across different time periods.

**Algorithm**:
1. **XBRL Tag Matching**: Link nodes with identical XBRL tags across periods
   - Confidence: **0.95** (exact match)

2. **Note Number Matching**: Link same-numbered notes across filings
   - Confidence: **0.90**

3. **Section Matching**: Link same-named sections (verified with embeddings)
   - Confidence: cosine similarity score (threshold: 0.7)

4. **Embedding Similarity**: High-similarity nodes across consecutive periods
   - Confidence: cosine similarity score (threshold: 0.90)

**Period Order**: Q1-2022 → Q2-2022 → Q3-2022 → FY2022 → Q1-2023 → ...

**Edge Types Created**: `TEMPORAL_NEXT`

---

### 2.4 TableTextConnector

**Location**: `src/experts/table_text.py`

**Purpose**: Connects financial tables/line items to explanatory text.

**Algorithm**:
1. **Numeric Value Matching**:
   - Extract numbers from text (with scale: billion, million, thousand)
   - Match to table values within 5% tolerance
   - Confidence: **0.85**

2. **XBRL Concept Matching**:
   - Parse XBRL tag names (CamelCase → keywords)
   - Match to text containing those keywords
   - Verify with embedding similarity (threshold: 0.6)
   - Confidence: (keyword_ratio + similarity) / 2

3. **Embedding Similarity**:
   - Same-filing semantic similarity matching
   - Threshold: 0.80
   - Confidence: similarity score

**Edge Types Created**: `EXPLAINS_LINE_ITEM`, `DISCUSSES`

---

### 2.5 SemanticBridge

**Location**: `src/experts/semantic.py`

**Purpose**: Creates edges between semantically similar content (fallback connector).

**Algorithm**:
1. **Within-Filing Similarity**:
   - Compute pairwise cosine similarity matrix
   - Link nodes above threshold (0.85)
   - Max 5 edges per node
   - Skip adjacent nodes (likely already connected)

2. **Cross-Filing Similarity**:
   - Compare same-type nodes across different filings
   - Find best match for each node
   - Threshold: 0.85

**Edge Types Created**: `SEMANTICALLY_SIMILAR`

**Confidence**: cosine similarity score

---

### 2.6 EntityExtractor (LLM-based)

**Location**: `src/experts/entity_extractor.py`

**Purpose**: Extracts named entities from text using LLM and creates entity nodes.

**Entity Types**:
- `COMPANY`: Apple subsidiaries, suppliers, competitors
- `PRODUCT`: iPhone, Mac, iPad, Apple Watch, Services
- `SEGMENT`: Americas, Europe, Greater China, Japan
- `PERSON`: Key executives
- `FINANCIAL_METRIC`: Revenue, Net Income, EPS
- `RISK_FACTOR`: Identified risks
- `REGULATION`: GAAP, GDPR, ASC 606

**Algorithm**:
1. Process TEXT_SECTION and NOTE nodes
2. Send text to LLM with extraction prompt
3. Parse JSON response for entities
4. Create ENTITY nodes with unique IDs
5. Create edges from source nodes to entities
6. Create entity-to-entity edges for co-occurrence

**Edge Types Created**: `MENTIONS_ENTITY`, `ENTITY_RELATED_TO`

**Confidence**:
- Mention edges: **0.85**
- Entity relationship edges: **0.70**

---

### 2.7 ConnectivityEnforcer

**Location**: `src/graph/connectivity.py`

**Purpose**: Ensures the graph forms a single connected component.

**Algorithm**:
1. Find all connected components using BFS
2. While multiple components exist:
   - Sample nodes from largest components
   - Find most similar pair across components
   - Add BRIDGE edge connecting them
   - Merge components
3. Verify final connectivity

**Edge Types Created**: `BRIDGE`

**Confidence**: cosine similarity score (forced connections get 0.5 minimum)

---

## 3. Node and Edge Creation

### Node Types

| Type | Description | Source |
|------|-------------|--------|
| `FINANCIAL_LINE` | Quantitative financial data | XBRL/Tables |
| `TEXT_SECTION` | Narrative text sections | HTML Parser |
| `NOTE` | Financial statement notes | HTML Parser |
| `TABLE_ROW` | Individual table rows | HTML Parser |
| `ENTITY` | Extracted named entities | LLM |

### Node Creation Process

```
SEC Filing (HTML)
    ↓
HTML Parser → Extract sections, tables, notes
    ↓
XBRL Processor → Extract tagged financial data
    ↓
Node objects created with:
  - id: {filing_id}_{type}_{index}
  - type: NodeType enum
  - text: Raw text content
  - metadata: Filing ID, period, section, XBRL tag, value, etc.
    ↓
Embedding Engine (FinBERT) → 768-dim embeddings
```

### Edge Types

| Edge Type | Description | Created By |
|-----------|-------------|------------|
| `REFERS_TO` | Explicit reference | CrossReferenceHunter |
| `EXPLAINS` | Explanation relationship | CrossReferenceHunter |
| `CAUSED_BY` | Causal (backward) | CausalChainBuilder |
| `LEADS_TO` | Causal (forward) | CausalChainBuilder |
| `TEMPORAL_NEXT` | Same metric over time | TemporalLinker |
| `EXPLAINS_LINE_ITEM` | Text explains number | TableTextConnector |
| `DISCUSSES` | Text discusses topic | TableTextConnector |
| `SEMANTICALLY_SIMILAR` | Similar content | SemanticBridge |
| `MENTIONS_ENTITY` | Text mentions entity | EntityExtractor |
| `ENTITY_RELATED_TO` | Entity co-occurrence | EntityExtractor |
| `BRIDGE` | Connectivity edge | ConnectivityEnforcer |

### Edge Attributes

Every edge contains:
```python
Edge(
    id: str,              # Unique identifier
    source_id: str,       # Source node ID
    target_id: str,       # Target node ID
    edge_type: EdgeType,  # Type enum
    confidence: float,    # 0.0 - 1.0
    expert: str,          # Which expert created it
    evidence: str,        # Supporting text (max 500 chars)
    metadata: {
        created_at: datetime,
        algorithm: str,     # e.g., "regex_pattern", "embedding_similarity"
        forced: bool,       # True for forced bridge edges
        ...                 # Expert-specific metadata
    }
)
```

---

## 4. LLM Prompts

### Entity Extraction Prompt

**System Prompt**:
```
You are an expert at extracting named entities from Apple SEC filings.
Your task is to identify important entities in financial text.

Entity Types:
- COMPANY: Companies (Apple subsidiaries, suppliers, competitors, partners)
- PRODUCT: Products and services (iPhone, Mac, iPad, Apple Watch, Services, AppleCare)
- SEGMENT: Business or geographic segments (Americas, Europe, Greater China, Japan, Rest of Asia Pacific)
- PERSON: Key executives or board members mentioned by name
- FINANCIAL_METRIC: Specific financial metrics (Revenue, Net Income, Gross Margin, EPS)
- RISK_FACTOR: Identified business risks
- REGULATION: Laws, regulations, accounting standards (GAAP, ASC 606, GDPR)

For each entity, output a JSON object with:
- "name": The entity name (use canonical names, e.g., "iPhone" not "iPhones")
- "type": One of the entity types above
- "context": Brief context (1 sentence) about the entity from the text

Output a JSON array. If no entities found, output [].
Only extract clearly identifiable entities, not generic terms.
```

**User Prompt**:
```
Extract entities from this Apple SEC filing text:

---
{node.text[:3000]}
---

Output entities as a JSON array:
```

### Causal Extraction Prompt

**System Prompt**:
```
You are an expert at extracting causal relationships from financial text.
Your task is to identify cause-effect relationships in SEC filings.

For each causal relationship found, output a JSON object with:
- "cause": The cause/driver (brief phrase)
- "effect": The effect/result (brief phrase)
- "evidence": The exact quote from the text showing the relationship
- "confidence": Your confidence score (0.0 to 1.0)
- "direction": Either "forward" (cause leads to effect) or "backward" (effect caused by cause)

Output a JSON array of relationships. If no causal relationships are found, output an empty array [].
Only extract explicit causal relationships, not correlations or coincidences.
```

---

## 5. Graph Statistics

### Current Graph Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 1,678 |
| **Total Edges** | 22,387 |
| **Connected Components** | 1 (fully connected) |
| **Isolated Nodes** | 0 |
| **Average Degree** | 26.7 |
| **Max Degree** | 413 |
| **Min Degree** | 1 |
| **Bridge Edges** | 2 |

### Nodes by Type

| Type | Count |
|------|-------|
| FINANCIAL_LINE | 963 |
| ENTITY | 454 |
| NOTE | 163 |
| TEXT_SECTION | 98 |

### Edges by Expert

| Expert | Count |
|--------|-------|
| EntityExtractor | 8,514 |
| TableTextConnector | 7,889 |
| SemanticBridge | 5,281 |
| TemporalLinker | 620 |
| CausalChainBuilder | 41 |
| CrossReferenceHunter | 40 |
| ConnectivityEnforcer | 2 |

### Accuracy Assessment

**Confidence Distribution by Expert**:

| Expert | Confidence Range | Notes |
|--------|-----------------|-------|
| CrossReferenceHunter | 0.75 - 0.95 | High confidence for explicit references |
| TemporalLinker | 0.70 - 0.95 | High for XBRL matches, variable for embeddings |
| TableTextConnector | 0.63 - 0.85 | Based on numeric/keyword/embedding match |
| SemanticBridge | 0.85 - 0.95 | Only high-similarity edges included |
| EntityExtractor | 0.70 - 0.85 | LLM extraction with co-occurrence |
| CausalChainBuilder | 0.75 | Pattern-based extraction |
| ConnectivityEnforcer | 0.50+ | Minimum for forced bridges |

---

## 6. Metadata Storage

### Node Metadata Schema

```python
NodeMetadata(
    filing_id: str,       # "AAPL-10-K-FY2024"
    period: str,          # "FY2024", "Q1-2024"
    section: str,         # "Item 7", "Note 3"
    xbrl_tag: str,        # "us-gaap:Revenues"
    value: float,         # 383300000000 (numeric value)
    unit: str,            # "USD", "shares"
    source_file: str,     # Original filename
    char_offset: int,     # Position in document
    table_id: str,        # For TABLE_ROW nodes
    row_index: int,       # Table row number
    note_number: int,     # For NOTE nodes
    entity_type: str,     # For ENTITY nodes ("COMPANY", "PRODUCT", etc.)
)
```

### Edge Metadata Schema

```python
EdgeMetadata(
    created_at: datetime,      # Timestamp
    filing_id: str,            # Source filing
    algorithm: str,            # "regex_pattern", "embedding_similarity", etc.
    score_breakdown: dict,     # Component scores
    forced: bool,              # True for forced bridge edges
)
```

### Confidence Scoring

Every edge has a `confidence` score (0.0 - 1.0):

- **0.95**: Exact XBRL tag match, explicit Note references
- **0.90**: Item/Part references, Note number matches
- **0.85**: Numeric value matches (5% tolerance), entity mentions
- **0.75-0.85**: Section matches, embedding similarity
- **0.70**: Entity co-occurrence, table references
- **0.50-0.70**: Forced bridge edges

---

## 7. Graph RAG Working

### Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────┐
│  1. SEARCH: Query Neo4j Graph       │
│     - Text search on node content   │
│     - Filter by node type           │
│     - Follow relationships          │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  2. RETRIEVE: Gather Context        │
│     - Financial line items          │
│     - Related text sections         │
│     - Connected notes               │
│     - Temporal data (trends)        │
│     - Entity relationships          │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  3. AUGMENT: Format for LLM         │
│     - Structure retrieved data      │
│     - Include source citations      │
│     - Add temporal context          │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  4. GENERATE: LLM Answer            │
│     - Local vLLM (Qwen2.5-7B)       │
│     - System prompt for analysis    │
│     - Grounded in retrieved context │
└─────────────────────────────────────┘
     │
     ▼
  Answer with citations
```

### Query Flow

1. **Question Analysis**: Extract keywords (revenue, margin, risk, etc.)
2. **Graph Search**:
   - Match keywords against node text
   - Filter by node type (FINANCIAL_LINE for numbers, TEXT_SECTION for narrative)
   - Same-filing relationships first
3. **Context Expansion**:
   - Follow TEMPORAL_NEXT edges for trends
   - Follow EXPLAINS_LINE_ITEM for explanations
   - Include ENTITY nodes for context
4. **LLM Generation**:
   - Format context with source attributions
   - Generate analysis grounded in SEC filing data

### Example Query

```
Q: "What was Apple's revenue trend from 2022 to 2024?"

Search:
  - FINANCIAL_LINE nodes containing "net sales" or "revenue"
  - Follow TEMPORAL_NEXT edges to get time series

Context Retrieved:
  - Net Sales: $394.33B (FY2022)
  - Net Sales: $383.29B (FY2023)
  - Net Sales: $391.04B (FY2024)

LLM Output:
  "Apple's revenue showed fluctuation over the period:
   - FY2022: $394.33B (peak)
   - FY2023: $383.29B (-2.8% YoY decline)
   - FY2024: $391.04B (+2.0% recovery)
   Source: AAPL-10-K filings"
```

---

## 8. Final Outputs

### Graph Database (Neo4j)

- **URL**: `bolt://localhost:7687`
- **Browser**: `http://localhost:7474`
- **Credentials**: neo4j / password123

### File Outputs

```
data/
├── raw/                    # Raw SEC filings
│   └── 0000320193/         # Apple CIK
│       ├── metadata.json
│       └── {accession}/    # Each filing
├── parsed/                 # Parsed filing data
│   └── AAPL-10-K-FY2024/
│       ├── nodes.jsonl
│       ├── embeddings.npz
│       └── metadata.json
└── graph/                  # Final graph
    ├── nodes.jsonl         # All nodes
    ├── edges.jsonl         # All edges
    └── stats.json          # Graph statistics
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/graph` | GET | Get nodes and edges |
| `/api/graph/stats` | GET | Graph statistics |
| `/api/nodes/{id}` | GET | Node details |
| `/api/nodes/{id}/neighbors` | GET | Node neighbors |
| `/api/path` | GET | Shortest path |
| `/api/filter` | POST | Filter graph |
| `/api/search` | POST | Text search |
| `/api/experts` | GET | Expert statistics |

### Frontend Visualization

- **2D View**: Sigma.js with circular layout by node type
- **3D View**: Three.js force-directed graph
- **Features**:
  - Node coloring by type
  - Edge coloring by expert
  - Click for node details
  - Filter by expert/type
  - Path highlighting

---

## Summary

The MoE Graph Builder creates a fully connected knowledge graph from Apple SEC filings using 6 specialized experts that identify different relationship types. The graph contains **1,678 nodes** and **22,387 edges** with confidence scores for each edge. The system supports Graph RAG queries using a local LLM (Qwen2.5-7B) for fundamental analysis questions grounded in the SEC filing data.
