"""
Enhanced Prompts for OpMech-GraphRAG.

These prompts enforce temporal accuracy and help prevent LLM errors
like confusing increase vs decrease in financial comparisons.
"""

# =============================================================================
# TEMPORAL VERIFICATION INSTRUCTIONS (shared across prompts)
# =============================================================================

TEMPORAL_VERIFICATION_INSTRUCTIONS = """
RULES: Compute direction (later - earlier). Positive = INCREASE. Negative = DECREASE.
Use EXACT fiscal years from evidence (FY2022, FY2023). NEVER use FY1, FY2, "earlier period".
"""

# =============================================================================
# BUG 1 & 6 FIX: STRICT PERIOD LABEL INSTRUCTIONS
# =============================================================================

STRICT_PERIOD_LABEL_INSTRUCTIONS = """
FORBIDDEN: FY1, FY2, FY3, "earlier period", "later period", "prior year"
REQUIRED: Use FY2022, FY2023, FY2024, Q1-2023 exactly as shown in evidence.
"""

# =============================================================================
# BUG 4 & 6 FIX: MANDATORY FACTS TEMPLATE
# =============================================================================

MANDATORY_FACTS_INSTRUCTIONS = """
{mandatory_facts}

CRITICAL - USE MANDATORY FACTS ABOVE:
1. The directions (INCREASE/DECREASE) above are PRE-COMPUTED and VERIFIED
2. DO NOT compute your own directions - use the ones provided
3. If MANDATORY FACTS says INCREASE, you MUST say INCREASE
4. If MANDATORY FACTS says DECREASE, you MUST say DECREASE
5. If a value is provided above, use it EXACTLY - do not round or estimate
"""

# =============================================================================
# OPERATOR ANSWER PROMPTS
# =============================================================================

OPERATOR_ANSWER_PROMPT = f"""You are a financial analyst assistant analyzing SEC filings.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

{STRICT_PERIOD_LABEL_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

BEFORE answering:
1. Identify the ACTUAL fiscal years in the evidence (look for [FY2022], [FY2023], [FY2024])
2. Use ONLY those explicit years - NEVER generic labels like "FY1" or "FY2"
3. Verify any temporal claims by computing the actual change direction

Answer:"""


OPERATOR_ANSWER_PROMPT_STRUCTURED = f"""You are a financial analyst assistant.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

{STRICT_PERIOD_LABEL_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

Structure your response as follows:
1. First, identify the key values and their EXPLICIT fiscal years (FY2022, FY2023, FY2024 - NOT FY1, FY2)
2. Compute the direction of change (show your work)
3. State your answer using the computed direction and EXPLICIT years

Answer:"""


OPERATOR_ANSWER_PROMPT_NUMERICAL = f"""You are a financial analyst assistant. Answer this NUMERICAL query with precision.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

{STRICT_PERIOD_LABEL_INSTRUCTIONS}

Evidence:
{{evidence}}

Temporal Summary:
{{temporal_summary}}

Question: {{query}}

Requirements:
1. Provide a specific number as the answer
2. Cite the source (XBRL tag, fiscal period) using EXPLICIT years (FY2022, FY2023, FY2024)
3. If multiple values exist, clarify which period/context - ALWAYS use explicit fiscal years
4. Use the pre-computed change if a comparison is requested
5. NEVER use generic labels like "FY1", "FY2", "earlier period"

Answer:"""


OPERATOR_ANSWER_PROMPT_CAUSAL = f"""You are analyzing the causes/factors behind a financial change.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

{STRICT_PERIOD_LABEL_INSTRUCTIONS}

Evidence:
{{evidence}}

Temporal Summary:
{{temporal_summary}}

Question: {{query}}

Requirements:
1. First, establish the FACTUAL change (direction and magnitude) using EXPLICIT fiscal years (FY2022, FY2023, FY2024)
2. Then, analyze the contributing factors
3. Distinguish between:
   - Verified factors (mentioned in filings)
   - Possible factors (inferred from context)
4. Do not speculate beyond the evidence
5. NEVER use generic labels like "FY1", "FY2", "earlier period"

Answer:"""


OPERATOR_ANSWER_PROMPT_OPINION = f"""You are providing a balanced analysis of a debatable financial question.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

{STRICT_PERIOD_LABEL_INSTRUCTIONS}

Evidence:
{{evidence}}

Question: {{query}}

Requirements:
1. Present multiple perspectives (quantitative and qualitative)
2. Ground opinions in factual evidence using EXPLICIT fiscal years (FY2022, FY2023, FY2024)
3. Acknowledge limitations and uncertainties
4. Do not claim certainty on inherently uncertain questions
5. NEVER use generic labels like "FY1", "FY2", "earlier period" - ALWAYS use actual years

Answer:"""


