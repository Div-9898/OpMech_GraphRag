# OpMech Hop Termination Diagnosis and Fix

## Problem Statement

All queries are stopping at exactly 2 hops, regardless of query complexity or divergence level:

```
Revenue Query:  Hop 1 → Hop 2 → STOP (Δ=0.335)
Margin Query:   Hop 1 → Hop 2 → STOP (Δ=0.340)
iPhone Query:   Hop 1 → Hop 2 → STOP (Δ=0.371)
```

The log message says "Max hops reached" but:
- `max_hops=4` was configured
- Divergence (0.33-0.37) is still above `tau_low=0.25`
- System should continue until convergence OR max_hops

**Expected behavior:**
- Simple queries (EXPLOIT): 2-3 hops, stop when Δ < 0.25
- Moderate queries (ADAPTIVE): 3-4 hops, balanced exploration
- Complex queries (EXPLORE): 3-4 hops, thorough exploration

---

## Task 1: Diagnose the Issue

### Step 1.1: Find the Termination Logic

Search for where traversal stops:

```bash
# Find termination conditions
grep -rn "max_hops" src/opmech/
grep -rn "break" src/opmech/system.py
grep -rn "return.*result" src/opmech/system.py
grep -rn "while.*hop" src/opmech/system.py
grep -rn "for.*hop" src/opmech/system.py
```

### Step 1.2: Check the Main Query Loop

Look in `system.py` for the traversal loop. It probably looks something like:

```python
def query(self, query_text: str) -> QueryResult:
    # ... initialization ...
    
    for hop in range(1, max_hops + 1):
        # Run operators
        # Calculate commutator
        # Check termination  <-- FIND THIS
        
        if some_condition:  # <-- WHAT IS THIS CONDITION?
            break
```

### Step 1.3: Log the Actual Termination Reason

Add temporary debug logging:

```python
def query(self, query_text: str) -> QueryResult:
    # ... 
    
    for hop in range(1, max_hops + 1):
        # ... operator execution ...
        
        # DEBUG: Log all termination checks
        logger.debug(f"Hop {hop} termination check:")
        logger.debug(f"  - hop >= max_hops? {hop} >= {max_hops} = {hop >= max_hops}")
        logger.debug(f"  - delta < tau_low? {delta:.3f} < {self.tau_low} = {delta < self.tau_low}")
        logger.debug(f"  - delta_change < threshold? ...")
        
        if termination_condition:
            logger.info(f"Terminating at hop {hop} because: {reason}")
            break
```

---

## Task 2: Identify the Bug

### Likely Cause 1: Hardcoded Max Hops

Check if there's a hardcoded `2` somewhere:

```python
# WRONG - hardcoded
max_hops = 2

# or
for hop in range(1, 3):  # Only 2 iterations!
```

### Likely Cause 2: Wrong Termination Condition

```python
# WRONG - terminates too early
if delta < 0.40:  # Should be tau_low (0.25)
    break

# WRONG - terminates after any improvement
if prev_delta > delta:
    break  # "It improved, good enough!"
```

### Likely Cause 3: Mode-Based Early Exit

```python
# WRONG - exits immediately after mode is determined
mode = self._determine_mode(...)
if mode == QueryMode.EXPLOIT:
    break  # "We know the mode, stop!"
```

### Likely Cause 4: Dynamic Max Hops Calculation

```python
# Check if max_hops is being recalculated
# The log shows "Hop 2/6" which suggests max_hops changed to 6
# But still stopped at 2

effective_max_hops = self._calculate_max_hops(query_type, delta)
# This might be returning 2!
```

### Likely Cause 5: Convergence Check Too Aggressive

```python
# WRONG - considers 0.34 as "converged"
if delta < 0.35:
    logger.info("Max hops reached")  # Misleading message!
    break
```

---

## Task 3: Implement the Fix

### Correct Termination Logic

