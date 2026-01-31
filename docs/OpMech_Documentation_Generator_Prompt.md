# OpMech-GraphRAG Documentation Generator Prompt

## Objective

Analyze the OpMech-GraphRAG codebase and generate a comprehensive **Word document (.docx)** that explains the entire system architecture, logic, and results. This documentation should be suitable for:
- Research paper submissions (ICAIF 2025, EMNLP 2025)
- Academic presentations
- Technical stakeholders
- Portfolio demonstration

**IMPORTANT:** Extract ALL values, statistics, code snippets, and results from the ACTUAL codebase - do not use placeholder values.

---

## Step 1: Codebase Analysis

First, analyze the codebase to extract real information:

```bash
# Find the project structure
find . -type f -name "*.py" | head -50
ls -la src/
ls -la src/opmech/
ls -la src/graph_builder/

# Find configuration files
find . -name "*.yaml" -o -name "*.json" -o -name "config*"
cat config/settings.py 2>/dev/null || cat src/config.py 2>/dev/null

# Find test files and results
find . -name "test*.py"
find . -name "*result*" -o -name "*output*"
```

### Extract Key Components

For each major component, read the source code and extract:

#### 1. Graph Statistics
```bash
# Find where graph stats are stored/computed
grep -rn "nodes" src/ --include="*.py" | grep -i "count\|total\|statistic"
grep -rn "edges" src/ --include="*.py" | grep -i "count\|total\|statistic"

# Check Neo4j queries or graph interface
cat src/opmech/graph_interface.py 2>/dev/null
cat src/graph_builder/pipeline.py 2>/dev/null
```

#### 2. Commutator Formula and Weights
```bash
# Find commutator implementation
cat src/opmech/commutator.py

# Extract weights
grep -n "w_E\|w_V\|w_A\|w_C\|delta_E\|delta_V\|delta_A\|delta_C" src/opmech/commutator.py
```

#### 3. Mode Selection Thresholds
```bash
# Find mode selection logic
cat src/opmech/mode_selection.py

# Extract thresholds
grep -n "tau_low\|tau_high\|threshold\|EXPLOIT\|ADAPTIVE\|EXPLORE" src/opmech/mode_selection.py
```

#### 4. Operator Configurations
```bash
# Find operator implementations
cat src/opmech/operators.py

# Extract edge/node preferences
grep -n "edge_preferences\|node_preferences\|HIERARCHICAL\|SEMANTIC\|FINANCIAL_LINE" src/opmech/operators.py
```

#### 5. Trust Decision Logic
```bash
# Find trust decision implementation
grep -n "TRUST_A\|TRUST_B\|MERGE\|authority\|trust" src/opmech/mode_selection.py
```

#### 6. Test Results
```bash
# Find test outputs or logs
find . -name "*.log" | head -5
cat tests/test_results.json 2>/dev/null
cat output/results.json 2>/dev/null

# Run tests if needed to capture output
python -m pytest tests/ -v 2>&1 | head -100
```

#### 7. MoE Experts
```bash
# Find expert implementations
ls src/graph_builder/experts/
cat src/graph_builder/experts/*.py | head -200
```

---

## Step 2: Document Structure

Create a Word document with the following structure:

### Title Page
- Title: "OpMech-GraphRAG: Multi-Perspective Knowledge Retrieval Through Quantum-Inspired Operator Mechanics"
- Subtitle: "Technical Documentation"
- Authors: Divyansh Maiwar Singh, Dhruvish Shah, Dharmik Kothari, Agastya Shetty
- Institution: SP Jain School of Global Management, Dubai
- Date: [Current Date]
- Key metrics box: Nodes, Edges, Mode Accuracy, Answer Quality, Trust Accuracy, Traversal Reduction

### Table of Contents

### 1. Executive Summary
- Core innovation (dual operators, commutator, mode selection)
- Key results table with ACTUAL values from test runs
- System capabilities

### 2. Problem Statement
- Limitations of traditional RAG
- Order-sensitivity in financial analysis
- The solution approach

### 3. System Architecture
- High-level architecture diagram (ASCII art or description)
- Two-phase design (Graph Construction + Query Processing)
- Component overview table

### 4. MoE Graph Construction
- Why Mixture-of-Experts
- Each of the 7 experts with:
  - Name and purpose
  - Model/technique used (from actual code)
  - Node types created
  - Edge types created