OPERATOR_ANSWER_PROMPT_TEMPORAL = f"""You are answering a temporal comparison question.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

{STRICT_PERIOD_LABEL_INSTRUCTIONS}

THIS IS A TEMPORAL QUERY - DIRECTION ACCURACY IS CRITICAL.
YOU MUST USE EXPLICIT FISCAL YEARS (FY2022, FY2023, FY2024) - NEVER "FY1", "FY2", "FY3".

Evidence:
{{evidence}}

Temporal Summary:
{{temporal_summary}}

Question: {{query}}

STEP-BY-STEP VERIFICATION (required):
1. Earlier period: {{fiscal_year_earlier}} with value $____ (use ACTUAL year from evidence, e.g., FY2023)
2. Later period: {{fiscal_year_later}} with value $____ (use ACTUAL year from evidence, e.g., FY2024)
3. Change calculation: $____ - $____ = $____
4. Direction: [INCREASE/DECREASE]
5. Percentage: ____%

Answer (using verified direction and EXPLICIT fiscal years):"""


# =============================================================================
# MERGE/SYNTHESIS PROMPTS
# =============================================================================

EXPLORE_MODE_MERGE_PROMPT = f"""You are synthesizing two analytical perspectives on a financial question.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

CRITICAL: Both perspectives should agree on basic FACTUAL claims (numbers, directions).
If they disagree on direction (one says increase, other says decrease), this is a factual error.

Perspective A (Quantitative/Financial):
{{answer_A}}

Perspective B (Qualitative/Narrative):
{{answer_B}}

{{discrepancy_note}}

FACT CHECK before synthesizing:
1. Do both perspectives agree on the direction of change?
   - If NO, use the pre-computed changes from evidence as the authoritative source
2. Do the specific figures match?
3. Note any discrepancies explicitly

Question: {{query}}

Synthesized Answer:"""


ADAPTIVE_MODE_MERGE_PROMPT = f"""You are merging two analytical perspectives with weighted reliability.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Perspective A (reliability: {{reliability_A:.0%}}):
{{answer_A}}

Perspective B (reliability: {{reliability_B:.0%}}):
{{answer_B}}

INSTRUCTIONS:
1. Weight the perspectives by their reliability scores
2. For factual claims (numbers, directions), prefer the higher-reliability source
3. For interpretations, consider both perspectives
4. Flag any contradictions

Question: {{query}}

Merged Answer:"""


ADAPTIVE_MODE_PROMPT = f"""You are providing a balanced financial analysis.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Evidence from multiple sources:
{{evidence}}

Primary finding:
{{primary_answer}}

Additional context:
{{secondary_answer}}

Question: {{query}}

Provide a balanced answer that:
1. States the factual finding with verified direction
2. Adds relevant context
3. Notes any limitations or uncertainties

Answer:"""


EXPLOIT_MODE_ANSWER_PROMPT = f"""You are providing a confident answer based on strong operator agreement.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Primary Answer (from trusted operator):
{{trusted_answer}}

Supporting Evidence Summary:
{{evidence_summary}}

Question: {{query}}

INSTRUCTIONS:
1. Verify temporal direction of any change claims
2. Cite specific figures and periods
3. Provide a concise, confident answer

Final Answer:"""


# =============================================================================
# VALIDATION PROMPTS
# =============================================================================

TEMPORAL_VALIDATION_PROMPT = f"""Verify the temporal accuracy of this financial answer.

{TEMPORAL_VERIFICATION_INSTRUCTIONS}

Answer to validate:
{{answer}}

Evidence context:
{{evidence}}

CHECK:
1. Are any "increase" or "decrease" claims correct given the evidence?
2. Are the period labels (FY2022, FY2023) correctly associated with values?
3. Are computed percentage changes accurate?

If errors found, provide corrections. If accurate, confirm.

Validation result:"""


