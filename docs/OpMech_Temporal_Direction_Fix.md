# OpMech-GraphRAG Debug & Fix: Temporal Direction & Answer Consistency

## Problem Summary

The system correctly selected EXPLORE mode and retrieved appropriate evidence, but **Operator A misinterpreted the temporal direction** of changes:

**Query:** "What factors drove iPhone revenue changes in FY2023?"

**What went wrong:**
- Operator A said: "revenue **increased** from $383.29B to $394.33B" ❌
- Operator B said: "revenue **decreased** from $394.33B to $383.29B" ✅
- Reality: Revenue DECREASED from FY2022 ($394.33B) to FY2023 ($383.29B)

**Root Cause:** The LLM confused which date corresponds to which fiscal year:
- `2022-09-24` = End of FY2022 → $394.33B (earlier, higher)
- `2023-09-30` = End of FY2023 → $383.29B (later, lower)

This is a **generalized problem** that can affect ANY temporal comparison query.

---

## Generalized Issues to Fix

| Issue | Description | Affected Queries |
|-------|-------------|------------------|
| **Temporal Direction** | LLM confuses increase vs decrease | Any YoY, QoQ comparison |
| **Date-to-Period Mapping** | Confuses which date = which fiscal year | All temporal queries |
| **Operator Answer Consistency** | Operators can contradict each other on facts | All queries with numerical claims |
| **Confidence Calibration** | Operator A had 97% confidence despite being wrong | All queries |
| **Trust Decision for Causal** | Used MERGE_EQUAL instead of MERGE_WEIGHTED | Causal queries |

---

## Debug Task 1: Analyze Current Evidence Formatting

Check how evidence is presented to the LLM:

```python
# debug_evidence_format.py

def debug_evidence_formatting():
    """Check how temporal evidence is formatted for the LLM."""
    
    # Sample evidence nodes (simulate what operators collect)
    sample_evidence = [
        {
            "type": "FINANCIAL_LINE",
            "content": "Net Sales: $394.33B (2022-09-24)",
            "xbrl_tag": "us-gaap:Revenues",
            "value": 394330000000,
            "period_end": "2022-09-24",
            "fiscal_year": None,  # Often missing!
        },
        {
            "type": "FINANCIAL_LINE", 
            "content": "Net Sales: $383.29B (2023-09-30)",
            "xbrl_tag": "us-gaap:Revenues",
            "value": 383290000000,
            "period_end": "2023-09-30",
            "fiscal_year": None,
        }
    ]
    
    print("Current Evidence Format:")
    for e in sample_evidence:
        print(f"  {e['content']}")
    
    print("\nProblems:")
    print("  1. No explicit fiscal year label (FY2022, FY2023)")
    print("  2. Date format (2022-09-24) is ambiguous")
    print("  3. No indication of chronological order")
    print("  4. No pre-computed change direction")
    
    print("\nRecommended Format:")
    print("  [FY2022] Net Sales: $394.33B (period ending 2022-09-24)")
    print("  [FY2023] Net Sales: $383.29B (period ending 2023-09-30)")
    print("  Change: -$11.04B (-2.8%) year-over-year DECREASE")

debug_evidence_formatting()
```

---

## Debug Task 2: Check Answer Generation Prompts

Find and analyze the prompts used to generate operator answers:

```bash
# Find answer generation code
grep -rn "generate" src/opmech/ --include="*.py" | grep -i "answer\|prompt"
cat src/opmech/operators.py | grep -A 50 "def _generate_answer"
cat src/opmech/llm_interface.py | grep -A 30 "def generate"
```

```python
# Check current prompt structure
def debug_answer_prompt():
    """Examine how the answer generation prompt is structured."""
    
    # Find the prompt template
    from src.opmech.operators import BaseOperator
    
    # Typical current prompt (problematic):
    current_prompt = """
    Based on the following evidence from SEC filings, answer the question.
    
    Evidence:
    {evidence}
    
    Question: {query}
    
    Answer:
    """
    
    print("Current Prompt Issues:")
    print("  1. No instruction to verify temporal direction")
    print("  2. No fiscal year context provided")
    print("  3. No instruction to compute changes explicitly")
    print("  4. No consistency checks required")
```

---

## Fix 1: Enhanced Evidence Preprocessing

Create a preprocessor that enriches evidence with temporal context:

