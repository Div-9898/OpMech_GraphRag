#!/usr/bin/env python3
"""Generate gold standard datasets for expert evaluation using LLM-assisted annotation."""

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.evaluation.gold_standard import GoldEdge, GoldStandard, save_gold_standard
from src.experts.base import cosine_similarity
from src.experts.llm_client import LLMClient
from src.models import EdgeType, Node, NodeType


def load_all_nodes() -> list[Node]:
    """Load all parsed nodes from all filings."""
    nodes = []
    parsed_dir = settings.parsed_dir

    for filing_dir in sorted(parsed_dir.iterdir()):
        if filing_dir.is_dir():
            # Load from JSONL format
            nodes_file = filing_dir / "nodes.jsonl"
            if nodes_file.exists():
                with open(nodes_file, "r") as f:
                    for line in f:
                        if line.strip():
                            node = Node.model_validate_json(line)
                            nodes.append(node)
                logger.debug(f"Loaded nodes from {filing_dir.name}")

    logger.info(f"Total nodes loaded: {len(nodes)}")
    return nodes


def load_all_embeddings() -> dict[str, np.ndarray]:
    """Load all embeddings."""
    embeddings = {}
    embeddings_dir = settings.embeddings_dir

    for filing_dir in sorted(embeddings_dir.iterdir()):
        if filing_dir.is_dir():
            # Load from NPZ format
            emb_file = filing_dir / "embeddings.npz"
            if emb_file.exists():
                data = np.load(emb_file)
                for key in data.files:
                    embeddings[key] = data[key]
                logger.debug(f"Loaded {len(data.files)} embeddings from {filing_dir.name}")

    logger.info(f"Total embeddings loaded: {len(embeddings)}")
    return embeddings


