# OpMech-GraphRAG Frontend Showcase - Complete Implementation Guide

## Project Vision

Create a **groundbreaking, first-of-its-kind** frontend that showcases OpMech-GraphRAG's multi-perspective knowledge retrieval system. This should be as novel and impressive as the underlying research - a visualization experience that has never been done before for GraphRAG systems.

**Think**: Apple's product reveal aesthetics + Google's AI demos + Scientific visualization beauty

---

## Design Philosophy

### Core Aesthetic: "Elegant Intelligence"

- **Light theme** with strategic dark accents
- **Apple-inspired** clean typography and spacing
- **3D visualizations** that make complex operations beautiful
- **Smooth, purposeful animations** that explain the system
- **Premium feel** - every pixel intentional

### What Makes This Novel

No one has visualized GraphRAG like this before:
1. **Dual-operator traversal** shown as two distinct energy streams exploring a 3D graph
2. **Real-time commutator visualization** - the mathematical heart of OpMech made visual
3. **Mode selection as a physical transformation** - watch the system "shift gears"
4. **Convergence as a beautiful collision** - when operators find common ground

---

## Technical Stack

```
Framework: React 18 + TypeScript
3D Graphics: Three.js + React Three Fiber + Drei
Animations: Framer Motion + GSAP
Styling: Tailwind CSS + Custom CSS
State: Zustand (lightweight)
Backend Connection: WebSocket for real-time updates
Build: Vite
```

---

## Architecture Overview

```
src/
├── components/
│   ├── landing/
│   │   ├── HeroSection.tsx          # 3D animated hero with floating graph
│   │   ├── FeatureShowcase.tsx      # Scroll-triggered feature reveals
│   │   ├── SystemArchitecture.tsx   # Interactive architecture diagram
│   │   └── TeamSection.tsx          # Credits and team info
│   │
│   ├── chat/
│   │   ├── ChatInterface.tsx        # Main chat component
│   │   ├── MessageBubble.tsx        # Individual messages
│   │   ├── QueryInput.tsx           # Input with suggestions
│   │   ├── TypingIndicator.tsx      # Animated typing dots
│   │   └── ModeIndicator.tsx        # EXPLOIT/ADAPTIVE/EXPLORE badge
│   │
│   ├── visualization/
│   │   ├── GraphCanvas.tsx          # Main 3D graph container
│   │   ├── KnowledgeGraph3D.tsx     # The 3D node-edge visualization
│   │   ├── OperatorStream.tsx       # Animated operator traversal paths
│   │   ├── NodeCluster.tsx          # Optimized node rendering (LOD)
│   │   ├── EdgeBundle.tsx           # Edge bundling for 27k edges
│   │   ├── CommutatorGauge.tsx      # Real-time divergence visualization
│   │   ├── ConvergenceEffect.tsx    # Particle effect when operators meet
│   │   └── EvidenceHighlight.tsx    # Highlight found evidence nodes
│   │
│   ├── metrics/
│   │   ├── MetricsDashboard.tsx     # Live performance metrics
│   │   ├── DivergenceChart.tsx      # Δ over hops visualization
│   │   ├── EvidenceBreakdown.tsx    # Pie chart of evidence types
│   │   ├── ConfidenceMeter.tsx      # Animated confidence gauge
│   │   └── TraversalStats.tsx       # Nodes/edges visited counter
│   │
│   └── shared/
│       ├── GlassCard.tsx            # Frosted glass effect cards
│       ├── AnimatedNumber.tsx       # Counting number animation
│       ├── GradientText.tsx         # Animated gradient text
│       ├── ParticleBackground.tsx   # Subtle particle system
│       └── LoadingSpinner.tsx       # Custom loading animation
│
├── hooks/
│   ├── useOpMechQuery.ts            # Backend query hook
│   ├── useGraphVisualization.ts     # Graph state management
│   ├── useRealtimeUpdates.ts        # WebSocket connection
│   └── useScrollAnimation.ts        # Scroll-based animations
│
├── stores/
│   ├── queryStore.ts                # Query state
│   ├── visualizationStore.ts        # Graph visualization state
│   └── metricsStore.ts              # Metrics state
│
├── utils/
│   ├── graphLayout.ts               # Force-directed layout algorithms
│   ├── nodeOptimization.ts          # LOD and clustering for 1700 nodes
│   ├── colorSchemes.ts              # Node type color mappings
│   └── formatters.ts                # Number/text formatters
│
└── styles/
    ├── globals.css                  # Global styles
    └── animations.css               # Keyframe animations
```