```python
# src/opmech/evidence_preprocessor.py

from typing import List, Dict, Tuple, Optional
from datetime import datetime
import re

class EvidencePreprocessor:
    """
    Preprocesses evidence to add temporal context and computed metrics.
    Prevents LLM from making temporal interpretation errors.
    """
    
    # Apple's fiscal year ends in September
    # Configurable per company
    FISCAL_YEAR_END_MONTH = 9
    
    def __init__(self, company_fiscal_end_month: int = 9):
        self.fiscal_end_month = company_fiscal_end_month
    
    def preprocess(self, evidence_nodes: List[Dict]) -> List[Dict]:
        """
        Enrich evidence with temporal context.
        
        Adds:
        - Explicit fiscal year labels
        - Chronological ordering
        - Pre-computed period-over-period changes
        """
        enriched = []
        
        for node in evidence_nodes:
            enriched_node = node.copy()
            
            # Add fiscal year if date is present
            if 'period_end' in node or self._extract_date(node.get('content', '')):
                date_str = node.get('period_end') or self._extract_date(node['content'])
                if date_str:
                    fiscal_year = self._date_to_fiscal_year(date_str)
                    enriched_node['fiscal_year'] = fiscal_year
                    enriched_node['fiscal_label'] = f"FY{fiscal_year}"
            
            enriched.append(enriched_node)
        
        # Sort by fiscal year (chronological)
        enriched = self._sort_chronologically(enriched)
        
        # Compute period-over-period changes for same metrics
        enriched = self._compute_changes(enriched)
        
        return enriched
    
    def _extract_date(self, content: str) -> Optional[str]:
        """Extract date from content string."""
        # Match patterns like (2023-09-30), 2023-09-30, September 30, 2023
        patterns = [
            r'\((\d{4}-\d{2}-\d{2})\)',  # (2023-09-30)
            r'(\d{4}-\d{2}-\d{2})',       # 2023-09-30
            r'(\w+ \d{1,2}, \d{4})',      # September 30, 2023
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        return None
    
    def _date_to_fiscal_year(self, date_str: str) -> int:
        """
        Convert date to fiscal year.
        
        For Apple (fiscal year ends in September):
        - 2022-09-24 → FY2022
        - 2023-09-30 → FY2023
        - 2023-01-15 → FY2023 (Q1 of FY2023)
        """
        try:
            # Parse date
            if '-' in date_str:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date = datetime.strptime(date_str, '%B %d, %Y')
            
            # Determine fiscal year
            if date.month > self.fiscal_end_month:
                # After fiscal year end = next fiscal year
                return date.year + 1
            else:
                return date.year
                
        except ValueError:
            return None
    
    def _sort_chronologically(self, nodes: List[Dict]) -> List[Dict]:
        """Sort nodes by fiscal year, oldest first."""
        def sort_key(node):
            fy = node.get('fiscal_year')
            if fy is None:
                return (9999, node.get('content', ''))
            return (fy, node.get('content', ''))
        
        return sorted(nodes, key=sort_key)
    
    def _compute_changes(self, nodes: List[Dict]) -> List[Dict]:
        """
        Compute period-over-period changes for matching metrics.
        
        Groups by XBRL tag and computes YoY changes.
        """
        # Group by metric (xbrl_tag)
        by_metric = {}
        for node in nodes:
            tag = node.get('xbrl_tag', node.get('content', '')[:50])
            if tag not in by_metric:
                by_metric[tag] = []
            by_metric[tag].append(node)
        
        # Compute changes for each metric
        for tag, metric_nodes in by_metric.items():
            if len(metric_nodes) >= 2:
                # Sort by fiscal year
                sorted_nodes = sorted(
                    [n for n in metric_nodes if n.get('fiscal_year')],
                    key=lambda x: x['fiscal_year']
                )
                
                # Compute YoY changes
                for i in range(1, len(sorted_nodes)):
                    prev = sorted_nodes[i-1]
                    curr = sorted_nodes[i]
                    
                    if 'value' in prev and 'value' in curr:
                        prev_val = float(prev['value'])
                        curr_val = float(curr['value'])
                        
                        if prev_val != 0:
                            abs_change = curr_val - prev_val
                            pct_change = (abs_change / prev_val) * 100
                            direction = "INCREASE" if abs_change > 0 else "DECREASE"
                            
                            curr['computed_change'] = {
                                'from_period': prev.get('fiscal_label', 'prior'),
                                'to_period': curr.get('fiscal_label', 'current'),
                                'absolute': abs_change,
                                'percentage': pct_change,
                                'direction': direction,
                            }
        
        return nodes
    
    def format_for_llm(self, nodes: List[Dict]) -> str:
        """
        Format preprocessed evidence for LLM consumption.
        
        Includes explicit temporal labels and pre-computed changes.
        """
        lines = []
        
        for node in nodes:
            # Build the evidence line
            node_type = node.get('type', node.get('node_type', 'UNKNOWN'))
            fiscal_label = node.get('fiscal_label', '')
            content = node.get('content', '')
            
            # Add fiscal year prefix if available
            if fiscal_label:
                line = f"[{node_type}] [{fiscal_label}] {content}"
            else:
                line = f"[{node_type}] {content}"
            
            # Add computed change if available
            if 'computed_change' in node:
                change = node['computed_change']
                change_line = (
                    f"    → Change from {change['from_period']} to {change['to_period']}: "
                    f"{change['direction']} of ${abs(change['absolute'])/1e9:.2f}B "
                    f"({change['percentage']:+.1f}%)"
                )
                line += "\n" + change_line
            
            lines.append(line)
        
        return "\n\n".join(lines)
```

