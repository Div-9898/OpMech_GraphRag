# OpMech Evidence Grounding Diagnosis (7B Model Optimized)

## Context: Qwen 2.5 7B Instruct

The system uses a **7B parameter model**, which changes the analysis:

### Why Low Δ_A is Likely GOOD for 7B

| Factor | Large Model (70B+) | Small Model (7B) |
|--------|-------------------|------------------|
| Parametric knowledge | Extensive | Limited |
| Knows Apple's exact FY2023 revenue? | Probably | **Unlikely** |
| Same answer from different evidence | Could be memorized | **Likely from evidence** |
| Risk | Using training data | Hallucination |

**Key insight**: If a 7B model gives the correct specific figure ($383.29B), it almost certainly came from the evidence, not memorized training data.

---

## Revised Diagnostic Tests for 7B

### Test 1: Evidence-Answer Alignment

Check if specific numbers in the answer exist in the evidence:

```python
def test_evidence_answer_alignment():
    """
    For 7B models: verify answer figures come from evidence.
    
    7B models have limited memorization, so if they produce
    specific figures, those figures came from the context.
    """
    
    system = OpMechGraphRAG(...)
    
    test_queries = [
        "What was Apple's total revenue in FY2023?",
        "What was Apple's R&D expense in FY2023?",
        "What was Apple's net income in FY2023?",
    ]
    
    for query in test_queries:
        result = system.query(query)
        
        # Extract numbers from evidence
        evidence_numbers = set()
        for node in result.evidence_A + result.evidence_B:
            numbers = re.findall(r'\$?[\d,]+\.?\d*\s*[BMK]?(?:illion)?', node.content)
            evidence_numbers.update(numbers)
        
        # Extract numbers from answer
        answer_numbers = re.findall(r'\$?[\d,]+\.?\d*\s*[BMK]?(?:illion)?', result.answer)
        
        # Check alignment
        aligned = []
        unaligned = []
        
        for num in answer_numbers:
            num_clean = num.replace(',', '').replace('$', '').strip()
            found = any(num_clean in ev.replace(',', '').replace('$', '') 
                       for ev in evidence_numbers)
            if found:
                aligned.append(num)
            else:
                unaligned.append(num)
        
        print(f"\nQuery: {query[:50]}...")
        print(f"  Evidence numbers: {len(evidence_numbers)} unique figures")
        print(f"  Answer numbers: {len(answer_numbers)} figures")
        print(f"  ✅ Aligned with evidence: {aligned}")
        if unaligned:
            print(f"  ⚠️ Not found in evidence: {unaligned}")
            print(f"     (Could be: inference, rounding, or hallucination)")
        
        # Score
        if answer_numbers:
            score = len(aligned) / len(answer_numbers)
            print(f"  Alignment score: {score:.0%}")
```

### Test 2: Hallucination Detection (Primary Risk for 7B)

```python
def test_hallucination_detection():
    """
    7B models may hallucinate plausible-sounding but incorrect details.
    Check for common hallucination patterns.
    """
    
    system = OpMechGraphRAG(...)
    result = system.query("What was Apple's total revenue in FY2023?")
    
    # Known hallucination patterns for financial queries
    hallucination_signals = [
        # Overly precise numbers not in evidence
        r'\$\d{3}\.\d{3}B',  # e.g., "$394.567B" - too precise
        
        # Round numbers that look made up
        r'\$\d00\s*billion',  # e.g., "$400 billion" - suspiciously round
        
        # Comparisons not supported by evidence
        r'(increased|decreased|grew|declined)\s+by\s+\d+%',
        
        # Specific dates/quarters not in evidence
        r'Q[1-4]\s+\d{4}',
    ]
    
    potential_hallucinations = []
    
    for pattern in hallucination_signals:
        matches = re.findall(pattern, result.answer)
        for match in matches:
            # Check if this appears in evidence
            in_evidence = any(match in node.content 
                            for node in result.evidence_A + result.evidence_B)
            if not in_evidence:
                potential_hallucinations.append(match)
    
    if potential_hallucinations:
        print(f"⚠️ Potential hallucinations detected:")
        for h in potential_hallucinations:
            print(f"   - '{h}' not found in evidence")
    else:
        print("✅ No obvious hallucinations detected")
    
    return potential_hallucinations
```

### Test 3: Instruction Following (7B Strength)

```python
def test_instruction_following():
    """
    7B models are generally good at following instructions.
    Test if the model respects the prompt format.
    """
    
    # Test with explicit format requirement
    query = "What was Apple's revenue in FY2023?"
    
    # Prompt that requests specific format
    prompt = f"""Answer in this exact format:
REVENUE: [number]
SOURCE: [where you found this]

Evidence:
{evidence_text}

Question: {query}

Answer:"""
    
    response = llm.generate(prompt)
    
    # Check if format was followed
    has_revenue = "REVENUE:" in response
    has_source = "SOURCE:" in response
    
    if has_revenue and has_source:
        print("✅ 7B model followed format instructions")
    else:
        print("⚠️ 7B model did not follow format")
        print(f"   Response: {response[:200]}...")
```

---

## Optimized Prompts for Qwen 2.5 7B

### For EXPLOIT Mode (Factual Queries)

```python
EXPLOIT_PROMPT_7B = """Read the evidence below and answer the question.

Evidence:
{evidence}

Question: {query}

Give a direct answer using only the evidence above. Include the specific number if available.

Answer:"""
```

### For ADAPTIVE Mode (Analysis Queries)