---

## Page Structure

### Page 1: Landing / Hero

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NAV: [Logo] OpMech-GraphRAG          [Features] [Demo] [Architecture]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                    ╭─────────────────────────────╮                      │
│                    │                             │                      │
│                    │   3D KNOWLEDGE GRAPH        │                      │
│                    │   Slowly rotating           │                      │
│                    │   Nodes pulsing gently      │                      │
│                    │   Two operator streams      │                      │
│                    │   exploring paths           │                      │
│                    │                             │                      │
│                    ╰─────────────────────────────╯                      │
│                                                                         │
│              OpMech-GraphRAG                                            │
│              ─────────────────                                          │
│              Multi-Perspective Knowledge Retrieval                      │
│              Through Quantum-Inspired Operator Mechanics                │
│                                                                         │
│              "When two perspectives converge, truth emerges"            │
│                                                                         │
│                      [ Try Live Demo ↓ ]                                │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  SCROLL INDICATOR: Animated chevron                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 2: Feature Showcase (Scroll-Triggered)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  FEATURE 1: DUAL OPERATOR ARCHITECTURE                                  │
│  ┌────────────────────────────┐  ┌────────────────────────────┐        │
│  │  OPERATOR A               │  │  OPERATOR B               │         │
│  │  ════════════             │  │  ════════════             │         │
│  │  Structure-First          │  │  Narrative-First          │         │
│  │                           │  │                           │         │
│  │  🔷 XBRL Financial Data   │  │  🟢 MD&A Narratives       │         │
│  │  🔷 Hierarchical Links    │  │  🟢 Semantic Connections  │         │
│  │  🔷 Quantitative Focus    │  │  🟢 Qualitative Context   │         │
│  │                           │  │                           │         │
│  │  [3D mini visualization]  │  │  [3D mini visualization]  │         │
│  └────────────────────────────┘  └────────────────────────────┘        │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  FEATURE 2: THE COMMUTATOR                                              │
│                                                                         │
│         [A, B] = AB - BA ≠ 0                                           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                                                              │      │
│  │   Divergence Components (animated bars)                      │      │
│  │                                                              │      │
│  │   Δ_E (Evidence)    ████████████░░░░░░  0.63                │      │
│  │   Δ_V (Structure)   █████████░░░░░░░░░  0.57                │      │
│  │   Δ_A (Answer)      ██░░░░░░░░░░░░░░░░  0.03                │      │
│  │   Δ_C (Confidence)  ███░░░░░░░░░░░░░░░  0.11                │      │
│  │   ─────────────────────────────────────                      │      │
│  │   Combined Δ        ████████░░░░░░░░░░  0.34                │      │
│  │                                                              │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  FEATURE 3: INTELLIGENT MODE SELECTION                                  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   EXPLOIT    │  │   ADAPTIVE   │  │   EXPLORE    │                  │
│  │   ════════   │  │   ════════   │  │   ════════   │                  │
│  │              │  │              │  │              │                  │
│  │   ⚡ 89%     │  │   ⚖️ 75%     │  │   🔍 45%     │                  │
│  │   Direct     │  │   Balanced   │  │   Multiple   │                  │
│  │   Answer     │  │   Analysis   │  │   Perspectives│                 │
│  │              │  │              │  │              │                  │
│  │  "We know"   │  │  "Consider"  │  │  "Explore"   │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 3: Live Demo (Main Feature)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     LIVE VISUALIZATION                          │   │
│  │                                                                 │   │
│  │         ╭───────────────────────────────────────╮               │   │
│  │         │                                       │               │   │
│  │         │      3D KNOWLEDGE GRAPH               │               │   │
│  │         │      1,737 nodes • 26,842 edges       │               │   │
│  │         │                                       │               │   │
│  │         │   🔵 Operator A Path                  │               │   │
│  │         │   🟢 Operator B Path                  │               │   │
│  │         │   ⭐ Evidence Nodes (glowing)         │               │   │
│  │         │   🔗 Bridge Connections               │               │   │
│  │         │                                       │               │   │
│  │         │      [Interactive - drag to rotate]   │               │   │
│  │         │                                       │               │   │
│  │         ╰───────────────────────────────────────╯               │   │
│  │                                                                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │   │
│  │  │ HOP: 2/4    │ │ Δ: 0.335    │ │ MODE:EXPLOIT│ │ CONF: 89% │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        CHAT INTERFACE                           │   │
│  │                                                                 │   │
│  │  ┌───────────────────────────────────────────────────────────┐ │   │
│  │  │                                                           │ │   │
│  │  │  USER                                                     │ │   │
│  │  │  What was Apple's total revenue in FY2023?                │ │   │
│  │  │                                                           │ │   │
│  │  │  ─────────────────────────────────────────────────────── │ │   │
│  │  │                                                           │ │   │
│  │  │  OPMECH                           [EXPLOIT] [89%]         │ │   │
│  │  │                                                           │ │   │
│  │  │  Apple's total revenue for fiscal year 2023 is            │ │   │
│  │  │  $383.29 billion, as reported in the audited              │ │   │
│  │  │  financial statements (XBRL data).                        │ │   │
│  │  │                                                           │ │   │
│  │  │  ┌─────────────────────────────────────────────────────┐ │ │   │
│  │  │  │ Evidence Sources                                    │ │ │   │
│  │  │  │ 🔷 FINANCIAL_LINE (8) • 📝 NOTE (3) • 📄 TEXT (2)  │ │ │   │
│  │  │  │ Trust: Operator A (XBRL authority)                  │ │ │   │
│  │  │  └─────────────────────────────────────────────────────┘ │ │   │
│  │  │                                                           │ │   │
│  │  └───────────────────────────────────────────────────────────┘ │   │
│  │                                                                 │   │
│  │  ┌───────────────────────────────────────────────────────────┐ │   │
│  │  │  Ask about Apple's SEC filings...                    [➤] │ │   │
│  │  └───────────────────────────────────────────────────────────┘ │   │
│  │                                                                 │   │
│  │  Suggested: [Revenue trends] [Risk factors] [R&D expenses]     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 4: System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                      SYSTEM ARCHITECTURE                                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                 │   │
│  │                         ┌─────────┐                             │   │
│  │                         │  QUERY  │                             │   │
│  │                         └────┬────┘                             │   │
│  │                              │                                  │   │
│  │                    ┌─────────▼─────────┐                        │   │
│  │                    │ QUERY CLASSIFIER  │                        │   │
│  │                    │ numerical/causal/ │                        │   │
│  │                    │ opinion/temporal  │                        │   │
│  │                    └─────────┬─────────┘                        │   │
│  │                              │                                  │   │
│  │              ┌───────────────┴───────────────┐                  │   │
│  │              │                               │                  │   │
│  │      ┌───────▼───────┐             ┌────────▼────────┐         │   │
│  │      │  OPERATOR A   │             │   OPERATOR B    │         │   │
│  │      │  Structure    │             │   Narrative     │         │   │
│  │      │  First        │◄───────────►│   First         │         │   │
│  │      └───────┬───────┘  Bridge     └────────┬────────┘         │   │
│  │              │          Seeds               │                  │   │
│  │              └───────────────┬───────────────┘                  │   │
│  │                              │                                  │   │
│  │                    ┌─────────▼─────────┐                        │   │
│  │                    │    COMMUTATOR     │                        │   │
│  │                    │    [A,B] = Δ      │                        │   │
│  │                    └─────────┬─────────┘                        │   │
│  │                              │                                  │   │
│  │                    ┌─────────▼─────────┐                        │   │
│  │                    │  MODE SELECTOR    │                        │   │
│  │                    │  + TRUST DECISION │                        │   │
│  │                    └─────────┬─────────┘                        │   │
│  │                              │                                  │   │
│  │              ┌───────────────┼───────────────┐                  │   │
│  │              │               │               │                  │   │
│  │      ┌───────▼──────┐ ┌─────▼─────┐ ┌──────▼───────┐           │   │
│  │      │   EXPLOIT    │ │ ADAPTIVE  │ │   EXPLORE    │           │   │
│  │      │   Direct     │ │ Balanced  │ │   Multiple   │           │   │
│  │      │   Answer     │ │ View      │ │   Views      │           │   │
│  │      └──────────────┘ └───────────┘ └──────────────┘           │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 5: Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                      PERFORMANCE METRICS                                │
│                                                                         │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐        │
│  │                  │ │                  │ │                  │        │
│  │   MODE ACCURACY  │ │  ANSWER QUALITY  │ │   TRUST ACCURACY │        │
│  │                  │ │                  │ │                  │        │
│  │      100%        │ │      100%        │ │      100%        │        │
│  │   ████████████   │ │   ████████████   │ │   ████████████   │        │
│  │                  │ │                  │ │                  │        │
│  │   3/3 correct    │ │   3/3 correct    │ │   3/3 correct    │        │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   DIVERGENCE OVER HOPS                          │   │
│  │                                                                 │   │
│  │  0.8 ┤                                                          │   │
│  │      │  ●                                                       │   │
│  │  0.6 ┤   ╲                                                      │   │
│  │      │    ╲                                                     │   │
│  │  0.4 ┤     ╲____●                                               │   │
│  │      │          Convergence                                     │   │
│  │  0.2 ┤                                                          │   │
│  │      │                                                          │   │
│  │  0.0 ┼────┬────┬────┬────┬────                                  │   │
│  │      Hop1 Hop2 Hop3 Hop4 Hop5                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────────────────┐  ┌────────────────────────┐                │
│  │  EVIDENCE DISTRIBUTION │  │  TRAVERSAL EFFICIENCY  │                │
│  │                        │  │                        │                │
│  │     FINANCIAL_LINE     │  │   Before: 1,134 nodes  │                │
│  │        ████████ 62%    │  │   After:    76 nodes   │                │
│  │                        │  │                        │                │
│  │     TEXT_SECTION       │  │   Reduction: 93%       │                │
│  │        ███ 23%         │  │                        │                │
│  │                        │  │   No edge caps hit ✓   │                │
│  │     NOTE               │  │   Smart scoring ✓      │                │
│  │        ██ 15%          │  │                        │                │
│  └────────────────────────┘  └────────────────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 6: Team & Credits

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                           TEAM                                          │
│                                                                         │
│      OpMech-GraphRAG: Multi-Perspective Knowledge Retrieval             │
│      Through Quantum-Inspired Operator Mechanics                        │
│                                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │              │ │              │ │              │ │              │   │
│  │   Divyansh   │ │   Dhruvish   │ │   Dharmik    │ │   Agastya    │   │
│  │   Maiwar     │ │   Shah       │ │   Kothari    │ │   Shetty     │   │
│  │   Singh      │ │              │ │              │ │              │   │
│  │              │ │              │ │              │ │              │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
│                                                                         │
│                    SP Jain School of Global Management                  │
│                    Master's in AI in Business                           │
│                                                                         │
│  ───────────────────────────────────────────────────────────────────── │
│                                                                         │
│                         RESEARCH HIGHLIGHTS                             │
│                                                                         │
│  • First commutator-based divergence measurement for GraphRAG          │
│  • Novel dual-operator architecture for multi-perspective retrieval    │
│  • Intelligent mode selection (EXPLOIT/ADAPTIVE/EXPLORE)               │
│  • Query-aware trust decisions for numerical accuracy                   │
│  • 93% traversal reduction through smart edge scoring                  │
│                                                                         │
│                                                     [ View Paper → ]    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Specifications