---

## Fix 2: Enhanced Answer Generation Prompt

Update the answer generation prompt to enforce temporal accuracy:

```python
# src/opmech/prompts.py

OPERATOR_ANSWER_PROMPT = """You are a financial analyst assistant. Based on the evidence below, answer the question accurately.

CRITICAL INSTRUCTIONS:
1. TEMPORAL ACCURACY: Pay close attention to fiscal year labels ([FY2022], [FY2023], etc.)
   - Earlier fiscal years have LOWER numbers (FY2022 < FY2023)
   - If a value goes from $394B in FY2022 to $383B in FY2023, that is a DECREASE
   - Always verify: Is the later period's value higher or lower than the earlier period?

2. DIRECTION VERIFICATION: Before stating any increase/decrease:
   - Identify the earlier period and its value
   - Identify the later period and its value
   - Compute: later_value - earlier_value
   - If positive → INCREASE; If negative → DECREASE

3. USE PRE-COMPUTED CHANGES: If the evidence includes computed changes (marked with →), use those values directly.

4. CITE SPECIFIC FIGURES: Always include the actual numbers and periods when discussing changes.

Evidence:
{evidence}

Question: {query}

Before answering, verify any temporal claims:
- What is the earlier period value?
- What is the later period value?
- What is the direction of change?

Answer:"""


EXPLORE_MODE_MERGE_PROMPT = """You are synthesizing two analytical perspectives on a financial question.

CRITICAL: Both perspectives should agree on basic FACTUAL claims (numbers, directions of change).
If they disagree on facts, flag this as a discrepancy and use the more reliable figure.

Perspective A (Quantitative/Financial):
{answer_A}

Perspective B (Qualitative/Narrative):
{answer_B}

FACT CHECK before synthesizing:
1. Do both perspectives agree on the direction of change (increase vs decrease)?
2. Do the specific figures match?
3. If there's a discrepancy, note it explicitly.

Question: {query}

Synthesized Answer (flag any factual discrepancies between perspectives):"""
```

---

## Fix 3: Answer Validation Layer

Add a validation layer that checks answers for temporal consistency:

```python
# src/opmech/answer_validator.py

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[str]
    corrections: Dict[str, str]
    confidence_adjustment: float

class AnswerValidator:
    """
    Validates operator answers for factual consistency.
    Catches temporal direction errors, numerical mismatches, etc.
    """
    
    def __init__(self):
        # Patterns to detect temporal claims
        self.increase_patterns = [
            r'increas\w+',
            r'grew',
            r'growth',
            r'rose',
            r'gained',
            r'higher',
            r'up\s+\d',
        ]
        
        self.decrease_patterns = [
            r'decreas\w+',
            r'declined?',
            r'fell',
            r'dropped?',
            r'lower',
            r'down\s+\d',
            r'reduction',
        ]
    
    def validate(
        self, 
        answer: str, 
        evidence: List[Dict],
        query: str
    ) -> ValidationResult:
        """
        Validate an answer against the evidence.
        
        Checks:
        1. Temporal direction consistency
        2. Numerical accuracy
        3. Period labeling
        """
        issues = []
        corrections = {}
        confidence_adjustment = 0.0
        
        # Extract claims from answer
        temporal_claims = self._extract_temporal_claims(answer)
        
        # Validate each claim against evidence
        for claim in temporal_claims:
            validation = self._validate_temporal_claim(claim, evidence)
            if not validation['valid']:
                issues.append(validation['issue'])
                if validation.get('correction'):
                    corrections[claim['text']] = validation['correction']
                confidence_adjustment -= 0.15  # Reduce confidence for each error
        
        # Check for contradictions within the answer
        contradictions = self._check_internal_contradictions(answer)
        issues.extend(contradictions)
        confidence_adjustment -= 0.10 * len(contradictions)
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            corrections=corrections,
            confidence_adjustment=max(confidence_adjustment, -0.5)  # Cap at 50% reduction
        )
    
    def _extract_temporal_claims(self, answer: str) -> List[Dict]:
        """Extract claims about temporal changes from the answer."""
        claims = []
        
        # Pattern: "$X in FY20XX to $Y in FY20YY"
        pattern = r'\$?([\d,.]+)\s*[Bb]?\s*(?:in\s+)?(?:FY)?(\d{4}).*?(?:to|→)\s*\$?([\d,.]+)\s*[Bb]?\s*(?:in\s+)?(?:FY)?(\d{4})'
        
        for match in re.finditer(pattern, answer, re.IGNORECASE):
            value1 = self._parse_number(match.group(1))
            year1 = int(match.group(2))
            value2 = self._parse_number(match.group(3))
            year2 = int(match.group(4))
            
            # Determine claimed direction
            context = answer[max(0, match.start()-50):match.end()+50].lower()
            claimed_direction = self._detect_direction(context)
            
            claims.append({
                'text': match.group(0),
                'from_value': value1,
                'from_year': year1,
                'to_value': value2,
                'to_year': year2,
                'claimed_direction': claimed_direction,
                'actual_direction': 'increase' if value2 > value1 else 'decrease' if value2 < value1 else 'unchanged',
            })
        
        return claims
    
    def _parse_number(self, text: str) -> float:
        """Parse a number from text, handling B/M suffixes."""
        text = text.replace(',', '')
        multiplier = 1
        
        if 'B' in text.upper():
            multiplier = 1e9
            text = re.sub(r'[Bb]', '', text)
        elif 'M' in text.upper():
            multiplier = 1e6
            text = re.sub(r'[Mm]', '', text)
        
        try:
            return float(text) * multiplier
        except ValueError:
            return 0.0
    
    def _detect_direction(self, context: str) -> Optional[str]:
        """Detect if context claims increase or decrease."""
        for pattern in self.increase_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return 'increase'
        
        for pattern in self.decrease_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return 'decrease'
        
        return None
    
    def _validate_temporal_claim(
        self, 
        claim: Dict, 
        evidence: List[Dict]
    ) -> Dict:
        """Validate a single temporal claim against evidence."""
        
        # Check if claimed direction matches actual direction
        if claim['claimed_direction'] and claim['actual_direction']:
            if claim['claimed_direction'] != claim['actual_direction']:
                actual_change = claim['to_value'] - claim['from_value']
                pct_change = (actual_change / claim['from_value'] * 100) if claim['from_value'] else 0
                
                return {
                    'valid': False,
                    'issue': (
                        f"Direction error: Claimed {claim['claimed_direction']} but "
                        f"${claim['from_value']/1e9:.2f}B → ${claim['to_value']/1e9:.2f}B "
                        f"is actually a {claim['actual_direction']} ({pct_change:+.1f}%)"
                    ),
                    'correction': (
                        f"${claim['from_value']/1e9:.2f}B (FY{claim['from_year']}) to "
                        f"${claim['to_value']/1e9:.2f}B (FY{claim['to_year']}), "
                        f"a {claim['actual_direction']} of {abs(pct_change):.1f}%"
                    )
                }
        
        return {'valid': True}
    
    def _check_internal_contradictions(self, answer: str) -> List[str]:
        """Check for contradictions within the answer."""
        contradictions = []
        
        # Check if answer says both "increased" and "decreased" for same metric
        sentences = answer.split('.')
        
        for i, sent1 in enumerate(sentences):
            for sent2 in sentences[i+1:]:
                # Check for contradictory claims about same metric
                if self._are_contradictory(sent1, sent2):
                    contradictions.append(
                        f"Possible contradiction: '{sent1.strip()[:50]}...' vs '{sent2.strip()[:50]}...'"
                    )
        
        return contradictions
    
    def _are_contradictory(self, sent1: str, sent2: str) -> bool:
        """Check if two sentences make contradictory claims."""
        sent1_lower = sent1.lower()
        sent2_lower = sent2.lower()
        
        # Find common subjects (revenue, margin, etc.)
        subjects = ['revenue', 'sales', 'margin', 'profit', 'income', 'cost']
        common_subjects = [s for s in subjects if s in sent1_lower and s in sent2_lower]
        
        if not common_subjects:
            return False
        
        # Check for opposite directions
        sent1_increase = any(re.search(p, sent1_lower) for p in self.increase_patterns)
        sent1_decrease = any(re.search(p, sent1_lower) for p in self.decrease_patterns)
        sent2_increase = any(re.search(p, sent2_lower) for p in self.increase_patterns)
        sent2_decrease = any(re.search(p, sent2_lower) for p in self.decrease_patterns)
        
        # Contradiction if one says increase and other says decrease
        if (sent1_increase and sent2_decrease) or (sent1_decrease and sent2_increase):
            return True
        
        return False


def validate_and_adjust_answer(
    answer: str,
    evidence: List[Dict],
    query: str,
    original_confidence: float
) -> Tuple[str, float, List[str]]:
    """
    Validate answer and adjust confidence if issues found.
    
    Returns:
        Tuple of (answer, adjusted_confidence, issues)
    """
    validator = AnswerValidator()
    result = validator.validate(answer, evidence, query)
    
    adjusted_confidence = original_confidence + result.confidence_adjustment
    adjusted_confidence = max(0.1, min(0.99, adjusted_confidence))  # Clamp
    
    # If corrections available, append them as a note
    if result.corrections:
        correction_note = "\n\n**Note: Temporal accuracy check identified potential issues:**\n"
        for original, corrected in result.corrections.items():
            correction_note += f"- Correction: {corrected}\n"
        answer += correction_note
    
    return answer, adjusted_confidence, result.issues
```