```python
# In system.py

class OpMechGraphRAG:
    def __init__(self, ...):
        # ... existing init ...
        
        # Termination thresholds
        self.tau_low = tau_low          # 0.25 - convergence threshold
        self.tau_high = tau_high        # 0.60 - explore threshold
        self.max_hops = max_hops        # 4 - safety limit
        self.min_improvement = 0.02     # Minimum delta improvement to continue
        self.stability_window = 2       # Hops to check for stability
    
    def query(self, query_text: str) -> QueryResult:
        """Main query method with proper termination logic."""
        
        # Classify query
        query_class = self.query_classifier.classify(query_text)
        
        # Determine effective max hops based on query complexity
        effective_max_hops = self._get_effective_max_hops(query_class)
        
        logger.info(f"Processing query: {query_text[:50]}...")
        logger.info(f"Query type: {query_class.query_type.value}, complexity: {query_class.complexity}")
        logger.info(f"Max hops: {effective_max_hops}")
        
        trajectory = []
        belief_A = None
        belief_B = None
        
        for hop in range(1, effective_max_hops + 1):
            logger.info(f"Hop {hop}/{effective_max_hops}")
            
            # Execute operators
            belief_A = self.operator_A.execute(query_text, belief_A, hop)
            belief_B = self.operator_B.execute(query_text, belief_B, hop)
            
            # Calculate commutator
            commutator = self._calculate_commutator(belief_A, belief_B)
            trajectory.append(commutator)
            
            logger.info(f"Divergence at hop {hop}: Δ={commutator.combined:.3f} "
                       f"(Δ_E={commutator.delta_E:.3f}, Δ_V={commutator.delta_V:.3f}, "
                       f"Δ_A={commutator.delta_A:.3f}, Δ_C={commutator.delta_C:.3f})")
            
            # Check termination
            should_stop, reason = self._should_terminate(
                trajectory, hop, effective_max_hops, query_class
            )
            
            if should_stop:
                logger.info(f"Stopping at hop {hop}: {reason}")
                break
            
            # Apply convergence pressure if needed
            if commutator.delta_E > 0.8:
                logger.info(f"Applying convergence pressure at hop {hop} (Δ_E={commutator.delta_E:.3f} > 0.8)")
                self._apply_convergence_pressure(belief_A, belief_B)
        
        # Build final result
        return self._build_result(query_text, belief_A, belief_B, trajectory, query_class)
    
    def _get_effective_max_hops(self, query_class) -> int:
        """
        Determine max hops based on query complexity.
        
        Simple queries don't need many hops.
        Complex queries benefit from more exploration.
        """
        base_max_hops = self.max_hops
        
        if query_class.complexity == "simple":
            # Simple factual queries - 2-3 hops usually enough
            return min(base_max_hops, 3)
        
        elif query_class.complexity == "complex":
            # Complex queries - allow full exploration
            return base_max_hops + 1  # Allow extra hop
        
        else:  # moderate
            return base_max_hops
    
    def _should_terminate(
        self, 
        trajectory: List, 
        current_hop: int, 
        max_hops: int,
        query_class
    ) -> Tuple[bool, str]:
        """
        Determine if traversal should stop.
        
        Returns: (should_stop, reason)
        """
        
        current = trajectory[-1]
        delta = current.combined
        delta_A = current.delta_A
        
        # -----------------------------------------------------------------
        # CONDITION 1: Reached max hops (safety limit)
        # -----------------------------------------------------------------
        if current_hop >= max_hops:
            return True, f"Reached max hops ({max_hops})"
        
        # -----------------------------------------------------------------
        # CONDITION 2: Strong convergence (delta below threshold)
        # -----------------------------------------------------------------
        if delta < self.tau_low:
            return True, f"Converged: Δ={delta:.3f} < τ_low={self.tau_low}"
        
        # -----------------------------------------------------------------
        # CONDITION 3: Answer agreement is excellent
        # -----------------------------------------------------------------
        # If operators strongly agree on answer, we can stop early
        if delta_A < 0.05 and query_class.query_type.value == "numerical":
            if delta < 0.40:  # Combined also reasonable
                return True, f"Strong answer agreement: Δ_A={delta_A:.3f} < 0.05"
        
        # -----------------------------------------------------------------
        # CONDITION 4: Stability check (not improving)
        # -----------------------------------------------------------------
        if len(trajectory) >= 2:
            prev_delta = trajectory[-2].combined
            improvement = prev_delta - delta
            
            # If divergence increased, something is wrong
            if improvement < -0.05:
                logger.warning(f"Divergence increased! {prev_delta:.3f} → {delta:.3f}")
                # Don't stop, but note the issue
            
            # If improvement is minimal and we've done at least 2 hops
            if improvement < self.min_improvement and current_hop >= 2:
                # Check if we're in a good state
                if delta < 0.45:
                    return True, f"Stabilized: improvement={improvement:.3f} < {self.min_improvement}, Δ={delta:.3f}"
        
        # -----------------------------------------------------------------
        # CONDITION 5: Query-type specific early termination
        # -----------------------------------------------------------------
        
        # For EXPLOIT-destined queries, can stop earlier
        if query_class.query_type.value == "numerical" and query_class.complexity == "simple":
            if delta < 0.35 and delta_A < 0.10:
                return True, f"Simple numerical query converged: Δ={delta:.3f}, Δ_A={delta_A:.3f}"
        
        # For EXPLORE queries, encourage more exploration
        if query_class.query_type.value == "opinion":
            if current_hop < 3:  # Force at least 3 hops for opinion
                return False, ""
        
        # -----------------------------------------------------------------
        # DEFAULT: Continue
        # -----------------------------------------------------------------
        return False, ""
```