- Expert execution order
- Graph statistics table with ACTUAL values:
  - Total nodes by type
  - Total edges by type
  - Source filing info

### 5. Dual Operator Architecture
- Quantum mechanics analogy
- Operator A (Structure-First):
  - Philosophy
  - Starting point selection (actual code logic)
  - Edge preferences (actual weights from code)
  - Node preferences (actual weights from code)
- Operator B (Narrative-First):
  - Philosophy
  - Starting point selection (actual code logic)
  - Edge preferences (actual weights from code)
  - Node preferences (actual weights from code)
- Traversal algorithm
- Convergence pressure mechanism

### 6. The Commutator
- Formula with ACTUAL weights from code
- Each component (Δ_E, Δ_V, Δ_A, Δ_C):
  - Definition
  - Formula
  - What it measures
  - Example calculation
- Interpretation guide (what different Δ values mean)
- Divergence trajectory explanation

### 7. Mode Selection System
- The three modes with ACTUAL thresholds from code:
  - EXPLOIT (condition, confidence range)
  - ADAPTIVE (condition, confidence range)
  - EXPLORE (condition, confidence range)
- Mode selection triggers (from actual code)
- Dynamic hop control table

### 8. Trust Decision Framework
- The problem (wrong answer merging)
- Evidence authority hierarchy with ACTUAL weights
- Trust decision logic (from actual code)
- Trust decision types

### 9. Complete Query Processing Flow
- Step-by-step flow
- Termination conditions with ACTUAL thresholds
- Example walkthrough with ACTUAL test query results

### 10. Test Results & Validation
- Test query 1: Revenue Query
  - Query text
  - ACTUAL mode selected
  - ACTUAL confidence
  - ACTUAL hops used
  - ACTUAL trajectory values
  - ACTUAL answer
- Test query 2: Margin/Opinion Query
  - Same details
- Test query 3: Causal Query
  - Same details
- Aggregate metrics table

### 11. Technical Specifications
- Technology stack (from requirements.txt / imports)
- Hardware requirements
- Model configurations with ACTUAL values
- Threshold configurations with ACTUAL values

### 12. Novel Contributions
- Academic novelty points
- Practical applications
- Publication targets
- Future work

---

## Step 3: Generate the Document

Use docx-js to create the Word document. Here's the template:

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, BorderStyle, WidthType, ShadingType, AlignmentType,
        PageBreak, Header, Footer, PageNumber, LevelFormat } = require('docx');
const fs = require('fs');

// Color scheme
const colors = {
    primary: "1A365D",
    secondary: "2D5A87",
    accent: "4A90A4",
    highlight: "E8F4F8",
    lightGreen: "E6F4EA",
    lightOrange: "FEF3E2",
    white: "FFFFFF"
};

// REPLACE THESE WITH ACTUAL VALUES FROM CODEBASE
const ACTUAL_VALUES = {
    // Graph Statistics
    total_nodes: "EXTRACT_FROM_CODE",
    total_edges: "EXTRACT_FROM_CODE",
    node_breakdown: {
        FINANCIAL_LINE: "EXTRACT",
        TEXT_SECTION: "EXTRACT",
        NOTE: "EXTRACT",
        ENTITY: "EXTRACT"
    },
    edge_breakdown: {
        SEMANTIC: "EXTRACT",
        HIERARCHICAL: "EXTRACT",
        TEMPORAL: "EXTRACT",
        CAUSAL: "EXTRACT",
        RISK: "EXTRACT"
    },
    
    // Commutator Weights
    w_E: "EXTRACT_FROM_commutator.py",
    w_V: "EXTRACT_FROM_commutator.py",
    w_A: "EXTRACT_FROM_commutator.py",
    w_C: "EXTRACT_FROM_commutator.py",
    
    // Mode Thresholds
    tau_low: "EXTRACT_FROM_mode_selection.py",
    tau_high: "EXTRACT_FROM_mode_selection.py",
    answer_agreement_threshold: "EXTRACT",
    trust_threshold: "EXTRACT",
    
    // Operator Preferences
    operator_A_edge_prefs: "EXTRACT_FROM_operators.py",
    operator_A_node_prefs: "EXTRACT_FROM_operators.py",
    operator_B_edge_prefs: "EXTRACT_FROM_operators.py",
    operator_B_node_prefs: "EXTRACT_FROM_operators.py",
    
    // Test Results
    test1_query: "EXTRACT",
    test1_mode: "EXTRACT",
    test1_confidence: "EXTRACT",
    test1_hops: "EXTRACT",
    test1_trajectory: "EXTRACT",
    test1_answer: "EXTRACT",
    // ... same for test2, test3
    
    // Aggregate Metrics
    mode_accuracy: "EXTRACT",
    answer_quality: "EXTRACT",
    trust_accuracy: "EXTRACT",
    traversal_reduction: "EXTRACT"
};