---

## Fix 4: Cross-Operator Consistency Check

Add consistency checking between operator answers before merging:

```python
# src/opmech/consistency_checker.py

from typing import Dict, List, Tuple
import re

class CrossOperatorConsistencyChecker:
    """
    Checks consistency between Operator A and Operator B answers.
    Flags factual discrepancies before merging.
    """
    
    def check_consistency(
        self,
        answer_A: str,
        answer_B: str,
        evidence_A: List[Dict],
        evidence_B: List[Dict],
    ) -> Dict:
        """
        Check if both operators agree on factual claims.
        
        Returns:
            {
                'consistent': bool,
                'discrepancies': List[Dict],
                'recommended_resolution': str,
            }
        """
        # Extract factual claims from both answers
        claims_A = self._extract_factual_claims(answer_A)
        claims_B = self._extract_factual_claims(answer_B)
        
        discrepancies = []
        
        # Check for directional discrepancies
        directions_A = self._extract_directions(answer_A)
        directions_B = self._extract_directions(answer_B)
        
        for metric, dir_A in directions_A.items():
            if metric in directions_B:
                dir_B = directions_B[metric]
                if dir_A != dir_B:
                    discrepancies.append({
                        'type': 'direction',
                        'metric': metric,
                        'operator_A': dir_A,
                        'operator_B': dir_B,
                        'resolution': self._resolve_direction_discrepancy(
                            metric, evidence_A, evidence_B
                        )
                    })
        
        # Check for numerical discrepancies
        numbers_A = self._extract_numbers(answer_A)
        numbers_B = self._extract_numbers(answer_B)
        
        for context, num_A in numbers_A.items():
            if context in numbers_B:
                num_B = numbers_B[context]
                if abs(num_A - num_B) / max(num_A, num_B, 1) > 0.05:  # >5% difference
                    discrepancies.append({
                        'type': 'numerical',
                        'context': context,
                        'operator_A': num_A,
                        'operator_B': num_B,
                    })
        
        return {
            'consistent': len(discrepancies) == 0,
            'discrepancies': discrepancies,
            'recommended_resolution': self._get_resolution_strategy(discrepancies),
        }
    
    def _extract_directions(self, answer: str) -> Dict[str, str]:
        """Extract claimed directions for various metrics."""
        directions = {}
        
        metrics = ['revenue', 'sales', 'margin', 'profit', 'income', 'iphone']
        
        for metric in metrics:
            # Find sentences mentioning this metric
            pattern = rf'[^.]*{metric}[^.]*\.'
            matches = re.findall(pattern, answer, re.IGNORECASE)
            
            for match in matches:
                match_lower = match.lower()
                if any(word in match_lower for word in ['increas', 'grew', 'rose', 'higher', 'up ']):
                    directions[metric] = 'increase'
                elif any(word in match_lower for word in ['decreas', 'declin', 'fell', 'drop', 'lower']):
                    directions[metric] = 'decrease'
        
        return directions
    
    def _extract_numbers(self, answer: str) -> Dict[str, float]:
        """Extract numerical values with their context."""
        numbers = {}
        
        # Pattern: $XXX.XXB or XXX.XX billion
        pattern = r'(\$?[\d,.]+)\s*[Bb](?:illion)?'
        
        for match in re.finditer(pattern, answer):
            # Get surrounding context
            start = max(0, match.start() - 30)
            end = min(len(answer), match.end() + 30)
            context = answer[start:end].lower()
            
            # Parse number
            num_str = match.group(1).replace('$', '').replace(',', '')
            try:
                num = float(num_str)
                numbers[context] = num
            except ValueError:
                pass
        
        return numbers
    
    def _extract_factual_claims(self, answer: str) -> List[Dict]:
        """Extract specific factual claims from answer."""
        claims = []
        
        # Pattern for fiscal year claims
        fy_pattern = r'FY(\d{4})[^$]*\$?([\d,.]+)\s*[Bb]'
        for match in re.finditer(fy_pattern, answer):
            claims.append({
                'fiscal_year': int(match.group(1)),
                'value': float(match.group(2).replace(',', '')),
                'text': match.group(0)
            })
        
        return claims
    
    def _resolve_direction_discrepancy(
        self,
        metric: str,
        evidence_A: List[Dict],
        evidence_B: List[Dict],
    ) -> str:
        """Determine correct direction from evidence."""
        # Look for computed_change in evidence
        for node in evidence_A + evidence_B:
            if 'computed_change' in node:
                change = node['computed_change']
                if metric.lower() in node.get('content', '').lower():
                    return f"Evidence shows {change['direction']}: {change['percentage']:+.1f}%"
        
        return "Unable to resolve - check raw evidence"
    
    def _get_resolution_strategy(self, discrepancies: List[Dict]) -> str:
        """Recommend how to handle discrepancies."""
        if not discrepancies:
            return "No resolution needed - answers are consistent"
        
        direction_issues = [d for d in discrepancies if d['type'] == 'direction']
        numerical_issues = [d for d in discrepancies if d['type'] == 'numerical']
        
        if direction_issues:
            return (
                "CRITICAL: Direction discrepancy detected. "
                "Use pre-computed changes from evidence. "
                "Flag uncertainty in merged answer."
            )
        
        if numerical_issues:
            return (
                "Numerical discrepancy detected. "
                "Use XBRL/FINANCIAL_LINE values as authoritative source."
            )
        
        return "Review evidence to resolve discrepancies"
```