```python
ADAPTIVE_PROMPT_7B = """Read the evidence below and answer the question.

Evidence:
{evidence}

Question: {query}

Provide your answer based on the evidence. Explain your reasoning briefly.

Answer:"""
```

### For EXPLORE Mode (Opinion Queries)

```python
EXPLORE_PROMPT_7B = """Read the evidence below. The question asks for analysis/opinion.

Evidence:
{evidence}

Question: {query}

Based on the evidence, discuss different perspectives. Be balanced.

Answer:"""
```

### Key Prompt Principles for 7B

1. **Keep it simple** - Avoid complex multi-step instructions
2. **Evidence first** - Put context before question
3. **Clear task** - One clear instruction per prompt
4. **Short** - Minimize prompt length to leave room for evidence
5. **No jargon** - Avoid terms like "synthesize", "elucidate"

---

## What Low Δ_A Actually Means for 7B

### Scenario Analysis

```
Revenue Query Results:
- Operator A evidence: FINANCIAL_LINE with "$383.29B"
- Operator B evidence: TEXT_SECTION with "revenue of $383 billion"
- Δ_E = 0.63 (different node types and contexts)
- Δ_A = 0.03 (both answers say ~$383B)
```

**Interpretation for 7B:**

1. **Both evidence sets contain the same core fact** ($383B revenue)
2. **7B model correctly extracted** this fact from both
3. **Low Δ_A indicates** robust extraction, not memorization
4. **High Δ_E indicates** operators explored different paths
5. **This is working correctly!**

### When to Be Concerned (7B)

| Signal | Concern Level | Action |
|--------|---------------|--------|
| Answer has figures not in evidence | 🟡 Medium | Check for hallucination |
| Answer contradicts evidence | 🔴 High | Fix prompt or evidence selection |
| Answer is generic/vague | 🟡 Medium | Model may not understand evidence |
| Answer copies evidence verbatim | 🟢 Low | Actually fine for 7B |

---

## Quick Diagnostic Script

```python
def run_7b_diagnostic():
    """Quick diagnostic for 7B model grounding."""
    
    print("=" * 60)
    print("7B MODEL GROUNDING DIAGNOSTIC")
    print("=" * 60)
    
    system = OpMechGraphRAG(...)
    
    # Test query
    query = "What was Apple's total revenue in FY2023?"
    result = system.query(query)
    
    print(f"\nQuery: {query}")
    print(f"Answer: {result.answer[:300]}...")
    print(f"\nMode: {result.mode}, Confidence: {result.confidence:.0%}")
    
    # Extract key figure
    revenue_match = re.search(r'\$?([\d,]+\.?\d*)\s*[Bb](?:illion)?', result.answer)
    
    if revenue_match:
        answer_revenue = revenue_match.group(1).replace(',', '')
        print(f"\nExtracted revenue: ${answer_revenue}B")
        
        # Check if this figure exists in evidence
        evidence_text = " ".join([n.content for n in result.evidence_A + result.evidence_B])
        
        if answer_revenue in evidence_text.replace(',', ''):
            print("✅ Revenue figure FOUND in evidence")
            print("   → 7B model is correctly grounded")
        else:
            # Check for close matches (rounding)
            try:
                answer_val = float(answer_revenue)
                evidence_numbers = re.findall(r'([\d,]+\.?\d*)\s*(?:billion|B\b|000000000)', evidence_text)
                
                for ev_num in evidence_numbers:
                    ev_val = float(ev_num.replace(',', ''))
                    if ev_val > 1000000:  # Probably in raw form
                        ev_val = ev_val / 1000000000
                    
                    if abs(answer_val - ev_val) < 1:  # Within $1B
                        print(f"✅ Revenue figure matches evidence ({ev_num})")
                        print("   → 7B model is correctly grounded")
                        break
                else:
                    print("⚠️ Revenue figure not found in evidence")
                    print("   → May be hallucination or inference")
            except:
                print("⚠️ Could not parse revenue for comparison")
    else:
        print("⚠️ Could not extract revenue figure from answer")
    
    # Show evidence sample
    print("\n" + "-" * 40)
    print("Evidence Sample (first 3 nodes from each operator):")
    print("-" * 40)
    
    for i, node in enumerate(result.evidence_A[:3]):
        print(f"[A-{i+1}] {node.type}: {node.content[:100]}...")
    
    for i, node in enumerate(result.evidence_B[:3]):
        print(f"[B-{i+1}] {node.type}: {node.content[:100]}...")
    
    print("=" * 60)


if __name__ == "__main__":
    run_7b_diagnostic()
```

---

## Conclusion for 7B Models

### The Observation is Likely GOOD

```
High Δ_E (63%) + Low Δ_A (3%) with 7B model means:

1. Operators found different evidence paths ✓
2. Both paths contained the correct information ✓  
3. 7B model extracted the same answer from both ✓
4. 7B model is NOT using memorized knowledge ✓
   (It doesn't have detailed Apple financials memorized)
```

### Primary Risk for 7B: Hallucination, Not Memorization

Focus diagnostic efforts on:
- Detecting fabricated details
- Ensuring specific numbers come from evidence
- Checking for plausible-sounding but wrong claims

### No Action Needed If:

- Answer contains specific figures from evidence ✓
- Answer doesn't contain figures NOT in evidence ✓
- Answer is consistent with evidence content ✓

**The current behavior (low Δ_A despite high Δ_E) is actually a sign the system is working well with a 7B model!**
