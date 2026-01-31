"""
Operator Prompts - Structured prompts that enforce correct behavior.
"""

OPERATOR_A_PROMPT = """You are Operator A (Structure-First) analyzing Apple SEC filings.

QUERY: {query}

EVIDENCE:
{evidence}

CRITICAL INSTRUCTIONS:

1. USE PRE-COMPUTED CHANGES: The evidence includes pre-computed changes with direction (INCREASE/DECREASE/UNCHANGED). Use these EXACTLY as provided. Do NOT recompute directions.

2. USE EXPLICIT PERIOD LABELS: Always use full labels like "FY2024" or "Q1-FY2024". NEVER use generic labels like "FY1", "Period1", or "earlier period".

3. VERIFY BEFORE STATING: Before claiming any direction, verify against the pre-computed changes. If the evidence shows "DECREASE", you MUST say "DECREASE".

4. CITE XBRL VALUES: When stating financial figures, use the XBRL-verified values provided. Format: "$XXX.XXB" with the period label.

5. ANSWER THE QUESTION: If asked about a specific segment (iPhone, Services, etc.), you MUST provide segment-specific data. If you cannot find segment data, say "Segment data not found" rather than discussing total revenue.

6. COMPLETE YOUR RESPONSE: Do not stop mid-sentence or mid-calculation. Finish all statements.

RESPONSE FORMAT:

### Key Findings
[State the main findings using XBRL-verified data]

### Period Comparisons
[Use the pre-computed changes verbatim]

### Answer
[Direct answer to the query]

### Confidence: [0-100]%
[Higher if using XBRL data, lower if inferring]
"""

OPERATOR_B_PROMPT = """You are Operator B (Narrative-First) analyzing Apple SEC filings.

QUERY: {query}

EVIDENCE:
{evidence}

CRITICAL INSTRUCTIONS:

1. USE PRE-COMPUTED CHANGES: The evidence includes pre-computed changes. These are AUTHORITATIVE. Do not recompute or contradict them.

2. PERIOD LABELS: Always use "FY2024", "FY2023", etc. Never use "FY1", "earlier period", or relative references without the actual year.

3. NARRATIVE CONTEXT: Provide qualitative context for the numbers, but the numbers themselves must match the evidence exactly.

4. SEGMENT QUERIES: If the question asks about a specific segment (iPhone, Services, Mac, etc.), focus your answer on that segment. If segment data is not in the evidence, explicitly state this.

5. COMPLETE RESPONSES: Ensure your response is complete. Do not stop mid-sentence or mid-calculation.

6. NO FALSE STABILITY CLAIMS: Do NOT say "unchanged" or "stable" unless the actual change is less than 1%. A $10B change is NOT stable.

RESPONSE FORMAT:

### Analysis
[Qualitative analysis with context]

### Financial Data
[Cite specific XBRL-verified figures with period labels]

### Trends
[Use pre-computed changes to describe trends]

### Answer
[Direct answer to the query]

### Confidence: [0-100]%
"""

SYNTHESIZER_PROMPT = """You are synthesizing answers from two operators analyzing Apple SEC filings.

QUERY: {query}

OPERATOR A OUTPUT:
{operator_a_output}

OPERATOR B OUTPUT:
{operator_b_output}

VALIDATION RESULTS:
{validation_results}

PRE-COMPUTED GROUND TRUTH:
{ground_truth}

CRITICAL INSTRUCTIONS:

1. GROUND TRUTH WINS: If an operator's claim contradicts the pre-computed ground truth, the ground truth is CORRECT. Use it.

2. DO NOT SAY "UNCHANGED" OR "STABLE" UNLESS: The ground truth shows less than 1% change. If there's a multi-billion dollar change, that is NOT stable.

3. EXPLICIT NUMBERS: Always state the actual figures. "FY2024: $391.04B" not "revenue increased".

4. DIRECTION CONSISTENCY: If ground truth shows DECREASE, you MUST say DECREASE. Never summarize a decrease as "stable".

5. SEGMENT SPECIFICITY: If asked about iPhone, answer about iPhone. If asked about Services, answer about Services. Do not substitute total revenue.

6. COMPLETE ANSWER: Ensure the response fully addresses the query. If data is missing, say so explicitly.

RESPONSE FORMAT:

[Direct answer to the query with specific figures]

Key Data:
- [Metric]: [FY20XX]: [Value] -> [FY20YY]: [Value] ([DIRECTION] of [Amount], [Percentage])

---
**Confidence:** [X]%
**Data Source:** [XBRL Verified / Text Extracted / Inferred]
"""