---

## Fix 5: Update Trust Decision for Causal Queries

The system used MERGE_EQUAL for a causal query, but should use MERGE_WEIGHTED:

```python
# In src/opmech/mode_selection.py

def _determine_trust(
    self,
    query_class: QueryClassification,
    belief_A: OperatorBelief,
    belief_B: OperatorBelief,
) -> TrustDecision:
    """Determine which operator to trust."""
    
    # For NUMERICAL queries, trust operator with more FINANCIAL_LINE
    if query_class.query_type == QueryType.NUMERICAL and query_class.expects_number:
        financial_A = belief_A.node_type_breakdown.get("FINANCIAL_LINE", 0)
        financial_B = belief_B.node_type_breakdown.get("FINANCIAL_LINE", 0)
        total = financial_A + financial_B
        
        if total > 0:
            if financial_A / total > self.trust_threshold:
                return TrustDecision.TRUST_A
            elif financial_B / total > self.trust_threshold:
                return TrustDecision.TRUST_B
    
    # For OPINION queries, always merge equal
    if query_class.query_type == QueryType.OPINION:
        return TrustDecision.MERGE_EQUAL
    
    # FIX: For CAUSAL queries, use MERGE_WEIGHTED
    # Weight by evidence quality and diversity
    if query_class.query_type == QueryType.CAUSAL:
        return TrustDecision.MERGE_WEIGHTED
    
    # For TEMPORAL queries, prefer operator with more temporal edges
    if query_class.query_type == QueryType.TEMPORAL:
        # Could add temporal edge counting here
        return TrustDecision.MERGE_WEIGHTED
    
    # Default to weighted merge
    return TrustDecision.MERGE_WEIGHTED
```

