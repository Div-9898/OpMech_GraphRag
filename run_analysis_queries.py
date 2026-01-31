#!/usr/bin/env python3
"""
Strategic Analysis Queries for OpMech-GraphRAG System.

This script runs 5 strategic analysis queries and generates a comprehensive
evaluation report in the same format as OpMech_GraphRAG_Evaluation_Report.md
Also saves complete execution logs.
"""

import json
import sys
import time
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from loguru import logger

# Configure logging - both to file and stderr
LOG_FILE = f"strategic_analysis_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
logger.add(LOG_FILE, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")


def check_vllm_availability(vllm_url: str) -> bool:
    """Check if vLLM server is available."""
    import requests
    try:
        response = requests.get(f"{vllm_url}/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            logger.info(f"vLLM available with models: {models}")
            return True
    except Exception as e:
        logger.warning(f"vLLM not available: {e}")
    return False


def run_strategic_queries():
    """Run strategic analysis queries and generate evaluation report."""

    logger.info("=" * 80)
    logger.info("Starting OpMech-GraphRAG Strategic Analysis")
    logger.info("=" * 80)
    logger.info(f"Log file: {LOG_FILE}")

    # Setup company configuration
    logger.info("Setting up company configuration...")
    from src.company_config import CompanyConfig, set_active_company
    config = CompanyConfig.from_ticker("AAPL")
    set_active_company(config)
    logger.info(f"Active company: {config.name} ({config.ticker})")

    # Initialize system
    logger.info("Initializing OpMech-GraphRAG system...")
    vllm_url = "http://localhost:8001/v1"
    logger.info(f"Using vLLM at: {vllm_url}")

    if not check_vllm_availability(vllm_url):
        logger.error("vLLM server not available. Please start it first.")
        return

    from src.core.integrated_system import IntegratedOpMechSystem

    system = IntegratedOpMechSystem(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        vllm_url=vllm_url,
        company="AAPL",
        tau_low=0.25,
        tau_high=0.60,
        max_hops=6
    )

    logger.info("Using IntegratedOpMechSystem (full pipeline with ground-truth-first)")
    system_type = "IntegratedOpMechSystem"

    # Strategic queries with categories
    queries = [
        {
            "query": "Is the company's growth sustainable?",
            "category": "Growth Sustainability Analysis"
        },
        {
            "query": "How has profitability changed and why?",
            "category": "Profitability Trend Analysis"
        },
        {
            "query": "Which business segment is most concerning?",
            "category": "Segment Risk Analysis"
        },
        {
            "query": "What's driving the change in operating performance?",
            "category": "Operating Performance Analysis"
        },
        {
            "query": "Should investors be worried about the balance sheet?",
            "category": "Balance Sheet Risk Assessment"
        }
    ]

    results = []
    total_start = time.time()

    logger.info("=" * 80)
    logger.info(f"RUNNING {len(queries)} STRATEGIC ANALYSIS QUERIES")
    logger.info("=" * 80)

    for i, q in enumerate(queries, 1):
        query = q["query"]
        category = q["category"]

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"QUERY {i}/{len(queries)}: {query}")
        logger.info(f"Category: {category}")
        logger.info("=" * 80)

        start_time = time.time()

        try:
            result = system.query(query)
            elapsed = time.time() - start_time

            # Extract trajectory data
            trajectory_data = []
            if hasattr(result, 'trajectory') and result.trajectory:
                for hop_data in result.trajectory:
                    if isinstance(hop_data, dict):
                        trajectory_data.append(hop_data)
                    else:
                        trajectory_data.append({
                            "hop": getattr(hop_data, 'hop', len(trajectory_data) + 1),
                            "delta": round(getattr(hop_data, 'combined', 0.0), 4),
                            "delta_E": round(getattr(hop_data, 'delta_E', 0.0), 4),
                            "delta_V": round(getattr(hop_data, 'delta_V', 0.0), 4),
                            "delta_A": round(float(getattr(hop_data, 'delta_A', 0.0)), 4),
                            "delta_C": round(getattr(hop_data, 'delta_C', 0.0), 4),
                            "op_A_score": round(getattr(hop_data, 'operator_A_score', 0.0), 4),
                            "op_B_score": round(getattr(hop_data, 'operator_B_score', 0.0), 4),
                        })

            # Get final divergence values
            final_delta = result.final_delta if hasattr(result, 'final_delta') else 0.0
            delta_E = result.delta_E if hasattr(result, 'delta_E') else 0.0
            delta_V = result.delta_V if hasattr(result, 'delta_V') else 0.0
            delta_A = result.delta_A if hasattr(result, 'delta_A') else 0.0
            delta_C = result.delta_C if hasattr(result, 'delta_C') else 0.0

            # If trajectory exists, use final hop values
            if trajectory_data:
                final_hop = trajectory_data[-1]
                final_delta = final_hop.get("delta", final_delta)
                delta_E = final_hop.get("delta_E", delta_E)
                delta_V = final_hop.get("delta_V", delta_V)
                delta_A = final_hop.get("delta_A", delta_A)
                delta_C = final_hop.get("delta_C", delta_C)

            result_data = {
                "query_id": i,
                "query": query,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "elapsed_seconds": round(elapsed, 2),
                "system_type": system_type,
                "answer": result.answer,
                "confidence": result.confidence,
                "mode": result.mode if isinstance(result.mode, str) else str(result.mode),
                "hops_used": result.hops_used,
                "trajectory": trajectory_data,
                "evidence_count_A": len(result.evidence_A) if hasattr(result, 'evidence_A') and result.evidence_A else 0,
                "evidence_count_B": len(result.evidence_B) if hasattr(result, 'evidence_B') and result.evidence_B else 0,
                "answer_A": result.answer_A if hasattr(result, 'answer_A') else "",
                "answer_B": result.answer_B if hasattr(result, 'answer_B') else "",
                "reasoning": result.reasoning if hasattr(result, 'reasoning') else "",
                "path_confidence_A": round(result.path_confidence_A, 4) if hasattr(result, 'path_confidence_A') else 0.0,
                "path_confidence_B": round(result.path_confidence_B, 4) if hasattr(result, 'path_confidence_B') else 0.0,
                "reliability_A": round(result.reliability_A, 4) if hasattr(result, 'reliability_A') else 0.7,
                "reliability_B": round(result.reliability_B, 4) if hasattr(result, 'reliability_B') else 0.55,
                "ground_truth_injected": result.ground_truth_injected if hasattr(result, 'ground_truth_injected') else False,
                "xbrl_facts_count": result.xbrl_facts_count if hasattr(result, 'xbrl_facts_count') else 0,
                "final_delta": round(final_delta, 4),
                "delta_E": round(delta_E, 4),
                "delta_V": round(delta_V, 4),
                "delta_A": round(float(delta_A), 4),
                "delta_C": round(delta_C, 4),
            }

            results.append(result_data)

            logger.info(f"Completed in {elapsed:.2f}s")
            logger.info(f"Mode: {result.mode}, Confidence: {result.confidence:.1%}")
            logger.info(f"Hops: {result.hops_used}")
            logger.info(f"Evidence A: {result_data['evidence_count_A']}, Evidence B: {result_data['evidence_count_B']}")
            logger.info(f"Final Δ: {final_delta:.3f} (E={delta_E:.3f}, V={delta_V:.3f}, A={delta_A:.3f}, C={delta_C:.3f})")

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query_id": i,
                "query": query,
                "category": category,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "elapsed_seconds": time.time() - start_time
            })

    total_elapsed = time.time() - total_start

    # Save raw results
    with open("strategic_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Saved raw results to strategic_analysis_results.json")

    # Generate evaluation report
    report = generate_evaluation_report(results, total_elapsed, system_type)

    # Cleanup
    system.close()

    logger.info("=" * 80)
    logger.info("STRATEGIC ANALYSIS COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Results: strategic_analysis_results.json")
    logger.info(f"Report: Strategic_Analysis_Report.md")
    logger.info(f"Logs: {LOG_FILE}")
    logger.info(f"Total time: {total_elapsed:.1f}s")


