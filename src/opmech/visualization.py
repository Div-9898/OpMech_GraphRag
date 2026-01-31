"""Visualization and diagnostics for OpMech-GraphRAG.

Provides trajectory visualization and JSON export.
"""

import json
from typing import Dict

from src.opmech.data_classes import QueryResult


def print_trajectory(result: QueryResult):
    """
    Print divergence trajectory visualization.

    Args:
        result: QueryResult from OpMech-GraphRAG query
    """
    print("\n" + "=" * 70)
    print("OPMECH-GRAPHRAG QUERY RESULT")
    print("=" * 70)

    print(f"\nMode: {result.mode.value.upper()}")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Hops Used: {result.hops_used}")

    print(f"\n{'-' * 70}")
    print("DIVERGENCE TRAJECTORY")
    print(f"{'-' * 70}")

    print(f"\n{'Hop':<5} {'delta_E':<10} {'delta_V':<10} {'delta_A':<10} {'delta_C':<10} {'Combined':<10} {'Status'}")
    print(f"{'-' * 70}")

    for comm in result.trajectory:
        # Status indicator
        if comm.combined < 0.25:
            status = "EXPLOIT"
        elif comm.combined > 0.60:
            status = "EXPLORE"
        else:
            status = "ADAPTIVE"

        print(f"{comm.hop:<5} {comm.delta_E:<10.3f} {comm.delta_V:<10.3f} "
              f"{comm.delta_A:<10.3f} {comm.delta_C:<10.3f} {comm.combined:<10.3f} {status}")

    # Visual bar chart
    print(f"\n{'-' * 70}")
    print("VISUAL TRAJECTORY")
    print(f"{'-' * 70}")

    for comm in result.trajectory:
        bar_len = int(comm.combined * 40)
        bar = '#' * bar_len + '.' * (40 - bar_len)
        print(f"Hop {comm.hop}: [{bar}] {comm.combined:.3f}")

    # Operator scores
    print(f"\n{'-' * 70}")
    print("OPERATOR SCORES")
    print(f"{'-' * 70}")

    for name, score in result.operator_scores.items():
        bar_len = int(score * 40)
        bar = '=' * bar_len + '.' * (40 - bar_len)
        print(f"{name:20}: [{bar}] {score:.3f}")

    # Path confidence
    print(f"\n{'-' * 70}")
    print("PATH CONFIDENCE")
    print(f"{'-' * 70}")
    print(f"Operator A (Structure-First): {result.path_confidence_A:.3f}")
    print(f"Operator B (Narrative-First): {result.path_confidence_B:.3f}")

    # Edge confidence stats
    if result.edge_conf_stats:
        print(f"\n{'-' * 70}")
        print("EDGE CONFIDENCE STATISTICS")
        print(f"{'-' * 70}")
        for op_name, stats in result.edge_conf_stats.items():
            print(f"{op_name}: mean={stats['mean']:.3f}, std={stats['std']:.3f}, "
                  f"min={stats['min']:.3f}, max={stats['max']:.3f}")

    # Evidence summary
    print(f"\n{'-' * 70}")
    print("EVIDENCE SUMMARY")
    print(f"{'-' * 70}")
    print(f"Structure-First evidence: {len(result.evidence_A)} nodes")
    print(f"Narrative-First evidence: {len(result.evidence_B)} nodes")

    # Final answer
    print(f"\n{'-' * 70}")
    print("FINAL ANSWER")
    print(f"{'-' * 70}")
    print(f"\n{result.answer}")

    print(f"\n{'-' * 70}")
    print(f"Reasoning: {result.reasoning}")
    print("=" * 70)


def print_trajectory_compact(result: QueryResult):
    """
    Print a compact version of the trajectory.

    Args:
        result: QueryResult from OpMech-GraphRAG query
    """
    print(f"\n[{result.mode.value.upper()}] Confidence: {result.confidence:.1%} | Hops: {result.hops_used}")

    if result.trajectory:
        final = result.trajectory[-1]
        print(f"Final divergence: {final.combined:.3f} "
              f"(E={final.delta_E:.2f} V={final.delta_V:.2f} "
              f"A={final.delta_A:.2f} C={final.delta_C:.2f})")

    print(f"\nAnswer: {result.answer[:200]}...")