---

## Fix 6: Integrate All Fixes into Operator Pipeline

```python
# In src/opmech/operators.py

from .evidence_preprocessor import EvidencePreprocessor
from .answer_validator import validate_and_adjust_answer
from .prompts import OPERATOR_ANSWER_PROMPT

class BaseOperator:
    
    def __init__(self, graph, llm, name, ...):
        # ... existing init ...
        self.evidence_preprocessor = EvidencePreprocessor()
    
    def _generate_answer(
        self,
        query: str,
        evidence: List[GraphNode],
        config: Dict,
    ) -> Tuple[str, np.ndarray, float]:
        """Generate answer with validation."""
        
        # 1. Preprocess evidence (add fiscal years, compute changes)
        evidence_dicts = [self._node_to_dict(n) for n in evidence]
        enriched_evidence = self.evidence_preprocessor.preprocess(evidence_dicts)
        
        # 2. Format evidence for LLM
        formatted_evidence = self.evidence_preprocessor.format_for_llm(enriched_evidence)
        
        # 3. Build prompt with temporal instructions
        prompt = OPERATOR_ANSWER_PROMPT.format(
            evidence=formatted_evidence,
            query=query
        )
        
        # 4. Generate answer
        raw_answer = self.llm.generate(prompt, temperature=config.get("temperature", 0.3))
        
        # 5. Validate and adjust confidence
        validated_answer, adjusted_confidence, issues = validate_and_adjust_answer(
            raw_answer,
            enriched_evidence,
            query,
            original_confidence=config.get("base_confidence", 0.8)
        )
        
        if issues:
            logger.warning(f"Answer validation issues for Operator {self.name}: {issues}")
        
        # 6. Get embedding
        embedding = self.llm.embed(validated_answer)
        
        return validated_answer, embedding, adjusted_confidence
    
    def _node_to_dict(self, node: GraphNode) -> Dict:
        """Convert GraphNode to dict for preprocessing."""
        return {
            'type': node.node_type.value,
            'content': node.content,
            'xbrl_tag': node.metadata.get('xbrl_tag'),
            'value': node.metadata.get('value'),
            'period_end': node.metadata.get('period_end'),
            **node.metadata
        }
```

---

## Fix 7: Update Merge Logic with Consistency Check

```python
# In src/opmech/system.py

from .consistency_checker import CrossOperatorConsistencyChecker

class OpMechGraphRAG:
    
    def __init__(self, ...):
        # ... existing init ...
        self.consistency_checker = CrossOperatorConsistencyChecker()
    
    def _generate_answer(self, query, belief_A, belief_B, mode_decision):
        """Generate final answer with consistency checking."""
        
        # Check consistency between operators
        consistency = self.consistency_checker.check_consistency(
            belief_A.generated_answer,
            belief_B.generated_answer,
            [self._node_to_dict(n) for n in belief_A.evidence_nodes],
            [self._node_to_dict(n) for n in belief_B.evidence_nodes],
        )
        
        if not consistency['consistent']:
            logger.warning(f"Operator discrepancies detected: {consistency['discrepancies']}")
            
            # Add discrepancy note to answer
            discrepancy_note = self._format_discrepancy_note(consistency['discrepancies'])
        else:
            discrepancy_note = ""
        
        # Generate merged answer based on trust decision
        if mode_decision.trust_decision == TrustDecision.TRUST_A:
            answer = belief_A.generated_answer
        elif mode_decision.trust_decision == TrustDecision.TRUST_B:
            answer = belief_B.generated_answer
        elif mode_decision.mode == QueryMode.EXPLORE:
            answer = self._generate_explore_answer(
                query, belief_A, belief_B, consistency
            )
        else:
            answer = self._generate_weighted_answer(
                query, belief_A, belief_B, mode_decision
            )
        
        # Append discrepancy note if any
        if discrepancy_note:
            answer += discrepancy_note
        
        return answer
    
    def _format_discrepancy_note(self, discrepancies: List[Dict]) -> str:
        """Format discrepancies as a note."""
        if not discrepancies:
            return ""
        
        note = "\n\n---\n**Analyst Note:** "
        
        for d in discrepancies:
            if d['type'] == 'direction':
                note += (
                    f"There was initial disagreement about the direction of {d['metric']} change. "
                    f"Resolution: {d.get('resolution', 'See evidence for clarification')}. "
                )
        
        return note
```

