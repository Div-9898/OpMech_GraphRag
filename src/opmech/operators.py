"""Operators for OpMech-GraphRAG.

Two operators traverse the graph from different starting points:

OperatorA (Structure-First): Numbers → Narrative
    - Seeds from FINANCIAL_LINE nodes (quantitative data)
    - Uses DYNAMIC query term extraction (no hardcoded segments)
    - Commutator-guided search expansion when divergence is high
    - Traverses via structure-oriented edges
    - Reaches explanatory text through EXPLAINS_LINE_ITEM

OperatorB (Narrative-First): Narrative → Numbers
    - Seeds from TEXT_SECTION and NOTE nodes (qualitative data)
    - Traverses via semantic/causal edges
    - Reaches financial data through DISCUSSES, CAUSED_BY

EDGE CONFIDENCE INTEGRATION:
    - Traversal prefers high-confidence edges (confidence-weighted BFS)
    - Path confidence = product of edge confidences along path
    - Evidence ranking combines query relevance AND path confidence

COMMUTATOR-GUIDED REFINEMENT:
    - When Δ_E (evidence divergence) is high, operators expand search
    - When operator_score is low, try harder to find XBRL data
    - Graph-driven discovery: let the graph tell us what data exists
"""

import re
from typing import Callable, List, Optional, Tuple, Set

import numpy as np
from loguru import logger

from src.opmech.data_classes import (
    BeliefState,
    CommutatorResult,
    Node,
    TraversalStrategy,
    TraversedNode,
)
from src.opmech.graph_interface import KnowledgeGraphInterface
from src.opmech.edge_scoring import create_scorer, EdgeScorer, TraversalContext, EdgeScore


# Import XBRL constants
from src.opmech.constants import QUERY_TO_XBRL_MAP, FINANCIAL_TERM_MAPPINGS, FINANCIAL_CONCEPT_MAP, expand_query_to_xbrl

# Keywords for detecting query types (generic financial terms, not company-specific)
REVENUE_KEYWORDS = ["revenue", "sales", "net sales", "total revenue", "total net sales"]
EXPENSE_KEYWORDS = ["expense", "cost", "r&d", "research and development", "operating expense"]
PROFIT_KEYWORDS = ["profit", "income", "earnings", "margin", "net income", "gross margin"]
MARGIN_KEYWORDS = ["margin", "gross margin", "operating margin", "net margin", "profit margin", "gross profit"]

# =============================================================================
# FIX 4: Risk Factor Detection Keywords
# =============================================================================

RISK_KEYWORDS = [
    "risk", "risks", "risk factors", "threats", "challenges", "concerns",
    "vulnerabilities", "exposure", "uncertainties", "headwinds"
]

# Keywords to search for in TEXT_SECTION nodes for risk-related content
RISK_CONTENT_KEYWORDS = [
    "supply chain", "competition", "regulatory", "china", "foreign exchange",
    "cybersecurity", "concentration", "dependence", "litigation", "compliance",
    "tariff", "trade", "labor", "workforce", "economic", "geopolitical",
    "intellectual property", "patent", "infringement", "product liability",
    "market risk", "credit risk", "liquidity", "debt", "financing",
    "climate", "environmental", "pandemic", "epidemic", "disruption"
]

# Financial risk-related XBRL concepts
FINANCIAL_RISK_XBRL = [
    "LongTermDebt", "TotalLiabilities", "DebtCurrent", "ShortTermDebt",
    "InterestExpense", "ContingentLiabilities", "LossContingencies"
]


def is_risk_query(query: str) -> bool:
    """
    Check if the query is asking about risk factors.

    FIX 4: Risk queries require special handling to include Item 1A
    and narrative risk content, not just financial numbers.

    Args:
        query: User query string

    Returns:
        True if query is about risks/risk factors
    """
    query_lower = query.lower()
    return any(kw in query_lower for kw in RISK_KEYWORDS)

# Stop words to filter out during query term extraction
STOP_WORDS = {
    "what", "is", "the", "a", "an", "of", "in", "for", "to", "and", "or", "how",
    "has", "have", "had", "was", "were", "been", "be", "are", "will", "would",
    "could", "should", "can", "do", "does", "did", "this", "that", "these",
    "those", "it", "its", "with", "from", "by", "on", "at", "as", "about",
    "like", "over", "between", "through", "during", "before", "after", "above",
    "below", "up", "down", "out", "off", "into", "onto", "upon", "than", "too",
    "very", "just", "also", "now", "here", "there", "where", "when", "why",
    "which", "who", "whom", "whose", "tell", "me", "us", "show", "give",
    "apple", "inc", "company", "fiscal", "year", "quarter", "fy", "q1", "q2", "q3", "q4",
}