class GoldStandardGenerator:
    """Generate gold standard datasets using LLM annotation."""

    def __init__(self, nodes: list[Node], embeddings: dict[str, np.ndarray]):
        self.nodes = nodes
        self.embeddings = embeddings
        self.node_map = {n.id: n for n in nodes}
        self.llm = LLMClient()

        # Group nodes by type and filing
        self.nodes_by_type = {}
        self.nodes_by_filing = {}

        for node in nodes:
            # By type
            if node.type not in self.nodes_by_type:
                self.nodes_by_type[node.type] = []
            self.nodes_by_type[node.type].append(node)

            # By filing
            fid = node.metadata.filing_id
            if fid not in self.nodes_by_filing:
                self.nodes_by_filing[fid] = []
            self.nodes_by_filing[fid].append(node)

    def generate_crossref_gold(self, n_samples: int = 100) -> GoldStandard:
        """Generate gold standard for CrossReferenceHunter."""
        logger.info("Generating CrossReferenceHunter gold standard...")
        annotations = []

        # Get text and note nodes
        text_nodes = self.nodes_by_type.get(NodeType.TEXT_SECTION, [])
        note_nodes = self.nodes_by_type.get(NodeType.NOTE, [])

        # Strategy 1: Find explicit "Note X" references and match to corresponding notes
        import re
        note_ref_pattern = re.compile(r'note\s*(\d+)', re.IGNORECASE)

        positive_pairs = []
        for source in text_nodes:
            if len(source.text) < 200:  # Skip short fragments
                continue

            matches = note_ref_pattern.findall(source.text)
            if matches:
                filing_notes = [n for n in note_nodes if n.metadata.filing_id == source.metadata.filing_id]
                for note_num in matches:
                    # Find matching note by number
                    for note in filing_notes:
                        if note.metadata.note_number and str(note.metadata.note_number) == note_num:
                            positive_pairs.append((source, note, True, f"Explicit reference to Note {note_num}"))
                            break
                        # Also try matching by text pattern "Note X -"
                        if f"Note {note_num}" in note.text[:50]:
                            positive_pairs.append((source, note, True, f"Explicit reference to Note {note_num}"))
                            break

        logger.info(f"Found {len(positive_pairs)} explicit cross-reference pairs")

        # Strategy 2: Use embedding similarity to find related text-note pairs
        for filing_id in list(self.nodes_by_filing.keys())[:6]:
            filing_texts = [n for n in text_nodes if n.metadata.filing_id == filing_id
                          and n.id in self.embeddings and len(n.text) > 300][:20]
            filing_notes = [n for n in note_nodes if n.metadata.filing_id == filing_id
                          and n.id in self.embeddings]

            for text_node in filing_texts[:10]:
                if not filing_notes:
                    continue

                # Find most similar note
                similarities = [
                    (note, cosine_similarity(self.embeddings[text_node.id], self.embeddings[note.id]))
                    for note in filing_notes if note.id in self.embeddings
                ]
                similarities.sort(key=lambda x: x[1], reverse=True)

                if similarities and similarities[0][1] > 0.7:
                    best_note, sim = similarities[0]
                    positive_pairs.append((text_node, best_note, None, f"High embedding similarity: {sim:.3f}"))

        # Sample and annotate
        random.shuffle(positive_pairs)
        for source, target, known_label, reason in tqdm(positive_pairs[:n_samples], desc="CrossRef pairs"):
            if known_label is not None:
                label, confidence = known_label, 0.95
            else:
                label, confidence = self._annotate_crossref(source, target)

            annotations.append(GoldEdge(
                source_id=source.id,
                target_id=target.id,
                edge_type=EdgeType.REFERS_TO,
                label=label,
                annotator="llm" if known_label is None else "pattern",
                confidence=confidence,
                notes=reason,
            ))

        # Add negative samples (random unrelated pairs)
        n_negative = n_samples // 3
        for _ in range(n_negative):
            source = random.choice([n for n in text_nodes if len(n.text) > 300][:200])
            # Pick note from DIFFERENT filing
            other_filings = [f for f in self.nodes_by_filing if f != source.metadata.filing_id]
            if other_filings:
                other_filing = random.choice(other_filings)
                other_notes = [n for n in self.nodes_by_filing[other_filing] if n.type == NodeType.NOTE]
                if other_notes:
                    target = random.choice(other_notes)
                    annotations.append(GoldEdge(
                        source_id=source.id,
                        target_id=target.id,
                        edge_type=EdgeType.REFERS_TO,
                        label=False,
                        annotator="heuristic",
                        confidence=0.95,
                        notes="Cross-filing (negative sample)",
                    ))

        return GoldStandard(
            expert_name="CrossReferenceHunter",
            edge_type=EdgeType.REFERS_TO,
            annotations=annotations,
            metadata={"n_samples": len(annotations)},
        )

    def _annotate_crossref(self, source: Node, target: Node) -> tuple[bool, float]:
        """Use LLM to annotate if source references target."""
        prompt = f"""Determine if the SOURCE text contains a reference to the TARGET note.

SOURCE TEXT (from {source.metadata.section or 'filing'}):
{source.text[:1500]}

TARGET NOTE:
{target.text[:1000]}

Does the source text explicitly reference this note (e.g., "See Note X", "refer to Note Y")?
Output JSON: {{"references": true/false, "confidence": 0.0-1.0, "evidence": "brief quote if found"}}"""

        try:
            response = self.llm.generate(prompt, max_tokens=256, temperature=0.1)
            result = self.llm._parse_json_object(response)
            return result.get("references", False), result.get("confidence", 0.5)
        except Exception as e:
            logger.debug(f"CrossRef annotation failed: {e}")
            return False, 0.5

    def generate_causal_gold(self, n_samples: int = 100) -> GoldStandard:
        """Generate gold standard for CausalChainBuilder."""
        logger.info("Generating CausalChainBuilder gold standard...")
        annotations = []

        # Get text nodes
        text_nodes = self.nodes_by_type.get(NodeType.TEXT_SECTION, [])

        # Sample text nodes that likely contain causal language
        causal_keywords = [
            "due to", "because", "resulted in", "led to", "driven by",
            "caused by", "as a result", "consequently", "therefore"
        ]
        candidate_nodes = [
            n for n in text_nodes
            if any(kw in n.text.lower() for kw in causal_keywords)
        ][:n_samples * 2]

        random.shuffle(candidate_nodes)

        for node in tqdm(candidate_nodes[:n_samples], desc="Causal pairs"):
            # Find another text node in same filing with high similarity
            filing_texts = [
                n for n in text_nodes
                if n.metadata.filing_id == node.metadata.filing_id
                and n.id != node.id
                and n.id in self.embeddings
            ]

            if not filing_texts or node.id not in self.embeddings:
                continue

            # Find semantically similar node
            similarities = [
                (n, cosine_similarity(self.embeddings[node.id], self.embeddings[n.id]))
                for n in filing_texts
            ]
            similarities.sort(key=lambda x: x[1], reverse=True)

            if not similarities:
                continue

            target = similarities[0][0]

            # Use LLM to determine causal relationship
            label, confidence, direction = self._annotate_causal(node, target)

            if label and direction == "backward":
                # Swap source and target for cause -> effect direction
                source_id, target_id = target.id, node.id
            else:
                source_id, target_id = node.id, target.id

            annotations.append(GoldEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=EdgeType.CAUSED_BY,
                label=label,
                annotator="llm",
                confidence=confidence,
                notes=f"Similarity: {similarities[0][1]:.3f}",
            ))

        # Add negative samples (random unrelated pairs)
        n_negative = n_samples // 4
        for _ in range(n_negative):
            nodes_sample = random.sample(text_nodes[:500], 2)
            if nodes_sample[0].metadata.filing_id != nodes_sample[1].metadata.filing_id:
                annotations.append(GoldEdge(
                    source_id=nodes_sample[0].id,
                    target_id=nodes_sample[1].id,
                    edge_type=EdgeType.CAUSED_BY,
                    label=False,
                    annotator="heuristic",
                    confidence=0.9,
                    notes="Cross-filing (unlikely causal)",
                ))

        return GoldStandard(
            expert_name="CausalChainBuilder",
            edge_type=EdgeType.CAUSED_BY,
            annotations=annotations,
            metadata={"n_samples": len(annotations)},
        )

    def _annotate_causal(self, source: Node, target: Node) -> tuple[bool, float, str]:
        """Use LLM to annotate causal relationship."""
        prompt = f"""Analyze if there is a causal relationship between these two text sections.

TEXT 1:
{source.text[:1200]}

TEXT 2:
{target.text[:1200]}

Is there a cause-effect relationship where one describes a cause/driver and the other describes its effect/result?

Output JSON: {{
    "has_causal_relationship": true/false,
    "confidence": 0.0-1.0,
    "direction": "text1_causes_text2" or "text2_causes_text1" or "none",
    "cause_phrase": "brief quote of cause",
    "effect_phrase": "brief quote of effect"
}}"""

        try:
            response = self.llm.generate(prompt, max_tokens=256, temperature=0.1)
            result = self.llm._parse_json_object(response)

            has_causal = result.get("has_causal_relationship", False)
            confidence = result.get("confidence", 0.5)
            direction = result.get("direction", "none")

            dir_mapped = "forward" if direction == "text1_causes_text2" else "backward"
            return has_causal, confidence, dir_mapped
        except Exception as e:
            logger.debug(f"Causal annotation failed: {e}")
            return False, 0.5, "none"

    def generate_temporal_gold(self, n_samples: int = 100) -> GoldStandard:
        """Generate gold standard for TemporalLinker."""
        logger.info("Generating TemporalLinker gold standard...")
        annotations = []

        # Group filings by fiscal year
        filings_by_year = {}
        for fid in self.nodes_by_filing:
            # Extract year from filing ID (e.g., AAPL-10-K-FY2024 -> 2024)
            if "FY" in fid:
                year = fid.split("FY")[1][:4]
            elif "Q" in fid.split("-")[-1]:
                year = fid.split("-")[-1][2:]  # e.g., Q12024 -> 2024
            else:
                continue

            if year not in filings_by_year:
                filings_by_year[year] = []
            filings_by_year[year].append(fid)

        years = sorted(filings_by_year.keys())

        # Sample pairs across adjacent years
        for i, year1 in enumerate(years[:-1]):
            year2 = years[i + 1]

            for filing1 in filings_by_year[year1]:
                for filing2 in filings_by_year[year2]:
                    nodes1 = [n for n in self.nodes_by_filing[filing1] if n.type == NodeType.TEXT_SECTION]
                    nodes2 = [n for n in self.nodes_by_filing[filing2] if n.type == NodeType.TEXT_SECTION]

                    if not nodes1 or not nodes2:
                        continue

                    # Sample pairs with embedding similarity
                    for _ in range(min(5, n_samples // 10)):
                        n1 = random.choice(nodes1)

                        if n1.id not in self.embeddings:
                            continue

                        # Find similar node in other filing
                        candidates = [(n, cosine_similarity(self.embeddings[n1.id], self.embeddings[n.id]))
                                     for n in nodes2 if n.id in self.embeddings]
                        candidates.sort(key=lambda x: x[1], reverse=True)

                        if not candidates:
                            continue

                        n2, sim = candidates[0]

                        # Use LLM to verify temporal link
                        label, confidence = self._annotate_temporal(
                            n1, n2,
                            n1.metadata.period or filing1.split("-")[-1],
                            n2.metadata.period or filing2.split("-")[-1]
                        )

                        annotations.append(GoldEdge(
                            source_id=n1.id,
                            target_id=n2.id,
                            edge_type=EdgeType.TEMPORAL_NEXT,
                            label=label,
                            annotator="llm",
                            confidence=confidence,
                            notes=f"Similarity: {sim:.3f}, {filing1} -> {filing2}",
                        ))

                        if len(annotations) >= n_samples:
                            break

                    if len(annotations) >= n_samples:
                        break
                if len(annotations) >= n_samples:
                    break
            if len(annotations) >= n_samples:
                break

        return GoldStandard(
            expert_name="TemporalLinker",
            edge_type=EdgeType.TEMPORAL_NEXT,
            annotations=annotations,
            metadata={"n_samples": len(annotations)},
        )

    def _annotate_temporal(self, node1: Node, node2: Node, period1: str, period2: str) -> tuple[bool, float]:
        """Use LLM to annotate temporal relationship."""
        result = self.llm.extract_temporal_links(
            node1.text[:1000],
            node2.text[:1000],
            period1,
            period2,
        )
        return result.get("is_related", False), result.get("confidence", 0.5)

    def generate_table_text_gold(self, n_samples: int = 100) -> GoldStandard:
        """Generate gold standard for TableTextConnector."""
        logger.info("Generating TableTextConnector gold standard...")
        annotations = []

        # Get table and text nodes
        table_nodes = (
            self.nodes_by_type.get(NodeType.TABLE_ROW, []) +
            self.nodes_by_type.get(NodeType.FINANCIAL_LINE, [])
        )
        text_nodes = self.nodes_by_type.get(NodeType.TEXT_SECTION, [])

        # Group by filing
        for filing_id in tqdm(list(self.nodes_by_filing.keys())[:8], desc="Table-Text pairs"):
            filing_tables = [n for n in table_nodes if n.metadata.filing_id == filing_id][:20]
            filing_texts = [n for n in text_nodes if n.metadata.filing_id == filing_id][:30]

            if not filing_tables or not filing_texts:
                continue

            for table_node in filing_tables[:n_samples // 12]:
                # Find text nodes that might explain this table
                for text_node in random.sample(filing_texts, min(3, len(filing_texts))):
                    label, confidence = self._annotate_table_text(table_node, text_node)

                    annotations.append(GoldEdge(
                        source_id=text_node.id,
                        target_id=table_node.id,
                        edge_type=EdgeType.DISCUSSES,
                        label=label,
                        annotator="llm",
                        confidence=confidence,
                        notes=f"Filing: {filing_id}",
                    ))

                    if len(annotations) >= n_samples:
                        break
                if len(annotations) >= n_samples:
                    break
            if len(annotations) >= n_samples:
                break

        return GoldStandard(
            expert_name="TableTextConnector",
            edge_type=EdgeType.DISCUSSES,
            annotations=annotations,
            metadata={"n_samples": len(annotations)},
        )

    def _annotate_table_text(self, table_node: Node, text_node: Node) -> tuple[bool, float]:
        """Use LLM to annotate table-text connection."""
        prompt = f"""Determine if the TEXT explains or discusses the TABLE data.

TABLE DATA:
{table_node.text[:800]}

TEXT:
{text_node.text[:1200]}

Does the text explain, discuss, or reference the specific data in the table?
Output JSON: {{"discusses": true/false, "confidence": 0.0-1.0, "connection": "brief explanation if yes"}}"""

        try:
            response = self.llm.generate(prompt, max_tokens=200, temperature=0.1)
            result = self.llm._parse_json_object(response)
            return result.get("discusses", False), result.get("confidence", 0.5)
        except Exception as e:
            logger.debug(f"Table-text annotation failed: {e}")
            return False, 0.5

    def generate_semantic_gold(self, n_samples: int = 100) -> GoldStandard:
        """Generate gold standard for SemanticBridge."""
        logger.info("Generating SemanticBridge gold standard...")
        annotations = []

        text_nodes = self.nodes_by_type.get(NodeType.TEXT_SECTION, [])

        # Sample pairs at different similarity levels
        similarity_buckets = [
            (0.9, 1.0, "high"),    # Very similar
            (0.7, 0.9, "medium"),  # Moderately similar
            (0.4, 0.7, "low"),     # Somewhat similar
        ]

        for min_sim, max_sim, bucket_name in similarity_buckets:
            bucket_samples = n_samples // 3
            bucket_count = 0

            # Sample from different filings
            for filing_id in self.nodes_by_filing:
                if bucket_count >= bucket_samples:
                    break

                filing_texts = [n for n in text_nodes
                               if n.metadata.filing_id == filing_id and n.id in self.embeddings][:50]

                for i, node1 in enumerate(filing_texts):
                    for node2 in filing_texts[i+1:]:
                        sim = cosine_similarity(
                            self.embeddings[node1.id],
                            self.embeddings[node2.id]
                        )

                        if min_sim <= sim < max_sim:
                            # Use LLM to verify semantic similarity
                            label, confidence = self._annotate_semantic(node1, node2, sim)

                            annotations.append(GoldEdge(
                                source_id=node1.id,
                                target_id=node2.id,
                                edge_type=EdgeType.SEMANTICALLY_SIMILAR,
                                label=label,
                                annotator="llm",
                                confidence=confidence,
                                notes=f"Embedding sim: {sim:.3f}, bucket: {bucket_name}",
                            ))
                            bucket_count += 1

                            if bucket_count >= bucket_samples:
                                break
                    if bucket_count >= bucket_samples:
                        break

        return GoldStandard(
            expert_name="SemanticBridge",
            edge_type=EdgeType.SEMANTICALLY_SIMILAR,
            annotations=annotations,
            metadata={"n_samples": len(annotations)},
        )

    def _annotate_semantic(self, node1: Node, node2: Node, embedding_sim: float) -> tuple[bool, float]:
        """Use LLM to annotate semantic similarity."""
        result = self.llm.extract_semantic_relationships(
            node1.text[:1000],
            node2.text[:1000],
        )

        rel_type = result.get("relationship_type", "unrelated")
        llm_sim = result.get("similarity_score", 0.0)

        # Consider similar if LLM says same_topic, detail_summary, or high similarity
        is_similar = rel_type in ["same_topic", "detail_summary"] or llm_sim >= 0.7

        # Combine LLM and embedding confidence
        combined_confidence = (llm_sim + embedding_sim) / 2

        return is_similar, combined_confidence


def main():
    parser = argparse.ArgumentParser(description="Generate gold standard datasets")
    parser.add_argument("--expert", type=str, default="all",
                       choices=["all", "crossref", "causal", "temporal", "table_text", "semantic"],
                       help="Which expert to generate gold data for")
    parser.add_argument("--samples", type=int, default=100,
                       help="Number of samples per expert")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility")

    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    random.seed(args.seed)
    np.random.seed(args.seed)

    # Load data
    logger.info("Loading nodes and embeddings...")
    nodes = load_all_nodes()
    embeddings = load_all_embeddings()

    if not nodes:
        logger.error("No nodes found. Run fetch_filings.py first.")
        return

    # Check LLM availability
    llm = LLMClient()
    if not llm.is_available():
        logger.error("vLLM server not available. Start with: ./scripts/start_vllm.sh")
        return

    logger.info("LLM server available")

    # Create generator
    generator = GoldStandardGenerator(nodes, embeddings)

    # Generate gold standards
    experts_to_generate = {
        "crossref": ("CrossReferenceHunter", generator.generate_crossref_gold),
        "causal": ("CausalChainBuilder", generator.generate_causal_gold),
        "temporal": ("TemporalLinker", generator.generate_temporal_gold),
        "table_text": ("TableTextConnector", generator.generate_table_text_gold),
        "semantic": ("SemanticBridge", generator.generate_semantic_gold),
    }

    if args.expert == "all":
        experts = list(experts_to_generate.keys())
    else:
        experts = [args.expert]

    for expert_key in experts:
        expert_name, generate_fn = experts_to_generate[expert_key]
        logger.info(f"\n{'='*60}")
        logger.info(f"Generating gold standard for {expert_name}...")
        logger.info(f"{'='*60}")

        try:
            gold = generate_fn(args.samples)

            # Save gold standard
            output_path = save_gold_standard(gold)

            # Print statistics
            n_positive = sum(1 for a in gold.annotations if a.label)
            n_negative = sum(1 for a in gold.annotations if not a.label)
            avg_confidence = sum(a.confidence or 0.5 for a in gold.annotations) / len(gold.annotations) if gold.annotations else 0

            logger.info(f"  Total annotations: {len(gold.annotations)}")
            logger.info(f"  Positive labels: {n_positive}")
            logger.info(f"  Negative labels: {n_negative}")
            logger.info(f"  Average confidence: {avg_confidence:.3f}")
            logger.info(f"  Saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate gold standard for {expert_name}: {e}")
            import traceback
            traceback.print_exc()

    logger.info("\nGold standard generation complete!")


if __name__ == "__main__":
    main()