### 1. Hero Section 3D Graph

```typescript
// KnowledgeGraph3D.tsx - The hero visualization

interface GraphConfig {
  nodeCount: 1737;
  edgeCount: 26842;
  
  // Level of Detail (LOD) for performance
  lod: {
    high: { distance: 0-100, showAllNodes: true, showLabels: true },
    medium: { distance: 100-300, showClusters: true, showLabels: false },
    low: { distance: 300+, showSuperClusters: true }
  };
  
  // Node types with colors
  nodeTypes: {
    FINANCIAL_LINE: { color: '#3B82F6', size: 1.0, glow: true },
    TEXT_SECTION: { color: '#10B981', size: 0.8, glow: false },
    NOTE: { color: '#F59E0B', size: 0.7, glow: false },
    ENTITY: { color: '#8B5CF6', size: 0.6, glow: false }
  };
  
  // Edge bundling for 27k edges
  edgeBundling: {
    enabled: true,
    strength: 0.85,
    maxEdgesRendered: 5000  // Bundle rest
  };
}

// Animation states
type AnimationState = 
  | 'idle'           // Slow rotation, gentle pulse
  | 'query_start'    // Zoom to seed nodes
  | 'operator_a_traversing'  // Blue stream exploring
  | 'operator_b_traversing'  // Green stream exploring
  | 'convergence'    // Operators meet, particle burst
  | 'evidence_highlight'  // Glow found evidence
  | 'complete';      // Final state with answer
```

