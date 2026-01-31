# OpMech Frontend Chatbot Response Fix

## The Problem

The chatbot is returning **generic/templated responses** instead of the **actual answers** from the OpMech backend.

### Current Broken Output:
```
User: "profits from macbook"

Bot Response (WRONG):
"Based on my analysis of Apple's SEC filings, I can provide the following 
information: The dual-operator system has analyzed both structured financial 
data and narrative disclosures to provide a comprehensive answer. The mode 
selected (ADAPTIVE) indicates a balanced analysis approach."
```

**This is a generic template, NOT the actual answer!**

### Expected Output:
```
User: "profits from macbook"

Bot Response (CORRECT):
"Based on Apple's SEC filings, Mac revenue for FY2023 was $29.36 billion, 
representing approximately 7.7% of total revenue. The Mac segment showed 
[actual data from OpMech response]..."

Mode: ADAPTIVE (75%)
Evidence: Financial (8), Text (3), Note (2)
```

---

## Root Cause Analysis

The frontend is likely doing one of these:

### Cause 1: Hardcoded/Template Response
```typescript
// WRONG - Returns template instead of actual response
const handleResponse = (response) => {
  setMessage({
    content: `Based on my analysis of Apple's SEC filings, I can provide the following 
    information: The dual-operator system has analyzed both structured financial 
    data and narrative disclosures...`, // HARDCODED!
    mode: response.mode,
    confidence: response.confidence
  });
};
```

### Cause 2: Not Extracting Answer from Response
```typescript
// WRONG - Ignores the actual answer
const handleResponse = (response) => {
  // response.answer exists but is not used!
  setMessage({
    content: genericTemplate,  // Should be: response.answer
    mode: response.mode
  });
};
```

### Cause 3: API Response Not Parsed Correctly
```typescript
// WRONG - Parsing issue
const response = await fetch('/api/query', { ... });
const data = await response.json();

// data.answer might be nested differently than expected
setMessage({
  content: data.answer,  // But actual path might be data.result.answer
});
```

### Cause 4: Mock/Placeholder Still Active
```typescript
// WRONG - Mock response not replaced with real API call
const queryOpMech = async (query: string) => {
  // TODO: Replace with actual API call
  return {
    answer: "Based on my analysis of Apple's SEC filings...", // PLACEHOLDER!
    mode: "ADAPTIVE",
    confidence: 0.75
  };
};
```

---

## Task 1: Find the Bug

### Step 1.1: Search for Hardcoded Response

```bash
# Find the hardcoded template text
grep -rn "Based on my analysis" src/
grep -rn "dual-operator system has analyzed" src/
grep -rn "balanced analysis approach" src/
```

### Step 1.2: Check API Response Handling

```bash
# Find where API response is handled
grep -rn "setMessage" src/
grep -rn "response.answer" src/
grep -rn "handleResponse" src/
grep -rn "onQueryComplete" src/
```

### Step 1.3: Check for Mock Data

```bash
# Find mock/placeholder responses
grep -rn "TODO" src/
grep -rn "PLACEHOLDER" src/
grep -rn "mock" src/
grep -rn "dummy" src/
```

---

## Task 2: Fix the Response Handling

### The Correct Implementation