def extract_query_terms(query: str) -> List[str]:
    """
    Extract meaningful terms from query for dynamic graph search.

    This is domain-agnostic - no hardcoded segment names.
    Extracts financial terms and entity names dynamically.

    Args:
        query: User query string

    Returns:
        List of meaningful search terms
    """
    # Tokenize and clean
    words = re.findall(r'\b[a-zA-Z]+\b', query.lower())

    # Filter stop words and short words
    terms = [w for w in words if w not in STOP_WORDS and len(w) > 2]

    # Also extract multi-word phrases that might be important
    # Look for capitalized words in original query (likely entity names)
    capitalized = re.findall(r'\b[A-Z][a-zA-Z]+\b', query)
    for cap in capitalized:
        cap_lower = cap.lower()
        if cap_lower not in STOP_WORDS and cap_lower not in terms:
            terms.append(cap_lower)

    # Extract numbers that might be years or values
    years = re.findall(r'\b(20\d{2})\b', query)
    terms.extend(years)

    # Deduplicate while preserving order
    seen = set()
    unique_terms = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique_terms.append(t)

    return unique_terms


def extract_fiscal_year(query: str) -> Optional[str]:
    """Extract fiscal year from query string."""
    # Match patterns like FY2023, FY 2023, fiscal year 2023, fiscal 2023
    match = re.search(r'FY\s*(\d{4})|fiscal\s*(?:year\s*)?(\d{4})', query, re.IGNORECASE)
    if match:
        return match.group(1) or match.group(2)
    # Also match plain year mentions
    match = re.search(r'\b(20\d{2})\b', query)
    if match:
        return match.group(1)
    return None


