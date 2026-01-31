"""Diagnostic script to understand why operators are diverging on simple queries."""

from typing import Dict, List, Set

from loguru import logger
from neo4j import GraphDatabase


class OpMechDiagnostics:
    """Diagnose issues with operator divergence."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def diagnose_query(self, query: str, evidence_A: List[str], evidence_B: List[str]):
        """Full diagnostic for a query that showed high divergence."""
        print("=" * 80)
        print(f"DIAGNOSTIC REPORT: {query}")
        print("=" * 80)

        # 1. Check evidence overlap
        self._analyze_evidence_overlap(evidence_A, evidence_B)

        # 2. Find what revenue nodes exist
        self._find_revenue_nodes()

        # 3. Check if revenue nodes are in either evidence set
        self._check_revenue_in_evidence(evidence_A, evidence_B)

        # 4. Analyze why operators diverged
        self._analyze_divergence_causes(evidence_A, evidence_B)

        # 5. Check edge density for different edge types
        self._analyze_edge_density()

    def _analyze_evidence_overlap(self, evidence_A: List[str], evidence_B: List[str]):
        """Compute and explain evidence overlap."""
        set_A = set(evidence_A)
        set_B = set(evidence_B)

        intersection = set_A & set_B
        union = set_A | set_B
        only_A = set_A - set_B
        only_B = set_B - set_A

        print("\n--- EVIDENCE OVERLAP ANALYSIS ---")
        print(f"Operator A evidence: {len(set_A)} nodes")
        print(f"Operator B evidence: {len(set_B)} nodes")
        print(f"Intersection: {len(intersection)} nodes")
        print(f"Union: {len(union)} nodes")
        print(f"Jaccard similarity: {len(intersection) / len(union) if union else 0:.3f}")
        print(f"Δ_E (Jaccard distance): {1 - len(intersection) / len(union) if union else 1:.3f}")

        if intersection:
            print(f"\nShared nodes: {list(intersection)[:10]}")
        else:
            print("\nWARNING: NO OVERLAP - Operators found completely different evidence!")

        print(f"\nOnly in Operator A: {list(only_A)[:5]}")
        print(f"Only in Operator B: {list(only_B)[:5]}")

    def _find_revenue_nodes(self):
        """Find all nodes that should contain revenue information."""
        print("\n--- REVENUE NODES IN GRAPH ---")

        with self.driver.session() as session:
            # Find FINANCIAL_LINE nodes with revenue XBRL tags
            result = session.run("""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND (
                    toLower(n.xbrl_tag) CONTAINS 'revenue'
                    OR toLower(n.xbrl_tag) CONTAINS 'sales'
                    OR toLower(n.text) CONTAINS 'total net sales'
                )
                RETURN n.id AS id, n.xbrl_tag AS xbrl_tag, n.value AS value,
                       n.period AS period, n.text AS text
                ORDER BY n.period DESC
                LIMIT 20
            """)

            revenue_nodes = list(result)
            print(f"Found {len(revenue_nodes)} revenue-related FINANCIAL_LINE nodes:")
            for node in revenue_nodes:
                print(f"  - {node['id']}: {node['xbrl_tag']} = {node['value']} ({node['period']})")

            # Find TEXT_SECTION nodes mentioning revenue
            result2 = session.run("""
                MATCH (n:Node)
                WHERE n.type = 'TEXT_SECTION'
                AND toLower(n.text) CONTAINS 'total net sales'
                RETURN n.id AS id, n.section AS section,
                       substring(n.text, 0, 200) AS text_preview
                LIMIT 10
            """)

            text_nodes = list(result2)
            print(f"\nFound {len(text_nodes)} TEXT_SECTION nodes mentioning revenue:")
            for node in text_nodes:
                print(f"  - {node['id']} ({node['section']}): {node['text_preview'][:100]}...")

    def _check_revenue_in_evidence(self, evidence_A: List[str], evidence_B: List[str]):
        """Check if the correct revenue nodes are in the evidence sets."""
        print("\n--- REVENUE NODES IN EVIDENCE ---")

        with self.driver.session() as session:
            # Get IDs of revenue nodes
            result = session.run("""
                MATCH (n:Node)
                WHERE n.type = 'FINANCIAL_LINE'
                AND (
                    toLower(n.xbrl_tag) CONTAINS 'revenue'
                    OR toLower(n.xbrl_tag) CONTAINS 'sales'
                )
                RETURN n.id AS id
            """)
            revenue_ids = {r['id'] for r in result}

        revenue_in_A = set(evidence_A) & revenue_ids
        revenue_in_B = set(evidence_B) & revenue_ids

        print(f"Revenue nodes in Operator A evidence: {len(revenue_in_A)}")
        if revenue_in_A:
            print(f"  IDs: {list(revenue_in_A)[:5]}")
        else:
            print("  WARNING: NO REVENUE NODES IN OPERATOR A EVIDENCE!")

        print(f"Revenue nodes in Operator B evidence: {len(revenue_in_B)}")
        if revenue_in_B:
            print(f"  IDs: {list(revenue_in_B)[:5]}")
        else:
            print("  WARNING: NO REVENUE NODES IN OPERATOR B EVIDENCE!")

    def _analyze_divergence_causes(self, evidence_A: List[str], evidence_B: List[str]):
        """Analyze why the operators diverged."""
        print("\n--- DIVERGENCE CAUSE ANALYSIS ---")

        with self.driver.session() as session:
            # Get node types in each evidence set
            for name, evidence in [("A", evidence_A), ("B", evidence_B)]:
                if not evidence:
                    continue

                result = session.run("""
                    MATCH (n:Node)
                    WHERE n.id IN $ids
                    RETURN n.type AS type, count(*) AS count
                    ORDER BY count DESC
                """, ids=evidence)

                print(f"\nOperator {name} evidence composition:")
                for row in result:
                    print(f"  {row['type']}: {row['count']} nodes")

            # Get sections represented in each evidence set
            for name, evidence in [("A", evidence_A), ("B", evidence_B)]:
                if not evidence:
                    continue

                result = session.run("""
                    MATCH (n:Node)
                    WHERE n.id IN $ids
                    RETURN DISTINCT n.section AS section
                """, ids=evidence)

                sections = [r['section'] for r in result if r['section']]
                print(f"\nOperator {name} sections: {sections[:10]}")

    def _analyze_edge_density(self):
        """Analyze edge density to understand traversal explosion."""
        print("\n--- EDGE DENSITY ANALYSIS ---")

        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                RETURN COALESCE(r.type, type(r)) AS edge_type,
                       count(*) AS count,
                       avg(COALESCE(r.confidence, 0.5)) AS avg_confidence,
                       min(COALESCE(r.confidence, 0.5)) AS min_confidence,
                       max(COALESCE(r.confidence, 1.0)) AS max_confidence
                ORDER BY count DESC
            """)

            print("\nEdge type statistics:")
            print(f"{'Edge Type':<30} {'Count':>8} {'Avg Conf':>10} {'Min':>8} {'Max':>8}")
            print("-" * 70)
            for row in result:
                print(f"{row['edge_type']:<30} {row['count']:>8} {row['avg_confidence']:>10.3f} {row['min_confidence']:>8.3f} {row['max_confidence']:>8.3f}")

            # Check average out-degree per edge type
            result2 = session.run("""
                MATCH (n:Node)-[r]->()
                WITH n, COALESCE(r.type, type(r)) AS edge_type, count(*) AS out_degree
                RETURN edge_type, avg(out_degree) AS avg_out_degree, max(out_degree) AS max_out_degree
                ORDER BY avg_out_degree DESC
            """)

            print("\nAverage out-degree per edge type:")
            for row in result2:
                print(f"  {row['edge_type']}: avg={row['avg_out_degree']:.1f}, max={row['max_out_degree']}")

    def trace_operator_path(self, operator_name: str, seed_ids: List[str],
                           edge_types: List[str], max_hops: int = 2):
        """Trace exactly what path an operator takes."""
        print(f"\n--- TRACING {operator_name} PATH ---")
        print(f"Seeds: {seed_ids[:5]}...")
        print(f"Edge types: {edge_types}")
        print(f"Max hops: {max_hops}")

        with self.driver.session() as session:
            current_frontier = set(seed_ids)
            visited = set(seed_ids)

            for hop in range(1, max_hops + 1):
                # Find neighbors
                result = session.run("""
                    MATCH (source:Node)-[r]->(target:Node)
                    WHERE source.id IN $frontier
                    AND COALESCE(r.type, type(r)) IN $edge_types
                    RETURN source.id AS source, target.id AS target,
                           COALESCE(r.type, type(r)) AS edge_type,
                           COALESCE(r.confidence, 0.5) AS confidence
                    ORDER BY confidence DESC
                    LIMIT 1000
                """, frontier=list(current_frontier), edge_types=edge_types)

                edges = list(result)
                new_nodes = {e['target'] for e in edges if e['target'] not in visited}

                print(f"\nHop {hop}:")
                print(f"  Frontier size: {len(current_frontier)}")
                print(f"  Edges found: {len(edges)}")
                print(f"  New nodes: {len(new_nodes)}")

                # Edge type breakdown
                edge_counts = {}
                for e in edges:
                    edge_counts[e['edge_type']] = edge_counts.get(e['edge_type'], 0) + 1
                print(f"  Edge breakdown: {edge_counts}")

                visited.update(new_nodes)
                current_frontier = new_nodes

                if not new_nodes:
                    print("  No new nodes - stopping")
                    break

            print(f"\nTotal visited: {len(visited)} nodes")

    def close(self):
        self.driver.close()