### 2. Operator Traversal Visualization

```typescript
// OperatorStream.tsx - Animated operator paths

interface OperatorStreamProps {
  operator: 'A' | 'B';
  color: string;  // A: blue, B: green
  path: NodeId[];
  isActive: boolean;
  progress: number;  // 0-1
}

// Visual representation:
// - Glowing particle stream following the path
// - Trail effect that fades
// - Pulse at current node
// - Different particle density based on edge score

const operatorStyles = {
  A: {
    primaryColor: '#3B82F6',
    glowColor: '#60A5FA',
    particleCount: 50,
    streamWidth: 3,
    label: 'Structure-First'
  },
  B: {
    primaryColor: '#10B981',
    glowColor: '#34D399',
    particleCount: 50,
    streamWidth: 3,
    label: 'Narrative-First'
  }
};
```

### 3. Commutator Gauge

```typescript
// CommutatorGauge.tsx - Real-time divergence visualization

interface CommutatorGaugeProps {
  delta: number;        // Combined divergence 0-1
  delta_E: number;      // Evidence overlap
  delta_V: number;      // Structural overlap
  delta_A: number;      // Answer agreement
  delta_C: number;      // Confidence agreement
  isAnimating: boolean;
}

// Visual design:
// - Circular gauge with animated fill
// - Color gradient: green (low Δ) → yellow → red (high Δ)
// - Inner breakdown bars for components
// - Pulse effect when value changes
// - Number counts up/down smoothly

const gaugeConfig = {
  size: 200,
  strokeWidth: 12,
  colors: {
    low: '#10B981',    // < 0.3
    medium: '#F59E0B', // 0.3-0.6
    high: '#EF4444'    // > 0.6
  },
  animation: {
    duration: 500,
    easing: 'easeOutCubic'
  }
};
```

