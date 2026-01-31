"""Commutator computation for OpMech-GraphRAG.

The commutator measures divergence between two operators A and B:
    Δ(q, h) = w_E · Δ_E + w_V · Δ_V + w_A · Δ_A + w_C · Δ_C

Where:
    - Δ_E = Evidence Divergence (what nodes were retrieved?)
    - Δ_V = Structural Divergence (what sections/types were covered?)
    - Δ_A = Answer Divergence (how different are the conclusions?)
    - Δ_C = Confidence Divergence (how confident is each path?)

Default weights: w_E = 0.30, w_V = 0.20, w_A = 0.30, w_C = 0.20
"""

from typing import Callable, Dict, List, Set

import numpy as np

from src.opmech.data_classes import BeliefState, CommutatorResult, Node


def compute_evidence_divergence(evidence_A: Set[str], evidence_B: Set[str]) -> float:
    """
    Compute evidence divergence using Jaccard distance.

    Δ_E = 1 - |E_A ∩ E_B| / |E_A ∪ E_B|

    Range: [0, 1]
        - 0 = identical evidence sets
        - 1 = completely disjoint evidence sets

    Args:
        evidence_A: Set of node IDs from operator A
        evidence_B: Set of node IDs from operator B

    Returns:
        Jaccard distance between the two sets
    """
    if not evidence_A and not evidence_B:
        return 0.0

    intersection = len(evidence_A & evidence_B)
    union = len(evidence_A | evidence_B)

    return 1.0 - (intersection / union) if union > 0 else 0.0


def compute_structural_divergence(
    evidence_A: List[Node],
    evidence_B: List[Node]
) -> float:
    """
    Compute structural divergence using Jaccard distance on structural attributes.

    Δ_V = 1 - |V_A ∩ V_B| / |V_A ∪ V_B|

    Where V = {(section, type, period)} tuples

    Range: [0, 1]
        - 0 = same structural coverage
        - 1 = completely different structural coverage

    Args:
        evidence_A: List of nodes from operator A
        evidence_B: List of nodes from operator B

    Returns:
        Jaccard distance between structural attribute sets
    """
    def extract_structure(nodes: List[Node]) -> Set[tuple]:
        return {
            (
                n.metadata.get('section', 'unknown'),
                n.type,
                n.metadata.get('period', 'unknown')
            )
            for n in nodes
        }

    V_A = extract_structure(evidence_A)
    V_B = extract_structure(evidence_B)

    if not V_A and not V_B:
        return 0.0

    intersection = len(V_A & V_B)
    union = len(V_A | V_B)

    return 1.0 - (intersection / union) if union > 0 else 0.0


def compute_answer_divergence(
    answer_A: str,
    answer_B: str,
    embed_fn: Callable[[str], np.ndarray]
) -> float:
    """
    Compute answer divergence using cosine distance between embeddings.

    Δ_A = 1 - cos(φ(a_A), φ(a_B))

    Where φ is the embedding function (FinBERT)

    Range: [0, 1] (assuming normalized embeddings)
        - 0 = identical semantic meaning
        - 1 = completely opposite meaning

    Args:
        answer_A: Answer string from operator A
        answer_B: Answer string from operator B
        embed_fn: Embedding function (e.g., FinBERT)

    Returns:
        Cosine distance between answer embeddings
    """
    if not answer_A or not answer_B:
        return 0.5  # Neutral if either answer is empty

    emb_A = embed_fn(answer_A)
    emb_B = embed_fn(answer_B)

    # Normalize
    norm_A = np.linalg.norm(emb_A)
    norm_B = np.linalg.norm(emb_B)

    if norm_A == 0 or norm_B == 0:
        return 0.5

    emb_A = emb_A / norm_A
    emb_B = emb_B / norm_B

    cosine_sim = np.dot(emb_A, emb_B)

    # Clamp to [0, 1] range
    return max(0.0, min(1.0, 1.0 - cosine_sim))