def export_trajectory_json(result: QueryResult, filepath: str):
    """
    Export trajectory to JSON for analysis.

    Args:
        result: QueryResult from OpMech-GraphRAG query
        filepath: Output JSON file path
    """
    data = {
        "mode": result.mode.value,
        "confidence": result.confidence,
        "hops_used": result.hops_used,
        "reasoning": result.reasoning,
        "operator_scores": result.operator_scores,
        "path_confidence_A": result.path_confidence_A,
        "path_confidence_B": result.path_confidence_B,
        "edge_conf_stats": result.edge_conf_stats,
        "trajectory": [
            {
                "hop": c.hop,
                "delta_E": c.delta_E,
                "delta_V": c.delta_V,
                "delta_A": c.delta_A,
                "delta_C": c.delta_C,
                "combined": c.combined,
                "operator_A_score": c.operator_A_score,
                "operator_B_score": c.operator_B_score
            }
            for c in result.trajectory
        ],
        "answer": result.answer,
        "answer_A": result.answer_A,
        "answer_B": result.answer_B,
        "evidence_A": [
            {
                "id": n.id,
                "type": n.type,
                "text": n.text[:500],
                "metadata": n.metadata
            }
            for n in result.evidence_A[:10]
        ],
        "evidence_B": [
            {
                "id": n.id,
                "type": n.type,
                "text": n.text[:500],
                "metadata": n.metadata
            }
            for n in result.evidence_B[:10]
        ]
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Trajectory exported to: {filepath}")


def format_evidence_table(result: QueryResult) -> str:
    """
    Format evidence as a table string.

    Args:
        result: QueryResult from OpMech-GraphRAG query

    Returns:
        Formatted table string
    """
    lines = []

    lines.append("\nEVIDENCE FROM STRUCTURE-FIRST OPERATOR:")
    lines.append("-" * 80)
    for i, node in enumerate(result.evidence_A[:5], 1):
        lines.append(f"{i}. [{node.type}] {node.metadata.get('section', 'N/A')} - {node.metadata.get('period', 'N/A')}")
        lines.append(f"   {node.text[:100]}...")

    lines.append("\nEVIDENCE FROM NARRATIVE-FIRST OPERATOR:")
    lines.append("-" * 80)
    for i, node in enumerate(result.evidence_B[:5], 1):
        lines.append(f"{i}. [{node.type}] {node.metadata.get('section', 'N/A')} - {node.metadata.get('period', 'N/A')}")
        lines.append(f"   {node.text[:100]}...")

    return "\n".join(lines)


def plot_trajectory_ascii(result: QueryResult) -> str:
    """
    Create ASCII art plot of divergence trajectory.

    Args:
        result: QueryResult from OpMech-GraphRAG query

    Returns:
        ASCII plot string
    """
    if not result.trajectory:
        return "No trajectory data"

    lines = []
    lines.append("\nDIVERGENCE TRAJECTORY PLOT")
    lines.append("=" * 50)

    # Y-axis labels
    y_labels = ["1.0", "0.8", "0.6", "0.4", "0.2", "0.0"]

    # Build plot grid (6 rows x trajectory length)
    height = 6
    width = len(result.trajectory)

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Mark thresholds
    tau_low_row = int((1.0 - 0.25) * (height - 1))
    tau_high_row = int((1.0 - 0.60) * (height - 1))

    for hop_idx, comm in enumerate(result.trajectory):
        # Map combined score to row (0 = top = 1.0, 5 = bottom = 0.0)
        row = int((1.0 - comm.combined) * (height - 1))
        row = max(0, min(height - 1, row))
        grid[row][hop_idx] = '*'

    # Print grid
    for row_idx, row in enumerate(grid):
        label = y_labels[row_idx]
        line = f"{label} |"
        for col_idx, cell in enumerate(row):
            if row_idx == tau_low_row:
                line += '-' if cell == ' ' else cell
            elif row_idx == tau_high_row:
                line += '-' if cell == ' ' else cell
            else:
                line += cell
        lines.append(line)

    # X-axis
    lines.append("    +" + "-" * width)
    hop_labels = "     " + "".join([str(i + 1) for i in range(width)])
    lines.append(hop_labels)
    lines.append("     Hop")

    # Legend
    lines.append("")
    lines.append("Legend: * = divergence, - = threshold (tau_low=0.25, tau_high=0.60)")

    return "\n".join(lines)