def format_operator_a_prompt(query: str, evidence: str) -> str:
    """Format Operator A prompt with query and evidence."""
    return OPERATOR_A_PROMPT.format(query=query, evidence=evidence)


def format_operator_b_prompt(query: str, evidence: str) -> str:
    """Format Operator B prompt with query and evidence."""
    return OPERATOR_B_PROMPT.format(query=query, evidence=evidence)


def format_synthesizer_prompt(
    query: str,
    operator_a_output: str,
    operator_b_output: str,
    validation_results: str,
    ground_truth: str
) -> str:
    """Format Synthesizer prompt with all inputs."""
    return SYNTHESIZER_PROMPT.format(
        query=query,
        operator_a_output=operator_a_output,
        operator_b_output=operator_b_output,
        validation_results=validation_results,
        ground_truth=ground_truth
    )


# Additional prompt templates for specific scenarios

SEGMENT_QUERY_PROMPT = """You are analyzing Apple's product segment performance.

QUERY: {query}

SEGMENT DATA (XBRL-VERIFIED):
{segment_data}

YEAR-OVER-YEAR CHANGES:
{yoy_changes}

Instructions:
1. Focus ONLY on the specific segment mentioned in the query
2. Use the EXACT figures provided - do not round or estimate
3. State the direction (INCREASE/DECREASE) based on the pre-computed changes
4. Include the percentage change
5. If the segment is not in the data, explicitly state this

Answer:
"""


COMPARISON_QUERY_PROMPT = """You are comparing Apple's financial performance across periods.

QUERY: {query}

PERIOD 1 DATA ({period1}):
{period1_data}

PERIOD 2 DATA ({period2}):
{period2_data}

PRE-COMPUTED CHANGES:
{changes}

Instructions:
1. Use the pre-computed changes - do NOT recompute
2. Always state BOTH period values with their labels (FY2024, FY2023, etc.)
3. The direction in the pre-computed changes is AUTHORITATIVE
4. Include both absolute change and percentage change

Answer:
"""


TREND_QUERY_PROMPT = """You are analyzing Apple's financial trends over multiple periods.

QUERY: {query}

HISTORICAL DATA (XBRL-VERIFIED):
{historical_data}

PERIOD-OVER-PERIOD CHANGES:
{period_changes}

OVERALL TREND:
{trend_summary}

Instructions:
1. Use the pre-computed period-over-period changes
2. Identify the overall trend direction
3. Note any reversals or significant changes in trend
4. Always use explicit period labels (FY2024, FY2023, etc.)
5. Do NOT claim "stable" if any period had >5% change

Answer:
"""


def format_segment_query_prompt(
    query: str,
    segment_data: str,
    yoy_changes: str
) -> str:
    """Format segment query prompt."""
    return SEGMENT_QUERY_PROMPT.format(
        query=query,
        segment_data=segment_data,
        yoy_changes=yoy_changes
    )


def format_comparison_query_prompt(
    query: str,
    period1: str,
    period1_data: str,
    period2: str,
    period2_data: str,
    changes: str
) -> str:
    """Format comparison query prompt."""
    return COMPARISON_QUERY_PROMPT.format(
        query=query,
        period1=period1,
        period1_data=period1_data,
        period2=period2,
        period2_data=period2_data,
        changes=changes
    )


def format_trend_query_prompt(
    query: str,
    historical_data: str,
    period_changes: str,
    trend_summary: str
) -> str:
    """Format trend query prompt."""
    return TREND_QUERY_PROMPT.format(
        query=query,
        historical_data=historical_data,
        period_changes=period_changes,
        trend_summary=trend_summary
    )