### 4. Mode Indicator

```typescript
// ModeIndicator.tsx - EXPLOIT/ADAPTIVE/EXPLORE badge

interface ModeIndicatorProps {
  mode: 'EXPLOIT' | 'ADAPTIVE' | 'EXPLORE';
  confidence: number;
  isTransitioning: boolean;
}

const modeStyles = {
  EXPLOIT: {
    icon: '⚡',
    color: '#3B82F6',
    gradient: 'from-blue-500 to-blue-600',
    label: 'High Confidence',
    description: 'Direct answer from authoritative source'
  },
  ADAPTIVE: {
    icon: '⚖️',
    color: '#F59E0B',
    gradient: 'from-amber-500 to-orange-500',
    label: 'Balanced View',
    description: 'Nuanced analysis with context'
  },
  EXPLORE: {
    icon: '🔍',
    color: '#8B5CF6',
    gradient: 'from-purple-500 to-violet-600',
    label: 'Multiple Perspectives',
    description: 'Exploring different viewpoints'
  }
};

// Animation: Card flips/morphs when mode changes
```

### 5. Chat Interface

```typescript
// ChatInterface.tsx

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  
  // OpMech-specific metadata
  metadata?: {
    mode: 'EXPLOIT' | 'ADAPTIVE' | 'EXPLORE';
    confidence: number;
    trustDecision: 'TRUST_A' | 'TRUST_B' | 'MERGE_EQUAL' | 'MERGE_WEIGHTED';
    queryType: string;
    hopsUsed: number;
    finalDelta: number;
    evidenceTypes: {
      FINANCIAL_LINE: number;
      TEXT_SECTION: number;
      NOTE: number;
    };
    trajectory: {
      hop: number;
      delta: number;
    }[];
  };
}

// Design features:
// - Glass morphism message bubbles
// - Expandable evidence section
// - Inline mode badge
// - Animated typing indicator with operator status
// - Smooth scroll to new messages
```