def generate_evaluation_report(results: List[Dict], total_elapsed: float, system_type: str) -> str:
    """Generate evaluation report in the standard OpMech format."""

    successful = [r for r in results if "error" not in r]

    # Calculate statistics
    avg_confidence = sum(r.get("confidence", 0) for r in successful) / len(successful) if successful else 0
    avg_hops = sum(r.get("hops_used", 0) for r in successful) / len(successful) if successful else 0
    avg_time = sum(r.get("elapsed_seconds", 0) for r in successful) / len(successful) if successful else 0

    # Mode distribution
    mode_counts = {}
    for r in successful:
        mode = r.get("mode", "unknown")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    report = f"""# OpMech-GraphRAG Strategic Analysis Report
## Commutator and Operator Based Graph Retrieval-Augmented Generation

**Test Date:** {datetime.now().strftime("%B %d, %Y")}
**System:** OpMech-GraphRAG with Commutator-Guided Dynamic Search ({system_type})
**Model:** Qwen/Qwen2.5-7B-Instruct via vLLM
**Dataset:** Apple Inc. SEC 10-K Filings (FY2022-FY2024)
**Total Queries Evaluated:** {len(results)}

---

## Executive Summary

This report presents the strategic analysis results from the OpMech-GraphRAG system, evaluating {len(results)} fundamental analysis queries designed to assess company health, risk factors, and performance trends.

### Key Results Summary

| Category | Query | Confidence | Mode |
|----------|-------|------------|------|
"""

    for r in successful:
        query_short = r.get('query', 'N/A')[:50] + "..." if len(r.get('query', '')) > 50 else r.get('query', 'N/A')
        report += f"| {r.get('category', 'N/A')} | {query_short} | {r.get('confidence', 0)*100:.1f}% | {r.get('mode', 'N/A').upper()} |\n"

    report += f"""
### Aggregate Statistics

| Metric | Value |
|--------|-------|
| Successful Queries | {len(successful)}/{len(results)} |
| Average Confidence | {avg_confidence*100:.1f}% |
| Average Hops Used | {avg_hops:.1f} |
| Average Processing Time | {avg_time:.1f}s |
| Total Processing Time | {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes) |

### Mode Distribution

| Mode | Count | Percentage | Avg Confidence |
|------|-------|------------|----------------|
"""

    for mode in sorted(mode_counts.keys()):
        count = mode_counts[mode]
        pct = count / len(successful) * 100 if successful else 0
        mode_results = [r for r in successful if r.get("mode") == mode]
        mode_avg_conf = sum(r.get("confidence", 0) for r in mode_results) / len(mode_results) if mode_results else 0
        report += f"| {mode.upper()} | {count} | {pct:.0f}% | {mode_avg_conf*100:.1f}% |\n"

    report += """
---

## Architecture Overview

```
                    +------------------+
                    |     Query        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+       +-----------v---------+
    |   Operator A      |       |     Operator B      |
    | (Structure-First) |       |  (Narrative-First)  |
    |   XBRL/Financial  |       |    MD&A/Narrative   |
    +---------+---------+       +-----------+---------+
              |                             |
              |     +---------------+       |
              +---->|  Commutator   |<------+
                    | (Divergence)  |
                    +-------+-------+
                            |
                    +-------v-------+
                    | Mode Selector |
                    | EXPLOIT/      |
                    | ADAPTIVE/     |
                    | EXPLORE       |
                    +-------+-------+
                            |
                    +-------v-------+
                    | Final Answer  |
                    +---------------+
```

### Divergence Metrics

- **Delta_E (Evidence)**: Jaccard distance between evidence sets
- **Delta_V (Structural)**: Overlap in graph neighborhoods
- **Delta_A (Answer)**: Semantic similarity of generated answers
- **Delta_C (Confidence)**: Difference in operator confidence scores

### Mode Selection Logic

- **EXPLOIT Mode** (Low Divergence): Operators agree - use consensus answer
- **ADAPTIVE Mode** (Medium Divergence): Partial agreement - weighted merge
- **EXPLORE Mode** (High Divergence): Significant disagreement - present multiple perspectives

---

## Detailed Query Results

"""

    for i, r in enumerate(successful, 1):
        # Get final divergence values
        final_delta = r.get("final_delta", 0)
        delta_E = r.get("delta_E", 0)
        delta_V = r.get("delta_V", 0)
        delta_A = r.get("delta_A", 0)
        delta_C = r.get("delta_C", 0)

        # Interpret divergence level
        if final_delta < 0.35:
            divergence_interp = "Low - Operators converged"
        elif final_delta < 0.55:
            divergence_interp = "Medium - Partial agreement"
        else:
            divergence_interp = "High - Significant disagreement"

        report += f"""---

## Query {i}: {r.get('category', 'Analysis')}

**Query:** "{r.get('query', 'N/A')}"

**Category:** {r.get('category', 'N/A')}
**Mode:** {r.get('mode', 'N/A').upper()}
**Confidence:** {r.get('confidence', 0)*100:.1f}%
**Processing Time:** {r.get('elapsed_seconds', 0):.2f} seconds
**Hops Used:** {r.get('hops_used', 0)}

### Final Synthesized Answer

> {r.get('answer', 'No answer generated.')[:3000]}

### Operator A Response (Structure-First / XBRL Focus)

> {r.get('answer_A', 'No response generated.')[:2000]}

### Operator B Response (Narrative-First / MD&A Focus)

> {r.get('answer_B', 'No response generated.')[:2000]}

### Divergence Metrics

| Metric | Final Value | Interpretation |
|--------|-------------|----------------|
| Combined Delta | {final_delta:.3f} | {divergence_interp} |
| Delta_E (Evidence) | {delta_E:.3f} | {"**Maximum** - Completely different" if delta_E > 0.95 else "High" if delta_E > 0.7 else "Moderate" if delta_E > 0.4 else "Low"} evidence |
| Delta_V (Structural) | {delta_V:.3f} | {"High" if delta_V > 0.7 else "Moderate" if delta_V > 0.4 else "Low"} structural divergence |
| Delta_A (Answer) | {delta_A:.3f} | {"Very high" if delta_A < 0.1 else "Good" if delta_A < 0.2 else "Moderate"} answer similarity |
| Delta_C (Confidence) | {delta_C:.3f} | {"Very similar" if delta_C < 0.1 else "Similar" if delta_C < 0.2 else "Different"} confidence |

### Evidence Statistics

| Metric | Operator A | Operator B |
|--------|------------|------------|
| Total Evidence Nodes | {r.get('evidence_count_A', 0)} | {r.get('evidence_count_B', 0)} |
| Reliability Score | {r.get('reliability_A', 0.7):.2f} | {r.get('reliability_B', 0.55):.2f} |
| Path Confidence | {r.get('path_confidence_A', 0):.4f} | {r.get('path_confidence_B', 0):.4f} |

"""

        # Add trajectory table if available
        trajectory = r.get("trajectory", [])
        if trajectory:
            report += "### Trajectory (Convergence Over Hops)\n\n"
            report += "| Hop | Combined | Delta_E | Delta_V | Delta_A | Delta_C | Op_A Score | Op_B Score |\n"
            report += "|-----|----------|---------|---------|---------|---------|------------|------------|\n"

            for hop_data in trajectory:
                hop = hop_data.get("hop", 0)
                delta = hop_data.get("delta", 0)
                d_e = hop_data.get("delta_E", 0)
                d_v = hop_data.get("delta_V", 0)
                d_a = float(hop_data.get("delta_A", 0))
                d_c = hop_data.get("delta_C", 0)
                op_a = hop_data.get("op_A_score", 0)
                op_b = hop_data.get("op_B_score", 0)

                report += f"| {hop} | {delta:.3f} | {d_e:.3f} | {d_v:.3f} | {d_a:.3f} | {d_c:.3f} | {op_a:.3f} | {op_b:.3f} |\n"

            report += "\n"

        # Add mode reasoning
        if r.get("reasoning"):
            report += f"**Mode Reasoning:** \"{r.get('reasoning')}\"\n\n"

        # Add ground truth info
        if r.get("ground_truth_injected"):
            report += f"**Ground Truth:** Injected {r.get('xbrl_facts_count', 0)} XBRL facts\n\n"

    # Key Findings section
    report += """---

## Key Findings and Analysis

### 1. Evidence Divergence Analysis

"""

    high_divergence = [r for r in successful if r.get("delta_E", 0) > 0.8]
    moderate_divergence = [r for r in successful if 0.4 < r.get("delta_E", 0) <= 0.8]
    low_divergence = [r for r in successful if r.get("delta_E", 0) <= 0.4]

    report += f"""| Divergence Level | Count | Description |
|------------------|-------|-------------|
| High (>0.8) | {len(high_divergence)} | Operators found completely different evidence |
| Moderate (0.4-0.8) | {len(moderate_divergence)} | Partial evidence overlap |
| Low (<0.4) | {len(low_divergence)} | Strong evidence agreement |

"""

    if high_divergence:
        report += f"**Note:** {len(high_divergence)} queries showed very high evidence divergence (Delta_E > 0.8), indicating the dual operators explored different parts of the knowledge graph.\n\n"

    report += """### 2. Mode Selection Patterns

"""

    for mode in sorted(mode_counts.keys()):
        count = mode_counts[mode]
        if mode.lower() == "exploit":
            report += f"- **EXPLOIT ({count} queries):** High confidence answers where operators converged on similar evidence and conclusions\n"
        elif mode.lower() == "adaptive":
            report += f"- **ADAPTIVE ({count} queries):** Balanced synthesis with reliability-weighted merging of operator perspectives\n"
        elif mode.lower() == "explore":
            report += f"- **EXPLORE ({count} queries):** Multiple perspectives presented due to high operator divergence\n"

    report += """

### 3. Operator Performance Comparison

| Metric | Operator A (Structure-First) | Operator B (Narrative-First) |
|--------|------------------------------|------------------------------|
"""

    avg_evidence_a = sum(r.get("evidence_count_A", 0) for r in successful) / len(successful) if successful else 0
    avg_evidence_b = sum(r.get("evidence_count_B", 0) for r in successful) / len(successful) if successful else 0
    avg_path_conf_a = sum(r.get("path_confidence_A", 0) for r in successful) / len(successful) if successful else 0
    avg_path_conf_b = sum(r.get("path_confidence_B", 0) for r in successful) / len(successful) if successful else 0

    report += f"| Avg Evidence Nodes | {avg_evidence_a:.1f} | {avg_evidence_b:.1f} |\n"
    report += f"| Avg Path Confidence | {avg_path_conf_a:.3f} | {avg_path_conf_b:.3f} |\n"

    report += f"""

---

## Conclusion

The OpMech-GraphRAG system processed {len(successful)} strategic analysis queries with:

1. **Average Confidence:** {avg_confidence*100:.1f}% across all queries
2. **Mode Distribution:** {', '.join(f'{m.upper()}: {c}' for m, c in mode_counts.items())}
3. **Processing Efficiency:** {avg_time:.1f}s average per query

The dual-operator architecture successfully provided complementary perspectives on financial analysis questions, with the commutator enabling intelligent synthesis based on operator agreement levels.

### Recommendations for Improvement

1. **Evidence Sharing:** Consider stronger evidence sharing mechanisms when Delta_E > 0.8
2. **Prompt Optimization:** Further reduce prompt length to stay within context limits
3. **Fiscal Year Labels:** Ensure LLM consistently uses explicit fiscal year labels (FY2022, FY2023)

---

**Report Generated:** {datetime.now().strftime("%B %d, %Y %H:%M:%S")}
**System Version:** OpMech-GraphRAG v1.0 ({system_type})
**Total Processing Time:** {total_elapsed:.2f} seconds ({total_elapsed/60:.1f} minutes)
**Log File:** {LOG_FILE}
"""

    # Save report
    report_path = "/home/divyansh/AIF_FInal_Project/Strategic_Analysis_Report.md"
    with open(report_path, "w") as f:
        f.write(report)

    logger.info(f"Saved evaluation report to {report_path}")

    return report


if __name__ == "__main__":
    run_strategic_queries()