class ScoringDiagnostics:
    """Analyze edge scoring patterns to understand traversal behavior."""

    def __init__(self, scores: List):
        """
        Initialize with edge scores from traversal.

        Args:
            scores: List of EdgeScore objects from traverse_with_scoring
        """
        self.scores = scores

    def summarize(self) -> Dict:
        """Generate summary statistics."""
        if not self.scores:
            return {"error": "No scores to analyze"}

        import numpy as np

        # Basic stats
        total_scores = [s.total_score for s in self.scores]

        # Reward breakdown
        rewards = {
            "domain_crossing": [s.domain_crossing_reward for s in self.scores],
            "query_relevance": [s.query_relevance_reward for s in self.scores],
            "novelty": [s.novelty_reward for s in self.scores],
            "bridge_edge": [s.bridge_edge_reward for s in self.scores],
            "convergence": [s.convergence_reward for s in self.scores],
        }

        # Penalty breakdown
        penalties = {
            "semantic_drift": [s.semantic_drift_penalty for s in self.scores],
            "domain_isolation": [s.domain_isolation_penalty for s in self.scores],
            "low_confidence": [s.low_confidence_penalty for s in self.scores],
            "redundancy": [s.redundancy_penalty for s in self.scores],
            "fanout": [s.fanout_penalty for s in self.scores],
        }

        # Edge type distribution
        edge_types = {}
        for s in self.scores:
            edge_types[s.edge_type] = edge_types.get(s.edge_type, 0) + 1

        return {
            "total_edges_scored": len(self.scores),
            "score_stats": {
                "mean": np.mean(total_scores),
                "std": np.std(total_scores),
                "min": np.min(total_scores),
                "max": np.max(total_scores),
                "median": np.median(total_scores),
            },
            "reward_means": {k: np.mean(v) for k, v in rewards.items()},
            "penalty_means": {k: np.mean(v) for k, v in penalties.items()},
            "edge_type_counts": edge_types,
            "edges_above_threshold": sum(1 for s in total_scores if s >= 0.3),
            "edges_below_threshold": sum(1 for s in total_scores if s < 0.3),
        }

    def find_problematic_patterns(self) -> List[str]:
        """Identify issues with scoring patterns."""
        issues = []
        summary = self.summarize()

        if "error" in summary:
            return [summary["error"]]

        # Check for semantic drift dominance
        if summary["penalty_means"]["semantic_drift"] > 0.3:
            issues.append(
                f"HIGH SEMANTIC DRIFT PENALTY: {summary['penalty_means']['semantic_drift']:.3f} "
                f"- Too many SEMANTICALLY_SIMILAR chains"
            )

        # Check for domain isolation
        if summary["penalty_means"]["domain_isolation"] > 0.2:
            issues.append(
                f"HIGH DOMAIN ISOLATION: {summary['penalty_means']['domain_isolation']:.3f} "
                f"- Operators not crossing domains"
            )

        # Check for low domain crossing rewards
        if summary["reward_means"]["domain_crossing"] < 0.1:
            issues.append(
                f"LOW DOMAIN CROSSING: {summary['reward_means']['domain_crossing']:.3f} "
                f"- Operators staying in their silos"
            )

        # Check for low convergence
        if summary["reward_means"]["convergence"] < 0.05:
            issues.append(
                f"LOW CONVERGENCE: {summary['reward_means']['convergence']:.3f} "
                f"- Operators not finding shared evidence"
            )

        # Check for too many low-score edges
        if summary["total_edges_scored"] > 0:
            pct_below = summary["edges_below_threshold"] / summary["total_edges_scored"]
            if pct_below > 0.7:
                issues.append(
                    f"HIGH REJECTION RATE: {pct_below*100:.1f}% edges below threshold "
                    f"- May need to relax penalties"
                )

        return issues

    def print_report(self):
        """Print human-readable diagnostic report."""
        summary = self.summarize()
        issues = self.find_problematic_patterns()

        print("\n" + "=" * 60)
        print("EDGE SCORING DIAGNOSTIC REPORT")
        print("=" * 60)

        if "error" in summary:
            print(f"Error: {summary['error']}")
            return

        print(f"\nTotal edges scored: {summary['total_edges_scored']}")
        print(f"Edges above threshold (>=0.3): {summary['edges_above_threshold']}")
        print(f"Edges below threshold (<0.3): {summary['edges_below_threshold']}")

        print("\n--- Score Statistics ---")
        stats = summary["score_stats"]
        print(f"Mean: {stats['mean']:.3f}, Std: {stats['std']:.3f}")
        print(f"Min: {stats['min']:.3f}, Max: {stats['max']:.3f}")

        print("\n--- Reward Means ---")
        for k, v in summary["reward_means"].items():
            bar = "#" * int(v * 20)
            print(f"  {k:<20}: {v:.3f} {bar}")

        print("\n--- Penalty Means ---")
        for k, v in summary["penalty_means"].items():
            bar = "X" * int(v * 20)
            print(f"  {k:<20}: {v:.3f} {bar}")

        print("\n--- Edge Type Distribution ---")
        for edge_type, count in sorted(summary["edge_type_counts"].items(),
                                       key=lambda x: -x[1]):
            print(f"  {edge_type:<25}: {count}")

        if issues:
            print("\n--- ISSUES DETECTED ---")
            for issue in issues:
                print(f"  [!] {issue}")
        else:
            print("\n[OK] No major issues detected")

        print("\n" + "=" * 60)


def run_diagnostics():
    """Run full diagnostics on the problematic query."""
    diag = OpMechDiagnostics(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123"
    )

    # Run edge density analysis
    diag._analyze_edge_density()

    # Find revenue nodes
    diag._find_revenue_nodes()

    # Trace Operator A path with typical edge types
    diag.trace_operator_path(
        "OperatorA",
        seed_ids=[],  # Will be filled dynamically
        edge_types=["TEMPORAL_NEXT", "EXPLAINS_LINE_ITEM", "REFERS_TO"],
        max_hops=2
    )

    # Trace Operator B path with typical edge types
    diag.trace_operator_path(
        "OperatorB",
        seed_ids=[],  # Will be filled dynamically
        edge_types=["CAUSED_BY", "DISCUSSES", "MENTIONS_ENTITY", "SEMANTICALLY_SIMILAR"],
        max_hops=2
    )

    diag.close()


if __name__ == "__main__":
    run_diagnostics()