---

## Animation Sequences

### Query Processing Animation

```
1. USER TYPES QUERY
   └─► Input glow effect
   └─► Suggestions fade out

2. QUERY SUBMITTED
   └─► Message appears with slide-up
   └─► Graph zooms to relevant region
   └─► "Processing..." indicator appears

3. OPERATOR A STARTS
   └─► Blue particles spawn at seed nodes
   └─► Stream flows along traversal path
   └─► Visited nodes pulse blue
   └─► Counter: "Operator A: 6 → 83 nodes"

4. OPERATOR B STARTS (slightly delayed)
   └─► Green particles spawn
   └─► Stream flows along different path
   └─► Visited nodes pulse green
   └─► Counter: "Operator B: 6 → 98 nodes"

5. CONVERGENCE PRESSURE
   └─► Bridge edges glow gold
   └─► Particles transfer between operators
   └─► "Sharing bridge seeds..." text

6. COMMUTATOR CALCULATION
   └─► Gauge animates from 0.6 to 0.34
   └─► Components bars fill
   └─► "Divergence: 0.606 → 0.335"

7. MODE SELECTION
   └─► Mode badge transforms
   └─► Color scheme shifts
   └─► "EXPLOIT" appears with confidence

8. EVIDENCE HIGHLIGHT
   └─► Final evidence nodes glow bright
   └─► Lines connect to answer
   └─► Trust decision indicator

9. ANSWER APPEARS
   └─► Typing animation
   └─► Evidence panel expands
   └─► Graph settles to final state
```

---

## Color System

```css
:root {
  /* Primary - Apple-inspired */
  --color-bg: #FAFAFA;
  --color-bg-elevated: #FFFFFF;
  --color-text-primary: #1D1D1F;
  --color-text-secondary: #6E6E73;
  --color-text-tertiary: #86868B;
  
  /* Accent Colors */
  --color-blue: #007AFF;
  --color-green: #34C759;
  --color-orange: #FF9500;
  --color-purple: #AF52DE;
  --color-red: #FF3B30;
  
  /* Operator Colors */
  --color-operator-a: #3B82F6;
  --color-operator-a-glow: rgba(59, 130, 246, 0.3);
  --color-operator-b: #10B981;
  --color-operator-b-glow: rgba(16, 185, 129, 0.3);
  
  /* Mode Colors */
  --color-exploit: #3B82F6;
  --color-adaptive: #F59E0B;
  --color-explore: #8B5CF6;
  
  /* Node Type Colors */
  --color-financial-line: #3B82F6;
  --color-text-section: #10B981;
  --color-note: #F59E0B;
  --color-entity: #8B5CF6;
  
  /* Glass Effect */
  --glass-bg: rgba(255, 255, 255, 0.72);
  --glass-border: rgba(255, 255, 255, 0.18);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  
  /* Gradients */
  --gradient-hero: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-mesh: radial-gradient(at 40% 20%, hsla(212, 93%, 67%, 0.1) 0px, transparent 50%),
                   radial-gradient(at 80% 0%, hsla(189, 100%, 56%, 0.1) 0px, transparent 50%),
                   radial-gradient(at 0% 50%, hsla(355, 100%, 93%, 0.1) 0px, transparent 50%);
}
```

---

## Typography