CONSISTENCY_CHECK_PROMPT = """Check if these two answers are factually consistent.

Answer A:
{answer_A}

Answer B:
{answer_B}

CHECK for discrepancies:
1. Direction of change (one says increase, other says decrease?)
2. Specific figures (do the numbers match?)
3. Period references (are fiscal years consistent?)

List any discrepancies found, or confirm consistency:"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_operator_prompt(
    query_type: str,
    evidence: str,
    query: str,
    temporal_summary: str = "",
    fiscal_year_earlier: str = "",
    fiscal_year_later: str = "",
    mandatory_facts: str = "",
) -> str:
    """
    Get the appropriate operator prompt based on query type.

    BUG 6 FIX: Now includes mandatory facts and strict period label instructions.

    Args:
        query_type: Type of query (numerical, causal, opinion, temporal, etc.)
        evidence: Formatted evidence string
        query: User query
        temporal_summary: Optional temporal summary
        fiscal_year_earlier: Earlier fiscal year for temporal queries
        fiscal_year_later: Later fiscal year for temporal queries
        mandatory_facts: Pre-computed facts that LLM must use (directions, values)

    Returns:
        Formatted prompt string
    """
    query_type_lower = query_type.lower()

    # BUG 6 FIX: Build mandatory facts section if provided
    facts_section = ""
    if mandatory_facts:
        facts_section = MANDATORY_FACTS_INSTRUCTIONS.format(mandatory_facts=mandatory_facts)

    # BUG 1 FIX: Always include strict period label instructions
    period_instructions = STRICT_PERIOD_LABEL_INSTRUCTIONS

    if query_type_lower == "numerical":
        base_prompt = OPERATOR_ANSWER_PROMPT_NUMERICAL.format(
            evidence=evidence,
            temporal_summary=temporal_summary or "No temporal summary available",
            query=query
        )
    elif query_type_lower == "causal":
        base_prompt = OPERATOR_ANSWER_PROMPT_CAUSAL.format(
            evidence=evidence,
            temporal_summary=temporal_summary or "No temporal summary available",
            query=query
        )
    elif query_type_lower == "opinion":
        base_prompt = OPERATOR_ANSWER_PROMPT_OPINION.format(
            evidence=evidence,
            query=query
        )
    elif query_type_lower == "temporal":
        base_prompt = OPERATOR_ANSWER_PROMPT_TEMPORAL.format(
            evidence=evidence,
            temporal_summary=temporal_summary or "No temporal summary available",
            query=query,
            fiscal_year_earlier=fiscal_year_earlier or "FY____",
            fiscal_year_later=fiscal_year_later or "FY____",
        )
    elif query_type_lower == "structured":
        base_prompt = OPERATOR_ANSWER_PROMPT_STRUCTURED.format(
            evidence=evidence,
            query=query
        )
    else:
        base_prompt = OPERATOR_ANSWER_PROMPT.format(
            evidence=evidence,
            query=query
        )

    # BUG 6 FIX: Insert mandatory facts and period instructions into prompt
    if facts_section:
        # Insert before evidence section
        parts = base_prompt.split("Evidence:")
        if len(parts) == 2:
            return parts[0] + facts_section + "\n" + period_instructions + "\n\nEvidence:" + parts[1]

    # At minimum, add period instructions
    parts = base_prompt.split("Evidence:")
    if len(parts) == 2:
        return parts[0] + period_instructions + "\n\nEvidence:" + parts[1]

    return base_prompt


def get_merge_prompt(
    mode: str,
    answer_A: str,
    answer_B: str,
    query: str,
    reliability_A: float = 0.5,
    reliability_B: float = 0.5,
    evidence_summary: str = "",
    discrepancy_note: str = "",
) -> str:
    """
    Get the appropriate merge prompt based on mode.

    Args:
        mode: Query mode (exploit, adaptive, explore)
        answer_A: Operator A's answer
        answer_B: Operator B's answer
        query: User query
        reliability_A: Operator A's reliability score
        reliability_B: Operator B's reliability score
        evidence_summary: Summary of evidence
        discrepancy_note: Note about any discrepancies found

    Returns:
        Formatted merge prompt string
    """
    mode_lower = mode.lower()

    if mode_lower == "explore":
        return EXPLORE_MODE_MERGE_PROMPT.format(
            answer_A=answer_A,
            answer_B=answer_B,
            query=query,
            discrepancy_note=discrepancy_note or "",
        )
    elif mode_lower == "adaptive":
        return ADAPTIVE_MODE_MERGE_PROMPT.format(
            answer_A=answer_A,
            answer_B=answer_B,
            reliability_A=reliability_A,
            reliability_B=reliability_B,
            query=query
        )
    elif mode_lower == "exploit":
        # For exploit, we typically trust one answer
        trusted_answer = answer_A if reliability_A >= reliability_B else answer_B
        return EXPLOIT_MODE_ANSWER_PROMPT.format(
            trusted_answer=trusted_answer,
            evidence_summary=evidence_summary or "See above evidence",
            query=query
        )
    else:
        # Default to explore mode prompt
        return EXPLORE_MODE_MERGE_PROMPT.format(
            answer_A=answer_A,
            answer_B=answer_B,
            query=query,
            discrepancy_note=discrepancy_note or "",
        )


def get_validation_prompt(answer: str, evidence: str) -> str:
    """
    Get the validation prompt.

    Args:
        answer: Answer to validate
        evidence: Evidence context

    Returns:
        Formatted validation prompt
    """
    return TEMPORAL_VALIDATION_PROMPT.format(
        answer=answer,
        evidence=evidence
    )