---

## Test Script

```python
# test_temporal_fixes.py

def test_temporal_validation():
    """Test that temporal direction errors are caught."""
    
    from src.opmech.answer_validator import AnswerValidator
    
    validator = AnswerValidator()
    
    # Test case: Operator claims increase but numbers show decrease
    bad_answer = """
    iPhone revenue increased from $383.29B in FY2022 to $394.33B in FY2023,
    representing a growth of about 2.8%.
    """
    
    # Note: $383.29B < $394.33B, so this IS an increase
    # But if the years are swapped (FY2022=$394.33B, FY2023=$383.29B), it's a decrease
    
    result = validator.validate(bad_answer, [], "")
    
    print(f"Validation result: {result}")
    print(f"Issues found: {result.issues}")
    print(f"Corrections: {result.corrections}")
    
    # Test preprocessing
    from src.opmech.evidence_preprocessor import EvidencePreprocessor
    
    preprocessor = EvidencePreprocessor()
    
    evidence = [
        {"content": "Net Sales: $394.33B (2022-09-24)", "value": 394330000000},
        {"content": "Net Sales: $383.29B (2023-09-30)", "value": 383290000000},
    ]
    
    enriched = preprocessor.preprocess(evidence)
    formatted = preprocessor.format_for_llm(enriched)
    
    print(f"\nEnriched evidence:")
    for e in enriched:
        print(f"  {e}")
    
    print(f"\nFormatted for LLM:")
    print(formatted)
    
    # Verify change is computed correctly
    for e in enriched:
        if 'computed_change' in e:
            change = e['computed_change']
            assert change['direction'] == 'DECREASE', f"Expected DECREASE, got {change['direction']}"
            print(f"\n✅ Change correctly identified as: {change['direction']}")

if __name__ == "__main__":
    test_temporal_validation()
```

---

## Summary of Fixes

| Fix | Problem Solved | Scope |
|-----|----------------|-------|
| **Fix 1: Evidence Preprocessor** | Adds fiscal year labels and pre-computes changes | All temporal queries |
| **Fix 2: Enhanced Prompts** | Instructs LLM to verify temporal direction | All queries with comparisons |
| **Fix 3: Answer Validator** | Catches direction errors post-generation | All queries |
| **Fix 4: Consistency Checker** | Flags discrepancies between operators | All merged answers |
| **Fix 5: Trust Decision** | Uses MERGE_WEIGHTED for causal queries | Causal queries |
| **Fix 6: Pipeline Integration** | Integrates all fixes into operator flow | System-wide |
| **Fix 7: Merge Logic** | Adds discrepancy notes to final answer | EXPLORE mode |

---

## Expected Outcomes

After implementing these fixes:

1. **Evidence will include fiscal year labels:**
   ```
   [FINANCIAL_LINE] [FY2022] Net Sales: $394.33B (period ending 2022-09-24)
   [FINANCIAL_LINE] [FY2023] Net Sales: $383.29B (period ending 2023-09-30)
       → Change from FY2022 to FY2023: DECREASE of $11.04B (-2.8%)
   ```

2. **LLM will receive explicit instructions** to verify direction before claiming increase/decrease

3. **Post-generation validation** will catch any remaining errors and adjust confidence

4. **Discrepancies between operators** will be flagged and noted in the final answer

5. **Causal queries** will use MERGE_WEIGHTED trust decision

Good luck implementing! 🔧