```css
/* Font Stack */
font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 
             'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;

/* Type Scale */
--text-hero: 72px / 1.05 / -0.015em;    /* Main headlines */
--text-h1: 48px / 1.1 / -0.01em;         /* Section titles */
--text-h2: 32px / 1.2 / -0.005em;        /* Subsections */
--text-h3: 24px / 1.3 / 0;               /* Card titles */
--text-body: 17px / 1.5 / 0;             /* Body text */
--text-caption: 14px / 1.4 / 0;          /* Captions */
--text-code: 14px / 1.5 / 0;             /* Code/mono */

/* Font Weights */
--font-light: 300;
--font-regular: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

---

## Backend API Integration

```typescript
// api/opmech.ts

interface QueryRequest {
  query: string;
  options?: {
    max_hops?: number;
    tau_low?: number;
    tau_high?: number;
  };
}

interface QueryResponse {
  answer: string;
  mode: 'EXPLOIT' | 'ADAPTIVE' | 'EXPLORE';
  confidence: number;
  
  // Detailed metrics
  metrics: {
    hops_used: number;
    final_delta: number;
    delta_components: {
      delta_E: number;
      delta_V: number;
      delta_A: number;
      delta_C: number;
    };
    
    // Trust decision
    trust_decision: 'TRUST_A' | 'TRUST_B' | 'MERGE_EQUAL' | 'MERGE_WEIGHTED';
    reliability_A: number;
    reliability_B: number;
    
    // Query classification
    query_type: string;
    query_complexity: string;
    
    // Evidence
    evidence_A: EvidenceNode[];
    evidence_B: EvidenceNode[];
    
    // Trajectory
    trajectory: HopData[];
  };
  
  // For visualization
  visualization: {
    traversal_A: TraversalPath;
    traversal_B: TraversalPath;
    bridge_edges: Edge[];
    final_evidence_nodes: string[];
  };
}

interface TraversalPath {
  nodes: {
    id: string;
    type: string;
    timestamp: number;
    score: number;
  }[];
  edges: {
    source: string;
    target: string;
    type: string;
    score: number;
  }[];
}

// WebSocket for real-time updates during query processing
interface RealtimeUpdate {
  type: 'hop_start' | 'operator_progress' | 'convergence' | 'mode_selected' | 'complete';
  data: any;
}
```

---

## Performance Optimizations for 1700 Nodes / 27k Edges

### 1. Level of Detail (LOD)

```typescript
// nodeOptimization.ts

class GraphLOD {
  // Cluster nearby nodes when zoomed out
  createClusters(nodes: Node[], zoomLevel: number): ClusterNode[] {
    if (zoomLevel > 0.7) return nodes; // Show all
    
    // Use k-means or DBSCAN to cluster
    const k = Math.max(50, Math.floor(nodes.length * zoomLevel));
    return kMeansClustering(nodes, k);
  }
  
  // Only render visible nodes
  frustumCulling(nodes: Node[], camera: Camera): Node[] {
    const frustum = new THREE.Frustum();
    frustum.setFromProjectionMatrix(camera.projectionMatrix);
    return nodes.filter(n => frustum.containsPoint(n.position));
  }
}
```

### 2. Edge Bundling

```typescript
// edgeBundling.ts

class EdgeBundler {
  // Bundle edges that share similar paths
  bundle(edges: Edge[]): BundledEdge[] {
    // Use force-directed edge bundling
    // Reduces 27k edges to ~3k bundled curves
    
    const controlPoints = this.computeControlPoints(edges);
    return edges.map(e => ({
      ...e,
      curve: new THREE.CatmullRomCurve3(controlPoints[e.id])
    }));
  }
  
  // Progressive loading
  loadInChunks(edges: Edge[], chunkSize = 1000): AsyncGenerator<Edge[]> {
    // Load edges in batches to prevent frame drops
  }
}
```

### 3. Instanced Rendering

```typescript
// NodeInstances.tsx