---

## Task 4: Add Detailed Logging

Update logging to clearly show WHY traversal stopped:

```python
# In system.py

def _log_termination_summary(
    self, 
    trajectory: List, 
    termination_reason: str,
    query_class
):
    """Log a summary of the traversal."""
    
    logger.info("=" * 60)
    logger.info("TRAVERSAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Query type: {query_class.query_type.value} ({query_class.complexity})")
    logger.info(f"Total hops: {len(trajectory)}")
    logger.info(f"Termination reason: {termination_reason}")
    logger.info("")
    logger.info("Divergence trajectory:")
    
    for i, t in enumerate(trajectory):
        marker = "→" if i < len(trajectory) - 1 else "■"
        logger.info(f"  Hop {i+1}: Δ={t.combined:.3f} (E={t.delta_E:.3f}, V={t.delta_V:.3f}, A={t.delta_A:.3f}) {marker}")
    
    # Show improvement
    if len(trajectory) >= 2:
        total_improvement = trajectory[0].combined - trajectory[-1].combined
        pct_improvement = (total_improvement / trajectory[0].combined) * 100
        logger.info(f"")
        logger.info(f"Total improvement: {trajectory[0].combined:.3f} → {trajectory[-1].combined:.3f} ({pct_improvement:.1f}% reduction)")
    
    logger.info("=" * 60)
```

---

## Task 5: Test the Fix

### Test 1: Simple Numerical Query (EXPLOIT)

```python
query = "What was Apple's total revenue in FY2023?"

# Expected:
# - Query type: numerical (simple)
# - Max hops: 3 (limited for simple)
# - Should stop at hop 2-3 when Δ_A < 0.05 and Δ < 0.35
# - Termination reason: "Simple numerical query converged"
```

### Test 2: Opinion Query (EXPLORE)

```python
query = "Is Apple's gross margin pressure cyclical or structural?"

# Expected:
# - Query type: opinion (complex)
# - Max hops: 5 (extended for complex)
# - Should do at least 3 hops (forced for opinion)
# - Termination reason: "Reached max hops" or "Stabilized"
```

### Test 3: Causal Query (ADAPTIVE)