// Build the document with actual values...
```

---

## Step 4: Specific Extraction Commands

Run these commands to get actual values:

### Graph Statistics
```python
# If there's a stats file or you can query Neo4j
from neo4j import GraphDatabase

driver = GraphDatabase.driver(uri, auth=(user, password))
with driver.session() as session:
    # Total nodes
    result = session.run("MATCH (n) RETURN count(n) as count")
    total_nodes = result.single()["count"]
    
    # Nodes by type
    result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
    node_breakdown = {r["type"]: r["count"] for r in result}
    
    # Total edges
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    total_edges = result.single()["count"]
    
    # Edges by type
    result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
    edge_breakdown = {r["type"]: r["count"] for r in result}
```

### From Python Files
```bash
# Extract commutator weights
python -c "
import ast
with open('src/opmech/commutator.py') as f:
    content = f.read()
    # Parse and extract w_E, w_V, w_A, w_C values
    print('Commutator file content:')
    print(content)
"

# Extract thresholds
python -c "
with open('src/opmech/mode_selection.py') as f:
    for line in f:
        if 'tau_low' in line or 'tau_high' in line or 'threshold' in line:
            print(line.strip())
"
```

### From Test Runs
```bash
# Run the system and capture output
python -c "
from src.opmech.system import OpMechGraphRAG
# Initialize and run test queries
system = OpMechGraphRAG(...)
result = system.query('What was Apple total revenue in FY2023?')
print(f'Mode: {result.mode}')
print(f'Confidence: {result.confidence}')
print(f'Hops: {result.hops_used}')
print(f'Trajectory: {[(t.combined, t.delta_E, t.delta_V, t.delta_A, t.delta_C) for t in result.trajectory]}')
print(f'Answer: {result.answer}')
"
```

---

## Step 5: Document Generation Code

After extracting all values, generate the document:

```javascript
// Save as generate_documentation.js
// Run with: node generate_documentation.js

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, BorderStyle, WidthType, ShadingType, AlignmentType,
        PageBreak, Header, Footer, PageNumber, LevelFormat } = require('docx');
const fs = require('fs');

// INSERT ACTUAL VALUES HERE after extraction
const V = {
    // ... all extracted values
};

// Helper functions for creating styled content
const createHeader = (level, text) => new Paragraph({
    heading: level,
    children: [new TextRun({ text, bold: true, font: "Arial" })]
});

const createParagraph = (text) => new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: 22 })]
});

const createTable = (headers, rows, colWidths) => {
    // ... table creation logic
};

// Build document
const doc = new Document({
    sections: [{
        children: [
            // Title page
            // Table of contents
            // All sections with ACTUAL values
        ]
    }]
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("OpMech_GraphRAG_Documentation.docx", buffer);
    console.log("Documentation generated!");
});
```

---

## Output Requirements

The final document should:

1. **Be professional and publication-ready**
2. **Contain ONLY real values from the codebase** - no placeholders
3. **Include actual code snippets** where relevant (formatted as code blocks)
4. **Show actual test results** with real trajectory values
5. **Have proper formatting**: tables, headers, consistent styling
6. **Be approximately 25-35 pages** when printed

---

## Validation Checklist

Before finalizing, verify:

- [ ] All node/edge counts match actual Neo4j database
- [ ] Commutator weights match `commutator.py`
- [ ] Mode thresholds match `mode_selection.py`
- [ ] Operator preferences match `operators.py`
- [ ] Test results match actual system output
- [ ] All formulas are correctly transcribed from code
- [ ] No placeholder values remain (search for "EXTRACT", "TODO", "TBD")

---

## Execution

1. Run the extraction commands to gather all actual values
2. Update the ACTUAL_VALUES object in the generation script
3. Run the document generation script
4. Review and verify all values
5. Save to `/mnt/user-data/outputs/OpMech_GraphRAG_Complete_Documentation.docx`

Good luck! The goal is a document that accurately reflects your working system with real, validated results.