// Use THREE.InstancedMesh for nodes
const NodeInstances = ({ nodes, nodeTypes }) => {
  const meshRef = useRef<THREE.InstancedMesh>();
  
  // One draw call for all nodes of same type
  useFrame(() => {
    nodes.forEach((node, i) => {
      dummy.position.copy(node.position);
      dummy.scale.setScalar(node.size);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });
  
  return (
    <instancedMesh ref={meshRef} args={[null, null, nodes.length]}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshStandardMaterial />
    </instancedMesh>
  );
};
```

### 4. GPU-Based Layout

```typescript
// gpuLayout.ts

// Use GPU compute for force-directed layout
class GPUForceLayout {
  private computeShader: THREE.ComputeShader;
  
  // Calculate node positions on GPU
  compute(nodes: Float32Array, edges: Uint32Array): Float32Array {
    // Much faster than CPU for 1700 nodes
  }
}
```

---

## Suggested Queries for Demo

```typescript
const DEMO_QUERIES = [
  {
    query: "What was Apple's total revenue in FY2023?",
    expectedMode: 'EXPLOIT',
    description: 'Simple factual - watch XBRL data take priority'
  },
  {
    query: "Is Apple's gross margin pressure cyclical or structural?",
    expectedMode: 'EXPLORE',
    description: 'Opinion query - see multiple perspectives emerge'
  },
  {
    query: "What factors drove iPhone revenue changes in FY2023?",
    expectedMode: 'ADAPTIVE',
    description: 'Causal analysis - balanced evidence synthesis'
  },
  {
    query: "What are Apple's main risk factors?",
    expectedMode: 'ADAPTIVE',
    description: 'Descriptive query - comprehensive coverage'
  },
  {
    query: "How did R&D expenses change from FY2022 to FY2023?",
    expectedMode: 'EXPLOIT',
    description: 'Temporal comparison - precise figures'
  }
];
```

---

## Project Setup

```bash
# Create project
npm create vite@latest opmech-frontend -- --template react-ts

# Install dependencies
cd opmech-frontend
npm install three @react-three/fiber @react-three/drei
npm install framer-motion gsap
npm install zustand
npm install tailwindcss postcss autoprefixer
npm install @heroicons/react lucide-react
npm install recharts  # For charts
npm install socket.io-client  # For WebSocket

# Initialize Tailwind
npx tailwindcss init -p

# Directory structure
mkdir -p src/{components,hooks,stores,utils,styles}
mkdir -p src/components/{landing,chat,visualization,metrics,shared}
```

---

## Deployment Considerations

```yaml
# For Vercel/Netlify
build:
  command: npm run build
  output: dist

# Environment variables
VITE_API_URL=http://localhost:8000  # OpMech backend
VITE_WS_URL=ws://localhost:8000/ws  # WebSocket endpoint

# Performance budget
- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Time to Interactive: < 3.5s
- 3D Scene Load: < 2s
```

---

## Success Criteria

After implementation, the frontend should:

1. **Wow Factor**: First-time visitors say "I've never seen GraphRAG visualized like this"
2. **Educational**: Users understand how dual-operator traversal works
3. **Functional**: Real queries work with real-time visualization
4. **Performance**: Smooth 60fps even with 1700 nodes
5. **Professional**: Publication/demo-ready quality
6. **Novel**: Truly unique - no existing GraphRAG UI looks like this

---

## Timeline Estimate

| Phase | Tasks | Time |
|-------|-------|------|
| 1 | Project setup, basic layout, routing | 2-3 hours |
| 2 | 3D graph visualization (core) | 4-6 hours |
| 3 | Operator traversal animation | 3-4 hours |
| 4 | Chat interface | 2-3 hours |
| 5 | Metrics dashboard | 2-3 hours |
| 6 | Landing page & animations | 3-4 hours |
| 7 | Backend integration | 2-3 hours |
| 8 | Polish & optimization | 3-4 hours |
| **Total** | | **21-30 hours** |

---

## Final Notes

This frontend will be a **showcase piece** that demonstrates not just the functionality of OpMech-GraphRAG, but the elegance of its design. The visualization of dual operators converging through a knowledge graph has never been done with this level of polish.

Key differentiators:
- Real-time 3D traversal visualization
- Commutator made visual
- Mode selection as a physical transformation
- Trust decisions explained visually
- Evidence sources highlighted in the graph

Good luck! This will be impressive. 🚀