class OperatorA:
    """
    Structure-First Operator (Numbers → Narrative)

    Workflow:
        1. Seed from FINANCIAL_LINE nodes (quantitative data)
        2. Use DYNAMIC query term extraction (no hardcoded segments)
        3. Commutator-guided search expansion when divergence is high
        4. Traverse via structure-oriented edges, WEIGHTED BY EDGE CONFIDENCE
        5. Reach explanatory text through EXPLAINS_LINE_ITEM

    EDGE CONFIDENCE INTEGRATION:
        - Traversal prefers high-confidence edges (confidence-weighted BFS)
        - Path confidence = product of edge confidences along path
        - Evidence ranking combines query relevance AND path confidence

    COMMUTATOR-GUIDED REFINEMENT:
        - Tracks previous hop's commutator result
        - When Δ_E is high or operator_score is low, expands XBRL search
        - Uses graph-driven discovery to find related financial data
    """

    def __init__(
        self,
        graph: KnowledgeGraphInterface,
        embed_fn: Callable[[str], np.ndarray]
    ):
        """
        Initialize Operator A.

        Args:
            graph: Knowledge graph interface
            embed_fn: Embedding function for queries
        """
        self.graph = graph
        self.embed_fn = embed_fn
        self.name = "OperatorA"
        self._bridge_seeds: List[str] = []  # For convergence pressure
        self._last_commutator: Optional[CommutatorResult] = None  # For commutator-guided refinement
        self._previous_evidence_ids: Set[str] = set()  # Track what we found before

    def add_bridge_seeds(self, seed_ids: List[str]):
        """Add bridge seeds from convergence pressure mechanism."""
        self._bridge_seeds = seed_ids

    def set_commutator_feedback(self, commutator: CommutatorResult):
        """
        Set commutator feedback from previous hop.

        This enables commutator-guided refinement of the search strategy.

        Args:
            commutator: CommutatorResult from previous hop
        """
        self._last_commutator = commutator

    def _should_expand_search(self) -> bool:
        """
        Determine if we should expand XBRL search based on commutator feedback.

        Returns True when:
        - Δ_E (evidence divergence) is high (operators found different things)
        - operator_A_score is low (we didn't find good XBRL data)
        - Previous evidence had few FINANCIAL_LINE nodes
        """
        if self._last_commutator is None:
            return False

        comm = self._last_commutator

        # High evidence divergence - operators found different things
        if comm.delta_E > 0.7:
            logger.debug(f"{self.name}: Expanding search due to high Δ_E={comm.delta_E:.3f}")
            return True

        # Low operator score - we didn't find good evidence
        if comm.operator_A_score < 0.4:
            logger.debug(f"{self.name}: Expanding search due to low operator_A_score={comm.operator_A_score:.3f}")
            return True

        # High overall divergence
        if comm.combined > 0.6:
            logger.debug(f"{self.name}: Expanding search due to high combined Δ={comm.combined:.3f}")
            return True

        return False

    def _find_direct_financial_seeds(self, query: str, expand_search: bool = False) -> List[Node]:
        """
        Find FINANCIAL_LINE nodes using DYNAMIC query term extraction.

        FIX 8: Uses semantic expansion to find XBRL concepts for abstract terms
        like "profitability" which maps to NetIncome, GrossProfit, etc.

        This method is domain-agnostic - no hardcoded segment names.
        Uses query terms to search the graph dynamically.

        Args:
            query: User query string
            expand_search: If True, broaden search (from commutator feedback)

        Returns:
            List of FINANCIAL_LINE nodes matching the query
        """
        query_lower = query.lower()

        # FIX 8: Use semantic expansion to find XBRL concepts
        expanded_xbrl_concepts = expand_query_to_xbrl(query)
        if expanded_xbrl_concepts:
            logger.info(f"{self.name}: FIX 8 - Expanded query to XBRL concepts: {expanded_xbrl_concepts[:5]}...")

        # Extract query terms dynamically (no hardcoded segments)
        query_terms = extract_query_terms(query)
        logger.debug(f"{self.name}: Extracted query terms: {query_terms}")

        # Extract period filter
        fiscal_year = extract_fiscal_year(query)
        period_filter = fiscal_year if fiscal_year else None

        # Get query embedding for similarity search
        query_embedding = self.embed_fn(query)

        # Use dynamic search - this searches graph based on extracted terms
        nodes = self.graph.search_financial_dynamic(
            query_terms=query_terms,
            query_embedding=query_embedding,
            period_filter=period_filter,
            limit=10 if not expand_search else 15,
            min_similarity=0.3 if not expand_search else 0.2,
            expand_search=expand_search
        )

        if nodes:
            logger.info(f"{self.name}: Found {len(nodes)} nodes via dynamic search (expand={expand_search})")

        # FIX 8: If semantic expansion found XBRL concepts, search for them
        if expanded_xbrl_concepts and len(nodes) < 5:
            try:
                concept_nodes = self.graph.search_financial_by_concept(
                    concepts=expanded_xbrl_concepts[:10],  # Use top 10 expanded concepts
                    period_filter=period_filter,
                    limit=7
                )
                if concept_nodes:
                    nodes.extend(concept_nodes)
                    logger.info(f"{self.name}: FIX 8 - Found {len(concept_nodes)} nodes via semantic expansion")
            except AttributeError:
                logger.debug(f"{self.name}: search_financial_by_concept not available")

        # If dynamic search found few results, try XBRL concept mapping as fallback
        if len(nodes) < 3:
            # Detect financial query type for fallback
            is_revenue_query = any(kw in query_lower for kw in REVENUE_KEYWORDS)
            is_margin_query = any(kw in query_lower for kw in MARGIN_KEYWORDS)
            is_profit_query = any(kw in query_lower for kw in PROFIT_KEYWORDS)

            if is_margin_query:
                relevant_concepts = self._get_relevant_xbrl_concepts(query_lower)
                if relevant_concepts:
                    try:
                        concept_nodes = self.graph.search_financial_by_concept(
                            concepts=relevant_concepts,
                            period_filter=period_filter,
                            limit=5
                        )
                        nodes.extend(concept_nodes)
                    except AttributeError:
                        pass

            elif is_revenue_query:
                try:
                    revenue_nodes = self.graph.find_revenue_nodes(period_filter=period_filter, limit=5)
                    nodes.extend(revenue_nodes)
                except AttributeError:
                    pass

            elif is_profit_query:
                try:
                    profit_nodes = self.graph.find_nodes_by_xbrl_keyword(
                        keyword="income",
                        period_filter=period_filter,
                        limit=5
                    )
                    nodes.extend(profit_nodes)
                except AttributeError:
                    pass

        # If still few results and we're expanding, use graph-driven discovery
        if len(nodes) < 3 and expand_search and self._previous_evidence_ids:
            logger.debug(f"{self.name}: Using graph-driven discovery from {len(self._previous_evidence_ids)} previous nodes")
            related_nodes = self.graph.search_related_financial_nodes(
                seed_node_ids=list(self._previous_evidence_ids)[:10],
                limit=5
            )
            nodes.extend(related_nodes)

        # Deduplicate nodes by ID
        seen_ids = set()
        unique_nodes = []
        for node in nodes:
            if node.id not in seen_ids:
                seen_ids.add(node.id)
                unique_nodes.append(node)

        return unique_nodes

    def _get_relevant_xbrl_concepts(self, query_lower: str) -> List[str]:
        """
        Get relevant XBRL concepts from query using QUERY_TO_XBRL_MAP.

        Args:
            query_lower: Lowercase query string

        Returns:
            List of XBRL concept names to search for
        """
        relevant_concepts = []
        for term, concepts in QUERY_TO_XBRL_MAP.items():
            if term in query_lower:
                relevant_concepts.extend(concepts)
        return list(set(relevant_concepts))

    def _extract_financial_terms(self, query: str) -> List[str]:
        """
        Extract financial terms from query for targeted search.

        Args:
            query: User query string

        Returns:
            List of search terms including XBRL-friendly variations
        """
        query_lower = query.lower()
        found_terms = []

        for key, variations in FINANCIAL_TERM_MAPPINGS.items():
            if key in query_lower:
                found_terms.extend(variations)

        # Also add the raw query for semantic fallback
        found_terms.append(query)

        return list(set(found_terms))

    def execute(
        self,
        query: str,
        strategy: TraversalStrategy,
        other_operator_evidence: Optional[set] = None
    ) -> BeliefState:
        """
        Execute structure-first traversal with reward/penalty scoring.

        COMMUTATOR-GUIDED: Uses feedback from previous hop to decide
        whether to expand XBRL search.

        Args:
            query: User query string
            strategy: Traversal strategy from controller
            other_operator_evidence: Optional set of node IDs from other operator for convergence

        Returns:
            BeliefState with evidence and metadata
        """
        logger.info(f"{self.name}: Starting execution (hop {strategy.current_hop})")

        # Check if we should expand search based on commutator feedback
        expand_search = self._should_expand_search()
        if expand_search:
            logger.info(f"{self.name}: Expanding XBRL search due to commutator feedback")

        # Embed query
        query_embedding = self.embed_fn(query)

        # Create scorer with appropriate weights
        scorer, context = create_scorer(
            query_embedding=query_embedding,
            embed_fn=self.embed_fn,
            explore_weight=strategy.explore_weight,
            other_operator_nodes=other_operator_evidence
        )

        # Use dynamic XBRL search with commutator-guided expansion
        direct_seeds = self._find_direct_financial_seeds(query, expand_search=expand_search)

        if direct_seeds:
            # Use direct seeds as primary
            seeds = direct_seeds
            logger.info(f"{self.name}: Using {len(seeds)} dynamic XBRL seeds (expand={expand_search})")
        else:
            # Fall back to embedding-based search
            seeds = self.graph.search_by_type(
                query_embedding=query_embedding,
                node_types=["FINANCIAL_LINE"],
                top_k=strategy.seeds_per_operator
            )

        seed_ids = [n.id for n in seeds]

        # Add shared seeds from other operator to ensure overlap (BUG 3 FIX)
        if other_operator_evidence:
            shared_ids = list(other_operator_evidence)[:3]  # Add up to 3 shared seeds
            seed_ids.extend(shared_ids)
            logger.debug(f"{self.name}: Added {len(shared_ids)} shared seeds for overlap")

        # Add bridge seeds if available (convergence pressure)
        if self._bridge_seeds:
            seed_ids.extend(self._bridge_seeds)
            logger.debug(f"{self.name}: Added {len(self._bridge_seeds)} bridge seeds")
            self._bridge_seeds = []  # Clear after use

        logger.debug(f"{self.name}: Total {len(seed_ids)} seed nodes")

        if not seed_ids:
            # Fallback: try any node type
            logger.warning(f"{self.name}: No FINANCIAL_LINE seeds, trying fallback")
            seeds = self.graph.search_by_type(
                query_embedding=query_embedding,
                node_types=["FINANCIAL_LINE", "NOTE", "TEXT_SECTION"],
                top_k=strategy.seeds_per_operator
            )
            seed_ids = [n.id for n in seeds]

        # Get dynamic edge types based on explore weight
        edge_types = self._get_edge_types(strategy.explore_weight, strategy.current_hop)

        # Compute min_edge_score based on explore weight AND hop
        # Base: EXPLOIT: 0.55, EXPLORE: 0.35
        # Hop 1 is stricter (+0.1) to prevent early explosion
        base_score = 0.55 - 0.20 * strategy.explore_weight
        hop_adjustment = 0.1 if strategy.current_hop == 1 else 0.0
        min_edge_score = base_score + hop_adjustment

        # Traverse graph WITH SCORING
        traversed_nodes, edges, edge_scores = self.graph.traverse_with_scoring(
            seed_ids=seed_ids,
            edge_types=edge_types,
            hops=strategy.max_hops,
            max_per_hop=strategy.nodes_per_hop,
            min_confidence=strategy.min_edge_confidence,
            confidence_decay=strategy.confidence_decay,
            scorer=scorer,
            context=context,
            min_edge_score=min_edge_score
        )

        logger.info(f"{self.name}: Traversed {len(traversed_nodes)} nodes, {len(edges)} edges")

        # Log score statistics
        if edge_scores:
            avg_score = np.mean([s.total_score for s in edge_scores])
            logger.debug(f"{self.name}: Avg edge score = {avg_score:.3f}")
            avg_rewards = {
                "domain_crossing": np.mean([s.domain_crossing_reward for s in edge_scores]),
                "query_relevance": np.mean([s.query_relevance_reward for s in edge_scores]),
                "convergence": np.mean([s.convergence_reward for s in edge_scores]),
            }
            avg_penalties = {
                "semantic_drift": np.mean([s.semantic_drift_penalty for s in edge_scores]),
                "domain_isolation": np.mean([s.domain_isolation_penalty for s in edge_scores]),
            }
            logger.debug(f"{self.name}: Rewards = {avg_rewards}")
            logger.debug(f"{self.name}: Penalties = {avg_penalties}")

        # Log node type distribution
        type_counts = {}
        for tn in traversed_nodes:
            t = tn.node.type
            type_counts[t] = type_counts.get(t, 0) + 1
        logger.debug(f"{self.name}: Node types = {type_counts}")

        # Collect edge confidences (for delta_C computation)
        edge_confidences = [e.confidence for e in edges] if edges else [0.5]

        # Select top-k evidence by COMBINED score (relevance + path confidence)
        evidence, evidence_confidences = self._rank_evidence_with_confidence(
            traversed_nodes=traversed_nodes,
            query_embedding=query_embedding,
            top_k=strategy.top_k_evidence,
            relevance_weight=strategy.relevance_weight,
            confidence_weight=strategy.confidence_weight
        )

        # Balance evidence to include both FINANCIAL_LINE and narrative nodes
        evidence = self._balance_evidence(evidence, strategy.top_k_evidence)

        # Compute mean path confidence
        mean_path_conf = np.mean([tn.path_confidence for tn in traversed_nodes]) if traversed_nodes else 0.0

        # Log evidence composition
        ev_types = {}
        for n in evidence:
            ev_types[n.type] = ev_types.get(n.type, 0) + 1
        logger.debug(f"{self.name}: Evidence types = {ev_types}")

        # Track evidence IDs for graph-driven discovery in subsequent hops
        self._previous_evidence_ids = {n.id for n in evidence}

        # Log FINANCIAL_LINE coverage for commutator feedback
        financial_count = ev_types.get("FINANCIAL_LINE", 0)
        logger.info(f"{self.name}: Found {financial_count} FINANCIAL_LINE nodes in evidence")

        return BeliefState(
            evidence=evidence,
            answer="",  # Will be filled by LLM
            edge_confidences=edge_confidences,
            evidence_confidences=evidence_confidences,
            mean_path_confidence=mean_path_conf,
            operator_path="structure_first",
            hops_used=strategy.max_hops,
            seeds_used=seed_ids,
            edges_traversed=edges
        )

    def _balance_evidence(
        self,
        evidence: List[Node],
        top_k: int,
        min_financial_nodes: int = 3
    ) -> List[Node]:
        """
        Ensure evidence includes FINANCIAL_LINE nodes.

        For Operator A (structure-first), we want to ensure we include
        the financial data we started from.
        """
        financial_nodes = [n for n in evidence if n.type == "FINANCIAL_LINE"]
        other_nodes = [n for n in evidence if n.type != "FINANCIAL_LINE"]

        # Ensure minimum financial nodes
        n_financial = min(len(financial_nodes), max(min_financial_nodes, top_k // 3))
        n_other = top_k - n_financial

        balanced = financial_nodes[:n_financial] + other_nodes[:n_other]
        return balanced[:top_k]

    def _rank_evidence_with_confidence(
        self,
        traversed_nodes: List[TraversedNode],
        query_embedding: np.ndarray,
        top_k: int,
        relevance_weight: float = 0.6,
        confidence_weight: float = 0.4
    ) -> Tuple[List[Node], List[float]]:
        """
        Rank nodes by COMBINED score of:
            1. Query relevance (embedding similarity)
            2. Path confidence (product of edge confidences)

        Combined Score = relevance_weight * similarity + confidence_weight * path_confidence

        This ensures we prefer evidence that is:
            - Relevant to the query (high similarity)
            - Reached via high-confidence edges (trustworthy path)

        Args:
            traversed_nodes: List of traversed nodes with path confidence
            query_embedding: Query embedding vector
            top_k: Number of top nodes to return
            relevance_weight: Weight for embedding similarity
            confidence_weight: Weight for path confidence

        Returns:
            (top_nodes, top_confidences) - ranked nodes and their path confidences
        """
        scored = []

        for tn in traversed_nodes:
            node = tn.node
            if node.id in self.graph.embeddings:
                emb = self.graph.embeddings[node.id]

                # Query relevance (cosine similarity)
                norm_q = np.linalg.norm(query_embedding)
                norm_e = np.linalg.norm(emb)

                if norm_q > 0 and norm_e > 0:
                    similarity = np.dot(query_embedding, emb) / (norm_q * norm_e)
                else:
                    similarity = 0.0

                # Path confidence (from traversal)
                path_conf = tn.path_confidence

                # Combined score
                combined_score = (
                    relevance_weight * similarity +
                    confidence_weight * path_conf
                )

                scored.append((combined_score, similarity, path_conf, node))

        # Sort by combined score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top-k nodes and their path confidences
        top_nodes = [item[3] for item in scored[:top_k]]
        top_confidences = [item[2] for item in scored[:top_k]]

        return top_nodes, top_confidences

    def _get_edge_types(self, explore_weight: float, hop: int) -> List[str]:
        """
        Dynamic edge selection based on explore weight.

        EXPLOIT (w→0): Focus on structural + bridge edges
        EXPLORE (w→1): Add causal edges, limit semantic
        """
        # Always include bridges (key for domain crossing)
        edges = ["EXPLAINS_LINE_ITEM", "DISCUSSES"]

        # Structural edges (Operator A specialty)
        edges += ["TEMPORAL_NEXT", "REFERS_TO"]

        # Add causal edges when exploring
        if explore_weight > 0.4:
            edges += ["CAUSED_BY"]

        # Entity edges for broader exploration
        if explore_weight > 0.6:
            edges += ["MENTIONS_ENTITY"]

        # NOTE: We intentionally exclude SEMANTICALLY_SIMILAR
        # The scoring system will heavily penalize it anyway

        return edges


class OperatorB:
    """
    Narrative-First Operator (Narrative → Numbers)

    Workflow:
        1. Seed from TEXT_SECTION and NOTE nodes (qualitative data)
        2. Traverse via semantic/causal edges, WEIGHTED BY EDGE CONFIDENCE
        3. Reach financial data through DISCUSSES, CAUSED_BY

    EDGE CONFIDENCE INTEGRATION:
        - Same as OperatorA: confidence-weighted traversal and ranking

    COMMUTATOR-GUIDED REFINEMENT:
        - Accepts feedback from commutator for search refinement
        - When divergence is high, can expand narrative search

    FIX 4 & 5: Enhanced to prioritize narrative content for qualitative queries.
    """

    def __init__(
        self,
        graph: KnowledgeGraphInterface,
        embed_fn: Callable[[str], np.ndarray]
    ):
        """
        Initialize Operator B.

        Args:
            graph: Knowledge graph interface
            embed_fn: Embedding function for queries
        """
        self.graph = graph
        self.embed_fn = embed_fn
        self.name = "OperatorB"
        self._bridge_seeds: List[str] = []  # For convergence pressure
        self._last_commutator: Optional[CommutatorResult] = None  # For commutator feedback

    def _get_risk_seeds(self, query: str, query_embedding: np.ndarray) -> List[Node]:
        """
        FIX 4: Get seed nodes specifically for risk-related queries.

        This ensures we find Item 1A (Risk Factors) and other risk-related
        narrative content.

        Args:
            query: User query string
            query_embedding: Query embedding vector

        Returns:
            List of risk-related nodes
        """
        seeds = []

        # 1. Search for Item 1A / Risk Factors section specifically
        try:
            item_1a_seeds = self.graph.search_by_section_pattern(
                patterns=["Item 1A", "Risk Factors", "RISK FACTORS"],
                top_k=3
            )
            if item_1a_seeds:
                seeds.extend(item_1a_seeds)
                logger.info(f"{self.name}: FIX 4 - Found {len(item_1a_seeds)} Item 1A/Risk Factors nodes")
        except AttributeError:
            # Method may not exist, use fallback
            logger.debug(f"{self.name}: search_by_section_pattern not available, using embedding search")

        # 2. Search TEXT_SECTION nodes for risk-related content keywords
        try:
            for keyword in RISK_CONTENT_KEYWORDS[:10]:  # Use top 10 keywords
                risk_nodes = self.graph.search_by_content_keyword(
                    keyword=keyword,
                    node_types=["TEXT_SECTION", "NOTE"],
                    top_k=2
                )
                if risk_nodes:
                    seeds.extend(risk_nodes)
        except AttributeError:
            logger.debug(f"{self.name}: search_by_content_keyword not available")

        # 3. Use embedding search with risk-enhanced query as fallback
        risk_query = query + " risk factors challenges threats concerns"
        risk_embedding = self.embed_fn(risk_query)
        text_seeds = self.graph.search_by_type(
            query_embedding=risk_embedding,
            node_types=["TEXT_SECTION", "NOTE"],
            top_k=5
        )
        seeds.extend(text_seeds)

        # Deduplicate
        seen_ids = set()
        unique_seeds = []
        for node in seeds:
            if node.id not in seen_ids:
                seen_ids.add(node.id)
                unique_seeds.append(node)

        logger.info(f"{self.name}: FIX 4 - Total risk seeds: {len(unique_seeds)}")
        return unique_seeds

    def add_bridge_seeds(self, seed_ids: List[str]):
        """Add bridge seeds from convergence pressure mechanism."""
        self._bridge_seeds = seed_ids

    def set_commutator_feedback(self, commutator: CommutatorResult):
        """
        Set commutator feedback from previous hop.

        Enables commutator-guided refinement of search strategy.

        Args:
            commutator: CommutatorResult from previous hop
        """
        self._last_commutator = commutator

    def execute(
        self,
        query: str,
        strategy: TraversalStrategy,
        other_operator_evidence: Optional[set] = None
    ) -> BeliefState:
        """
        Execute narrative-first traversal with reward/penalty scoring.

        FIX 4: Enhanced to handle risk queries specially.
        FIX 5: Prioritizes narrative content (TEXT_SECTION, NOTE) for all queries.

        Args:
            query: User query string
            strategy: Traversal strategy from controller
            other_operator_evidence: Optional set of node IDs from other operator for convergence

        Returns:
            BeliefState with evidence and metadata
        """
        logger.info(f"{self.name}: Starting execution")

        # Embed query
        query_embedding = self.embed_fn(query)

        # Create scorer with appropriate weights
        scorer, context = create_scorer(
            query_embedding=query_embedding,
            embed_fn=self.embed_fn,
            explore_weight=strategy.explore_weight,
            other_operator_nodes=other_operator_evidence
        )

        # FIX 4: Check if this is a risk query
        is_risk = is_risk_query(query)
        if is_risk:
            logger.info(f"{self.name}: FIX 4 - Detected risk query, using risk-specific seeds")
            seeds = self._get_risk_seeds(query, query_embedding)
        else:
            # FIX 5: Standard narrative-first seeding (TEXT_SECTION and NOTE priority)
            seeds = self.graph.search_by_type(
                query_embedding=query_embedding,
                node_types=["TEXT_SECTION", "NOTE"],
                top_k=strategy.seeds_per_operator
            )

        seed_ids = [n.id for n in seeds]

        # Add shared seeds from other operator to ensure overlap (BUG 3 FIX)
        if other_operator_evidence:
            shared_ids = list(other_operator_evidence)[:3]  # Add up to 3 shared seeds
            seed_ids.extend(shared_ids)
            logger.debug(f"{self.name}: Added {len(shared_ids)} shared seeds for overlap")

        # Add bridge seeds if available (convergence pressure)
        if self._bridge_seeds:
            seed_ids.extend(self._bridge_seeds)
            logger.debug(f"{self.name}: Added {len(self._bridge_seeds)} bridge seeds")
            self._bridge_seeds = []  # Clear after use

        logger.debug(f"{self.name}: Total {len(seed_ids)} seed nodes")

        if not seed_ids:
            # Fallback: try any node type
            logger.warning(f"{self.name}: No TEXT_SECTION/NOTE seeds, trying fallback")
            seeds = self.graph.search_by_type(
                query_embedding=query_embedding,
                node_types=["TEXT_SECTION", "NOTE", "FINANCIAL_LINE", "ENTITY"],
                top_k=strategy.seeds_per_operator
            )
            seed_ids = [n.id for n in seeds]

        # Get dynamic edge types based on explore weight
        edge_types = self._get_edge_types(strategy.explore_weight, strategy.current_hop)

        # Compute min_edge_score based on explore weight AND hop
        # Base: EXPLOIT: 0.55, EXPLORE: 0.35
        # Hop 1 is stricter (+0.1) to prevent early explosion
        base_score = 0.55 - 0.20 * strategy.explore_weight
        hop_adjustment = 0.1 if strategy.current_hop == 1 else 0.0
        min_edge_score = base_score + hop_adjustment

        # Traverse graph WITH SCORING
        traversed_nodes, edges, edge_scores = self.graph.traverse_with_scoring(
            seed_ids=seed_ids,
            edge_types=edge_types,
            hops=strategy.max_hops,
            max_per_hop=strategy.nodes_per_hop,
            min_confidence=strategy.min_edge_confidence,
            confidence_decay=strategy.confidence_decay,
            scorer=scorer,
            context=context,
            min_edge_score=min_edge_score
        )

        logger.info(f"{self.name}: Traversed {len(traversed_nodes)} nodes, {len(edges)} edges")

        # Log score statistics
        if edge_scores:
            avg_score = np.mean([s.total_score for s in edge_scores])
            logger.debug(f"{self.name}: Avg edge score = {avg_score:.3f}")
            avg_rewards = {
                "domain_crossing": np.mean([s.domain_crossing_reward for s in edge_scores]),
                "query_relevance": np.mean([s.query_relevance_reward for s in edge_scores]),
                "convergence": np.mean([s.convergence_reward for s in edge_scores]),
            }
            avg_penalties = {
                "semantic_drift": np.mean([s.semantic_drift_penalty for s in edge_scores]),
                "domain_isolation": np.mean([s.domain_isolation_penalty for s in edge_scores]),
            }
            logger.debug(f"{self.name}: Rewards = {avg_rewards}")
            logger.debug(f"{self.name}: Penalties = {avg_penalties}")

        # Log node type distribution
        type_counts = {}
        for tn in traversed_nodes:
            t = tn.node.type
            type_counts[t] = type_counts.get(t, 0) + 1
        logger.debug(f"{self.name}: Node types = {type_counts}")

        # Collect edge confidences
        edge_confidences = [e.confidence for e in edges] if edges else [0.5]

        # Select top-k evidence by COMBINED score
        evidence, evidence_confidences = self._rank_evidence_with_confidence(
            traversed_nodes=traversed_nodes,
            query_embedding=query_embedding,
            top_k=strategy.top_k_evidence,
            relevance_weight=strategy.relevance_weight,
            confidence_weight=strategy.confidence_weight
        )

        # FIX 5: Balance evidence with priority to narrative content
        # For risk queries, strongly prioritize narrative
        evidence = self._balance_evidence(
            evidence,
            strategy.top_k_evidence,
            is_qualitative=is_risk  # Risk queries are qualitative
        )

        # Compute mean path confidence
        mean_path_conf = np.mean([tn.path_confidence for tn in traversed_nodes]) if traversed_nodes else 0.0

        # Log evidence composition
        ev_types = {}
        for n in evidence:
            ev_types[n.type] = ev_types.get(n.type, 0) + 1
        logger.debug(f"{self.name}: FIX 5 - Evidence types = {ev_types}")

        return BeliefState(
            evidence=evidence,
            answer="",
            edge_confidences=edge_confidences,
            evidence_confidences=evidence_confidences,
            mean_path_confidence=mean_path_conf,
            operator_path="narrative_first",
            hops_used=strategy.max_hops,
            seeds_used=seed_ids,
            edges_traversed=edges
        )

    def _balance_evidence(
        self,
        evidence: List[Node],
        top_k: int,
        min_financial_nodes: int = 2,
        is_qualitative: bool = False
    ) -> List[Node]:
        """
        FIX 5: Ensure evidence PRIORITIZES narrative content (TEXT_SECTION, NOTE).

        For Operator B (narrative-first), narrative content is PRIMARY,
        financial data is SECONDARY supporting evidence.

        Args:
            evidence: List of evidence nodes
            top_k: Maximum nodes to return
            min_financial_nodes: Minimum financial nodes to include
            is_qualitative: If True, minimize financial nodes further
        """
        # Separate by type
        text_nodes = [n for n in evidence if n.type == "TEXT_SECTION"]
        note_nodes = [n for n in evidence if n.type == "NOTE"]
        financial_nodes = [n for n in evidence if n.type == "FINANCIAL_LINE"]
        other_nodes = [n for n in evidence if n.type not in ["TEXT_SECTION", "NOTE", "FINANCIAL_LINE"]]

        # FIX 5: For qualitative queries, minimize financial nodes
        if is_qualitative:
            min_financial_nodes = 1
            max_financial_nodes = 2
        else:
            max_financial_nodes = max(min_financial_nodes, top_k // 5)

        # Priority order: TEXT_SECTION > NOTE > FINANCIAL_LINE > other
        balanced = []

        # 1. Add TEXT_SECTION nodes first (highest priority for Operator B)
        n_text = min(len(text_nodes), top_k // 2)  # Up to half can be text
        balanced.extend(text_nodes[:n_text])

        # 2. Add NOTE nodes
        remaining = top_k - len(balanced)
        n_notes = min(len(note_nodes), remaining // 2)
        balanced.extend(note_nodes[:n_notes])

        # 3. Add FINANCIAL_LINE nodes (limited for narrative operator)
        remaining = top_k - len(balanced)
        n_financial = min(len(financial_nodes), max_financial_nodes, remaining)
        balanced.extend(financial_nodes[:n_financial])

        # 4. Fill remaining with other nodes
        remaining = top_k - len(balanced)
        balanced.extend(other_nodes[:remaining])

        logger.debug(f"{self.name}: FIX 5 - Balanced evidence: {len(text_nodes[:n_text])} TEXT_SECTION, "
                    f"{n_notes} NOTE, {n_financial} FINANCIAL_LINE")

        return balanced[:top_k]

    def _rank_evidence_with_confidence(
        self,
        traversed_nodes: List[TraversedNode],
        query_embedding: np.ndarray,
        top_k: int,
        relevance_weight: float = 0.6,
        confidence_weight: float = 0.4
    ) -> Tuple[List[Node], List[float]]:
        """
        Rank nodes by COMBINED score (same implementation as OperatorA).

        Args:
            traversed_nodes: List of traversed nodes with path confidence
            query_embedding: Query embedding vector
            top_k: Number of top nodes to return
            relevance_weight: Weight for embedding similarity
            confidence_weight: Weight for path confidence

        Returns:
            (top_nodes, top_confidences) - ranked nodes and their path confidences
        """
        scored = []

        for tn in traversed_nodes:
            node = tn.node
            if node.id in self.graph.embeddings:
                emb = self.graph.embeddings[node.id]

                # Query relevance (cosine similarity)
                norm_q = np.linalg.norm(query_embedding)
                norm_e = np.linalg.norm(emb)

                if norm_q > 0 and norm_e > 0:
                    similarity = np.dot(query_embedding, emb) / (norm_q * norm_e)
                else:
                    similarity = 0.0

                path_conf = tn.path_confidence
                combined_score = relevance_weight * similarity + confidence_weight * path_conf
                scored.append((combined_score, similarity, path_conf, node))

        scored.sort(key=lambda x: x[0], reverse=True)

        top_nodes = [item[3] for item in scored[:top_k]]
        top_confidences = [item[2] for item in scored[:top_k]]

        return top_nodes, top_confidences

    def _get_edge_types(self, explore_weight: float, hop: int) -> List[str]:
        """
        Dynamic edge selection for Operator B.

        Key difference: Can use SEMANTICALLY_SIMILAR but only on hop 1
        and the scoring system will penalize chains.
        """
        # Always include bridges
        edges = ["EXPLAINS_LINE_ITEM", "DISCUSSES"]

        # Narrative operator specialty
        edges += ["CAUSED_BY", "MENTIONS_ENTITY"]

        # Add structural edges when exploiting (convergence with Op A)
        if explore_weight < 0.5:
            edges += ["TEMPORAL_NEXT"]

        # SEMANTICALLY_SIMILAR: only on hop 1, only when exploring
        # The scoring system will penalize chains anyway
        if explore_weight > 0.6 and hop == 1:
            edges.append("SEMANTICALLY_SIMILAR")

        return edges