```python
query = "What factors drove iPhone revenue changes in FY2023?"

# Expected:
# - Query type: causal (moderate)
# - Max hops: 4
# - Should do 3-4 hops
# - Termination reason: "Stabilized" or "Reached max hops"
```

### Test Script

```python
# tests/test_hop_termination.py

def test_hop_counts():
    """Verify queries use appropriate number of hops."""
    
    system = OpMechGraphRAG(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        vllm_url="http://localhost:8000/v1",
        tau_low=0.25,
        tau_high=0.60,
        max_hops=4
    )
    
    test_cases = [
        {
            "query": "What was Apple's total revenue in FY2023?",
            "expected_type": "numerical",
            "min_hops": 2,
            "max_hops": 3,
        },
        {
            "query": "Is Apple's gross margin pressure cyclical or structural?",
            "expected_type": "opinion",
            "min_hops": 3,  # Force 3 for opinion
            "max_hops": 5,
        },
        {
            "query": "What factors drove iPhone revenue changes in FY2023?",
            "expected_type": "causal",
            "min_hops": 2,
            "max_hops": 4,
        },
    ]
    
    for test in test_cases:
        result = system.query(test["query"])
        
        actual_hops = result.hops_used
        
        assert actual_hops >= test["min_hops"], \
            f"Query '{test['query'][:30]}...' used {actual_hops} hops, expected >= {test['min_hops']}"
        
        assert actual_hops <= test["max_hops"], \
            f"Query '{test['query'][:30]}...' used {actual_hops} hops, expected <= {test['max_hops']}"
        
        print(f"✓ {test['expected_type']}: {actual_hops} hops (expected {test['min_hops']}-{test['max_hops']})")
    
    system.close()


if __name__ == "__main__":
    test_hop_counts()
```

---

## Task 6: Expected Output After Fix

### Revenue Query (Simple Numerical)

```
18:26:50 | INFO     | Processing query: What was Apple's total revenue in FY2023?...
18:26:50 | INFO     | Query type: numerical, complexity: simple
18:26:50 | INFO     | Max hops: 3
18:26:50 | INFO     | Hop 1/3
18:26:51 | INFO     | Divergence at hop 1: Δ=0.606 (Δ_E=1.000, Δ_V=1.000, Δ_A=0.054)
18:26:51 | INFO     | Applying convergence pressure at hop 1 (Δ_E=1.000 > 0.8)
18:27:31 | INFO     | Hop 2/3
18:27:32 | INFO     | Divergence at hop 2: Δ=0.335 (Δ_E=0.632, Δ_V=0.571, Δ_A=0.034)
18:27:32 | INFO     | Stopping at hop 2: Simple numerical query converged: Δ=0.335, Δ_A=0.034
============================================================
TRAVERSAL SUMMARY
============================================================
Query type: numerical (simple)
Total hops: 2
Termination reason: Simple numerical query converged: Δ=0.335, Δ_A=0.034

Divergence trajectory:
  Hop 1: Δ=0.606 (E=1.000, V=1.000, A=0.054) →
  Hop 2: Δ=0.335 (E=0.632, V=0.571, A=0.034) ■

Total improvement: 0.606 → 0.335 (44.7% reduction)
============================================================
```

### Margin Query (Opinion - Should Do 3+ Hops)