def compute_confidence_divergence(
    evidence_A: List[Node],
    evidence_B: List[Node],
    edge_confidences_A: List[float],
    edge_confidences_B: List[float]
) -> float:
    """
    Compute confidence divergence capturing disagreement in confidence levels.

    Δ_C captures two aspects:
        1. Path confidence difference: |mean(conf_A) - mean(conf_B)|
        2. Confidence variance ratio: measures if one path is certain while other is uncertain

    Formula:
        Δ_C = α · |μ_A - μ_B| + β · |σ_A - σ_B| / max(σ_A, σ_B, ε)

    Where:
        - μ_A, μ_B = mean confidence of edges in path A, B
        - σ_A, σ_B = std dev of confidence in path A, B
        - α = 0.6, β = 0.4 (weights)
        - ε = 0.01 (small constant to avoid division by zero)

    Range: [0, 1]
        - 0 = both paths equally confident
        - 1 = one path very confident, other very uncertain

    Args:
        evidence_A: List of nodes from operator A (not used but kept for consistency)
        evidence_B: List of nodes from operator B (not used but kept for consistency)
        edge_confidences_A: List of edge confidences from operator A traversal
        edge_confidences_B: List of edge confidences from operator B traversal

    Returns:
        Confidence divergence score
    """
    if not edge_confidences_A:
        edge_confidences_A = [0.5]  # Default if no edges
    if not edge_confidences_B:
        edge_confidences_B = [0.5]

    # Mean confidence
    mu_A = np.mean(edge_confidences_A)
    mu_B = np.mean(edge_confidences_B)

    # Std dev of confidence
    sigma_A = np.std(edge_confidences_A) if len(edge_confidences_A) > 1 else 0.0
    sigma_B = np.std(edge_confidences_B) if len(edge_confidences_B) > 1 else 0.0

    # Mean difference component
    mean_diff = abs(mu_A - mu_B)

    # Variance difference component (normalized)
    epsilon = 0.01
    max_sigma = max(sigma_A, sigma_B, epsilon)
    variance_diff = abs(sigma_A - sigma_B) / max_sigma

    # Weighted combination
    alpha, beta = 0.6, 0.4
    delta_C = alpha * mean_diff + beta * variance_diff

    # Clamp to [0, 1]
    return max(0.0, min(1.0, delta_C))


def compute_operator_score(belief: BeliefState) -> float:
    """
    Compute overall quality score for an operator's output.

    Score = confidence_score * coverage_score * diversity_score

    Where:
        - confidence_score = mean edge confidence (0-1)
        - coverage_score = min(1, |evidence| / target_k) (0-1)
        - diversity_score = unique_sections / total_evidence (0-1)

    Range: [0, 1]

    Args:
        belief: Belief state from operator execution

    Returns:
        Quality score for the operator's output
    """
    if not belief.evidence:
        return 0.0

    # Confidence score: mean of edge confidences
    if belief.edge_confidences:
        confidence_score = np.mean(belief.edge_confidences)
    else:
        confidence_score = 0.5

    # Coverage score: did we find enough evidence?
    target_k = 10  # Target number of evidence nodes
    coverage_score = min(1.0, len(belief.evidence) / target_k)

    # Diversity score: are we covering multiple sections?
    sections = {n.metadata.get('section', 'unknown') for n in belief.evidence}
    diversity_score = len(sections) / len(belief.evidence) if belief.evidence else 0.0

    # Combined score
    return confidence_score * coverage_score * (0.5 + 0.5 * diversity_score)


def compute_commutator(
    belief_A: BeliefState,
    belief_B: BeliefState,
    embed_fn: Callable[[str], np.ndarray],
    weights: Dict[str, float] = None,
    hop: int = 1
) -> CommutatorResult:
    """
    Compute the full commutator proxy for operator divergence.

    Formula:
        Δ(q, h) = w_E · Δ_E + w_V · Δ_V + w_A · Δ_A + w_C · Δ_C

    Also computes operator scores:
        score_A = mean(edge_confidences_A) * coverage_A * relevance_A
        score_B = mean(edge_confidences_B) * coverage_B * relevance_B

    Args:
        belief_A: Belief state from operator A (structure-first)
        belief_B: Belief state from operator B (narrative-first)
        embed_fn: Embedding function for answer divergence
        weights: Optional custom weights for divergence components
        hop: Current hop number

    Returns:
        CommutatorResult with all divergence scores
    """
    # Default weights
    if weights is None:
        weights = {
            'evidence': 0.30,
            'structural': 0.20,
            'answer': 0.30,
            'confidence': 0.20
        }

    # Extract evidence node IDs
    evidence_ids_A = {n.id for n in belief_A.evidence}
    evidence_ids_B = {n.id for n in belief_B.evidence}

    # Compute individual divergences
    delta_E = compute_evidence_divergence(evidence_ids_A, evidence_ids_B)
    delta_V = compute_structural_divergence(belief_A.evidence, belief_B.evidence)
    delta_A = compute_answer_divergence(belief_A.answer, belief_B.answer, embed_fn)
    delta_C = compute_confidence_divergence(
        belief_A.evidence,
        belief_B.evidence,
        belief_A.edge_confidences,
        belief_B.edge_confidences
    )

    # Combined commutator
    combined = (
        weights['evidence'] * delta_E +
        weights['structural'] * delta_V +
        weights['answer'] * delta_A +
        weights['confidence'] * delta_C
    )

    # Compute operator scores
    operator_A_score = compute_operator_score(belief_A)
    operator_B_score = compute_operator_score(belief_B)

    return CommutatorResult(
        delta_E=delta_E,
        delta_V=delta_V,
        delta_A=delta_A,
        delta_C=delta_C,
        combined=combined,
        weights=weights,
        hop=hop,
        operator_A_score=operator_A_score,
        operator_B_score=operator_B_score
    )