```typescript
// src/components/chat/ChatInterface.tsx

interface OpMechResponse {
  answer: string;           // THE ACTUAL ANSWER - use this!
  mode: 'EXPLOIT' | 'ADAPTIVE' | 'EXPLORE';
  confidence: number;
  metrics: {
    hops_used: number;
    final_delta: number;
    delta_A: number;
    delta_E: number;
    query_type: string;
    trust_decision: string;
  };
  evidence: {
    evidence_A: Array<{ type: string; content: string }>;
    evidence_B: Array<{ type: string; content: string }>;
  };
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (query: string) => {
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setIsLoading(true);

    try {
      // Call OpMech API
      const response = await queryOpMech(query);
      
      // CRITICAL: Use response.answer, NOT a template!
      const botMessage: Message = {
        role: 'assistant',
        content: response.answer,  // <-- THE ACTUAL ANSWER!
        metadata: {
          mode: response.mode,
          confidence: response.confidence,
          hopsUsed: response.metrics.hops_used,
          queryType: response.metrics.query_type,
          trustDecision: response.metrics.trust_decision,
          evidenceTypes: countEvidenceTypes(response.evidence),
          delta: response.metrics.final_delta,
          deltaA: response.metrics.delta_A,
        }
      };
      
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      console.error('Query failed:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error processing query: ${error.message}`,
        metadata: { error: true }
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // ... rest of component
};
```

### API Call Function

```typescript
// src/api/opmech.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function queryOpMech(query: string): Promise<OpMechResponse> {
  const response = await fetch(`${API_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  
  // DEBUG: Log the actual response to verify structure
  console.log('OpMech API Response:', data);
  
  // Verify we got an actual answer
  if (!data.answer || data.answer.trim() === '') {
    throw new Error('Empty answer received from API');
  }
  
  return data;
}
```

---

## Task 3: Add Response Validation

```typescript
// src/utils/validateResponse.ts

export function validateOpMechResponse(data: any): OpMechResponse {
  // Check required fields exist
  if (!data) {
    throw new Error('No response data');
  }
  
  if (!data.answer) {
    console.error('Response missing answer:', data);
    throw new Error('Response missing answer field');
  }
  
  if (typeof data.answer !== 'string') {
    console.error('Answer is not a string:', typeof data.answer, data.answer);
    throw new Error('Answer is not a string');
  }
  
  // Check for placeholder/template text (should NOT exist!)
  const placeholderPhrases = [
    'Based on my analysis of Apple\'s SEC filings, I can provide',
    'The dual-operator system has analyzed',
    'balanced analysis approach',
    'comprehensive answer'
  ];
  
  for (const phrase of placeholderPhrases) {
    if (data.answer.includes(phrase)) {
      console.warn('WARNING: Response may be a template/placeholder!');
      console.warn('Answer:', data.answer.substring(0, 200));
      // Don't throw, but log warning
    }
  }
  
  // Validate mode
  if (!['EXPLOIT', 'ADAPTIVE', 'EXPLORE'].includes(data.mode)) {
    console.warn('Invalid mode:', data.mode);
  }
  
  // Validate confidence
  if (typeof data.confidence !== 'number' || data.confidence < 0 || data.confidence > 1) {
    console.warn('Invalid confidence:', data.confidence);
  }
  
  return data as OpMechResponse;
}
```

---

## Task 4: Debug the Current Implementation

Add console logging to trace where the problem is:

```typescript
// Add this to your API call
const handleSubmit = async (query: string) => {
  console.log('=== QUERY DEBUG ===');
  console.log('1. User query:', query);
  
  try {
    const response = await fetch(`${API_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    
    console.log('2. Response status:', response.status);
    
    const data = await response.json();
    console.log('3. Raw API response:', JSON.stringify(data, null, 2));
    console.log('4. Answer field:', data.answer);
    console.log('5. Answer type:', typeof data.answer);
    console.log('6. Answer length:', data.answer?.length);
    
    // Check if answer is the template
    if (data.answer?.includes('dual-operator system has analyzed')) {
      console.error('ERROR: Received template response instead of actual answer!');
      console.error('This means the backend is returning a placeholder.');
    }
    
    // Use the answer
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: data.answer,  // Should be actual answer
      metadata: { mode: data.mode, confidence: data.confidence }
    }]);
    
  } catch (error) {
    console.error('Query error:', error);
  }
};
```

---

## Task 5: Check Backend Response

The problem might be in the backend, not frontend. Verify the backend returns actual answers:

```bash
# Test the backend directly
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "profits from macbook"}' | jq .
```

**Expected response:**
```json
{
  "answer": "Based on Apple's SEC filings, Mac revenue for FY2023 was $29.36 billion...",
  "mode": "ADAPTIVE",
  "confidence": 0.75,
  "metrics": { ... }
}
```

**If backend returns template, fix in backend:**
```python
# backend/api.py

@app.post("/query")
async def query(request: QueryRequest):
    result = opmech_system.query(request.query)
    
    # DEBUG: Log what we're returning
    logger.info(f"Returning answer: {result.answer[:100]}...")
    
    return {
        "answer": result.answer,  # This should be the ACTUAL answer!
        "mode": result.mode.value,
        "confidence": result.confidence,
        "metrics": result.metrics
    }
```

---

## Task 6: Fix the Message Display Component

Make sure the message component displays the actual content:

```typescript
// src/components/chat/MessageBubble.tsx

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && message.metadata && (
        <div className="mode-badge">
          <span className={`badge ${message.metadata.mode?.toLowerCase()}`}>
            {message.metadata.mode}
          </span>
          <span className="confidence">
            {(message.metadata.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}
      
      {/* THE ACTUAL CONTENT - not a template! */}
      <div className="content">
        {message.content}
      </div>
      
      {!isUser && message.metadata?.evidenceTypes && (
        <div className="evidence-sources">
          <span>Evidence Sources</span>
          <div className="tags">
            {Object.entries(message.metadata.evidenceTypes).map(([type, count]) => (
              <span key={type} className="tag">
                {type} ({count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

---

## Verification Checklist

After fixing, verify:

- [ ] Query "What was Apple's revenue in FY2023?" returns actual revenue figure ($383.29B)
- [ ] Query "profits from macbook" returns actual Mac revenue data
- [ ] Response does NOT contain "dual-operator system has analyzed"
- [ ] Response does NOT contain "balanced analysis approach"
- [ ] Mode badge shows correct mode (EXPLOIT/ADAPTIVE/EXPLORE)
- [ ] Confidence percentage matches backend
- [ ] Evidence sources show actual counts

---

## Quick Test After Fix

```typescript
// Add this test function temporarily
const testResponse = () => {
  const testQueries = [
    "What was Apple's total revenue in FY2023?",
    "profits from macbook",
    "Is Apple's margin pressure cyclical or structural?"
  ];
  
  testQueries.forEach(async (query) => {
    const response = await queryOpMech(query);
    
    console.log(`Query: ${query}`);
    console.log(`Answer: ${response.answer.substring(0, 100)}...`);
    console.log(`Mode: ${response.mode}`);
    console.log(`---`);
    
    // Verify it's not template
    if (response.answer.includes('dual-operator system')) {
      console.error(`FAILED: ${query} returned template!`);
    } else {
      console.log(`PASSED: ${query} returned actual answer`);
    }
  });
};
```

---

## Summary

| Component | Check | Fix |
|-----------|-------|-----|
| Frontend API call | Is it calling real backend? | Update API_URL |
| Response parsing | Is it extracting `response.answer`? | Use `data.answer` |
| Message display | Is it showing `message.content`? | Fix MessageBubble |
| Backend | Is it returning actual answers? | Fix answer generation |
| Placeholders | Any hardcoded templates? | Remove them |

The key fix is ensuring **`response.answer`** from the backend is actually displayed, not a hardcoded template string.