```
18:28:09 | INFO     | Processing query: Is Apple's gross margin pressure cyclical or struc...
18:28:09 | INFO     | Query type: opinion, complexity: complex
18:28:09 | INFO     | Max hops: 5
18:28:09 | INFO     | Hop 1/5
18:28:09 | INFO     | Divergence at hop 1: Δ=0.569 (Δ_E=1.000, Δ_V=0.800, Δ_A=0.054)
18:28:09 | INFO     | Applying convergence pressure at hop 1 (Δ_E=1.000 > 0.8)
18:29:48 | INFO     | Hop 2/5
18:29:50 | INFO     | Divergence at hop 2: Δ=0.340 (Δ_E=0.611, Δ_V=0.667, Δ_A=0.037)
18:29:50 | INFO     | Opinion query - continuing to hop 3 (minimum 3 hops for opinion)
18:31:27 | INFO     | Hop 3/5
18:31:28 | INFO     | Divergence at hop 3: Δ=0.312 (Δ_E=0.550, Δ_V=0.600, Δ_A=0.030)
18:31:28 | INFO     | Stopping at hop 3: Stabilized: improvement=0.028 < 0.03, Δ=0.312
============================================================
TRAVERSAL SUMMARY
============================================================
Query type: opinion (complex)
Total hops: 3
Termination reason: Stabilized: improvement=0.028 < 0.03, Δ=0.312

Divergence trajectory:
  Hop 1: Δ=0.569 (E=1.000, V=0.800, A=0.054) →
  Hop 2: Δ=0.340 (E=0.611, V=0.667, A=0.037) →
  Hop 3: Δ=0.312 (E=0.550, V=0.600, A=0.030) ■

Total improvement: 0.569 → 0.312 (45.2% reduction)
============================================================
```

### iPhone Query (Causal - Should Do 3-4 Hops)

```
18:33:07 | INFO     | Processing query: What factors drove iPhone revenue changes in FY202...
18:33:07 | INFO     | Query type: causal, complexity: moderate
18:33:07 | INFO     | Max hops: 4
18:33:07 | INFO     | Hop 1/4
18:33:07 | INFO     | Divergence at hop 1: Δ=0.542 (Δ_E=0.857, Δ_V=0.909, Δ_A=0.038)
18:33:07 | INFO     | Applying convergence pressure at hop 1 (Δ_E=0.857 > 0.8)
18:35:05 | INFO     | Hop 2/4
18:35:06 | INFO     | Divergence at hop 2: Δ=0.371 (Δ_E=0.600, Δ_V=0.583, Δ_A=0.163)
18:36:48 | INFO     | Hop 3/4
18:36:49 | INFO     | Divergence at hop 3: Δ=0.345 (Δ_E=0.520, Δ_V=0.510, Δ_A=0.140)
18:36:49 | INFO     | Stopping at hop 3: Stabilized: improvement=0.026 < 0.03, Δ=0.345
============================================================
TRAVERSAL SUMMARY
============================================================
Query type: causal (moderate)
Total hops: 3
Termination reason: Stabilized: improvement=0.026 < 0.03, Δ=0.345

Divergence trajectory:
  Hop 1: Δ=0.542 (E=0.857, V=0.909, A=0.038) →
  Hop 2: Δ=0.371 (E=0.600, V=0.583, A=0.163) →
  Hop 3: Δ=0.345 (E=0.520, V=0.510, A=0.140) ■

Total improvement: 0.542 → 0.345 (36.3% reduction)
============================================================
```

---

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| Max hops | Fixed at 2 (bug) | Dynamic based on query complexity |
| Simple queries | 2 hops | 2-3 hops |
| Opinion queries | 2 hops | 3-5 hops (minimum 3 enforced) |
| Causal queries | 2 hops | 3-4 hops |
| Termination logging | "Max hops reached" (misleading) | Clear reason for stopping |
| Convergence check | Unknown condition | Explicit delta thresholds |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/opmech/system.py` | Update `query()` method with new termination logic |
| `src/opmech/system.py` | Add `_should_terminate()` method |
| `src/opmech/system.py` | Add `_get_effective_max_hops()` method |
| `src/opmech/system.py` | Add `_log_termination_summary()` method |
| `tests/test_hop_termination.py` | New test file for hop count verification |

---

## Verification Checklist

After implementing the fix, verify:

- [ ] Simple numerical queries: 2-3 hops
- [ ] Opinion queries: 3+ hops (minimum enforced)
- [ ] Causal queries: 3-4 hops
- [ ] Termination reason is logged clearly
- [ ] Divergence trajectory is logged
- [ ] All existing tests still pass (mode selection, trust decision, answer accuracy)
