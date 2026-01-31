// ═══════════════════════════════════════════════════════════════════════════
// OpMech-GraphRAG Type Definitions
// ═══════════════════════════════════════════════════════════════════════════

// Core Types
export type OperatorType = 'A' | 'B';
export type ModeType = 'EXPLOIT' | 'ADAPTIVE' | 'EXPLORE';
export type TrustDecision = 'TRUST_A' | 'TRUST_B' | 'MERGE_EQUAL' | 'MERGE_WEIGHTED';
export type QueryType = 'numerical' | 'causal' | 'opinion' | 'temporal' | 'descriptive';
export type NodeType = 'FINANCIAL_LINE' | 'TEXT_SECTION' | 'NOTE' | 'ENTITY';
export type AnimationState =
  | 'idle'
  | 'query_start'
  | 'operator_a_traversing'
  | 'operator_b_traversing'
  | 'convergence'
  | 'evidence_highlight'
  | 'complete';

// Graph Node
export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  position: {
    x: number;
    y: number;
    z: number;
  };
  score?: number;
  isEvidence?: boolean;
  operatorVisited?: OperatorType[];
}

// Graph Edge
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
  isBridge?: boolean;
}

// Knowledge Graph Data
export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  nodeCount: number;
  edgeCount: number;
}

// Operator Stream for visualization
export interface OperatorStream {
  operator: OperatorType;
  path: string[];
  currentNodeIndex: number;
  progress: number;
  isActive: boolean;
  color: string;
  glowColor: string;
}

// Divergence Components
export interface DivergenceComponents {
  delta_E: number; // Evidence overlap
  delta_V: number; // Structural overlap
  delta_A: number; // Answer agreement
  delta_C: number; // Confidence agreement
}

// Hop Data for trajectory with full divergence components
export interface HopData {
  hop: number;
  delta: number;
  // Per-hop divergence components (from documentation)
  delta_E?: number; // Evidence divergence
  delta_V?: number; // Structural divergence
  delta_A?: number; // Answer divergence
  delta_C?: number; // Confidence divergence
  nodesA: number;
  nodesB: number;
  bridgeSeeds: number;
}

// Evidence Node
export interface EvidenceNode {
  id: string;
  type: NodeType;
  content: string;
  score: number;
  source: OperatorType;
}

// Traversal Path
export interface TraversalPath {
  nodes: {
    id: string;
    type: NodeType;
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

// Query Metrics
export interface QueryMetrics {
  hopsUsed: number;
  finalDelta: number;
  deltaComponents: DivergenceComponents;
  trustDecision: TrustDecision;
  reliabilityA: number;
  reliabilityB: number;
  // Path confidence per operator
  pathConfidenceA: number;
  pathConfidenceB: number;
  // Financial evidence ratio
  financialRatioA: number;
  financialRatioB: number;
  // Evidence counts per operator
  evidenceCountA: number;
  evidenceCountB: number;
  queryType: QueryType;
  queryComplexity: string;
  evidenceA: EvidenceNode[];
  evidenceB: EvidenceNode[];
  trajectory: HopData[];
}

// Visualization Data
export interface VisualizationData {
  traversalA: TraversalPath;
  traversalB: TraversalPath;
  bridgeEdges: GraphEdge[];
  finalEvidenceNodes: string[];
}

// Chat Message
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    mode: ModeType;
    confidence: number;
    trustDecision: TrustDecision;
    queryType: QueryType;
    queryComplexity: string;
    hopsUsed: number;
    finalDelta: number;
    // Individual operator answers (for EXPLORE mode)
    answerA?: string;
    answerB?: string;
    // Divergence components
    deltaE: number;
    deltaV: number;
    deltaA: number;
    deltaC: number;
    // Reliability scores
    reliabilityA: number;
    reliabilityB: number;
    // Path confidence per operator
    pathConfidenceA?: number;
    pathConfidenceB?: number;
    // Financial evidence ratio (for numerical queries)
    financialRatioA?: number;
    financialRatioB?: number;
    // Evidence counts
    evidenceCountA?: number;
    evidenceCountB?: number;
    // Evidence counts per operator by type
    evidenceTypesA: {
      FINANCIAL_LINE: number;
      TEXT_SECTION: number;
      NOTE: number;
    };
    evidenceTypesB: {
      FINANCIAL_LINE: number;
      TEXT_SECTION: number;
      NOTE: number;
    };
    // Combined evidence types (backwards compatible)
    evidenceTypes: {
      FINANCIAL_LINE: number;
      TEXT_SECTION: number;
      NOTE: number;
    };
    trajectory: HopData[];
    // Reasoning string from the backend
    reasoning?: string;
  };
}

// API Request/Response Types
export interface QueryRequest {
  query: string;
  options?: {
    max_hops?: number;
    tau_low?: number;
    tau_high?: number;
  };
}

export interface QueryResponse {
  answer: string;
  // Individual operator answers (for EXPLORE mode)
  answerA: string;
  answerB: string;
  mode: ModeType;
  confidence: number;
  metrics: QueryMetrics;
  visualization: VisualizationData;
}

// WebSocket Event Types
export interface RealtimeUpdate {
  type: 'hop_start' | 'operator_progress' | 'convergence' | 'mode_selected' | 'complete';
  data: {
    hop?: number;
    operator?: OperatorType;
    nodesVisited?: number;
    delta?: number;
    mode?: ModeType;
    progress?: number;
  };
}

// Store Types
export interface QueryState {
  currentQuery: string;
  isProcessing: boolean;
  messages: ChatMessage[];
  currentResponse: QueryResponse | null;
  error: string | null;
}

export interface VisualizationState {
  graphData: KnowledgeGraphData | null;
  animationState: AnimationState;
  operatorStreams: {
    A: OperatorStream;
    B: OperatorStream;
  };
  selectedNode: GraphNode | null;
  cameraPosition: { x: number; y: number; z: number };
  zoomLevel: number;
}

export interface MetricsState {
  currentMetrics: QueryMetrics | null;
  modeAccuracy: number;
  answerQuality: number;
  trustAccuracy: number;
  queryHistory: {
    query: string;
    mode: ModeType;
    delta: number;
    timestamp: Date;
  }[];
}

// Component Props Types
export interface GraphCanvasProps {
  data: KnowledgeGraphData;
  animationState: AnimationState;
  operatorStreams: { A: OperatorStream; B: OperatorStream };
  onNodeClick?: (node: GraphNode) => void;
  onAnimationComplete?: () => void;
}

export interface CommutatorGaugeProps {
  delta: number;
  deltaComponents: DivergenceComponents;
  isAnimating: boolean;
  size?: number;
}

export interface ModeIndicatorProps {
  mode: ModeType;
  confidence: number;
  isTransitioning: boolean;
}

export interface ChatInterfaceProps {
  messages: ChatMessage[];
  isProcessing: boolean;
  onSendMessage: (message: string) => void;
  suggestedQueries?: string[];
}

// Color Scheme Configuration
export interface ColorScheme {
  primary: string;
  glow: string;
  dim: string;
  gradient: string;
}

export const OPERATOR_COLORS: Record<OperatorType, ColorScheme> = {
  A: {
    primary: '#3B82F6',
    glow: 'rgba(59, 130, 246, 0.35)',
    dim: 'rgba(59, 130, 246, 0.15)',
    gradient: 'linear-gradient(135deg, #3B82F6 0%, #60A5FA 100%)',
  },
  B: {
    primary: '#10B981',
    glow: 'rgba(16, 185, 129, 0.35)',
    dim: 'rgba(16, 185, 129, 0.15)',
    gradient: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
  },
};

export const MODE_COLORS: Record<ModeType, ColorScheme> = {
  EXPLOIT: {
    primary: '#3B82F6',
    glow: 'rgba(59, 130, 246, 0.4)',
    dim: 'rgba(59, 130, 246, 0.15)',
    gradient: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
  },
  ADAPTIVE: {
    primary: '#F59E0B',
    glow: 'rgba(245, 158, 11, 0.4)',
    dim: 'rgba(245, 158, 11, 0.15)',
    gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
  },
  EXPLORE: {
    primary: '#8B5CF6',
    glow: 'rgba(139, 92, 246, 0.4)',
    dim: 'rgba(139, 92, 246, 0.15)',
    gradient: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
  },
};

export const NODE_COLORS: Record<NodeType, string> = {
  FINANCIAL_LINE: '#3B82F6',
  TEXT_SECTION: '#10B981',
  NOTE: '#F59E0B',
  ENTITY: '#8B5CF6',
};

// Demo Queries
export const DEMO_QUERIES = [
  {
    query: "What was Apple's total revenue in FY2023?",
    expectedMode: 'EXPLOIT' as ModeType,
    description: 'Simple factual - watch XBRL data take priority',
  },
  {
    query: "Is Apple's gross margin pressure cyclical or structural?",
    expectedMode: 'EXPLORE' as ModeType,
    description: 'Opinion query - see multiple perspectives emerge',
  },
  {
    query: 'What factors drove iPhone revenue changes in FY2023?',
    expectedMode: 'ADAPTIVE' as ModeType,
    description: 'Causal analysis - balanced evidence synthesis',
  },
  {
    query: "What are Apple's main risk factors?",
    expectedMode: 'ADAPTIVE' as ModeType,
    description: 'Descriptive query - comprehensive coverage',
  },
  {
    query: 'How did R&D expenses change from FY2022 to FY2023?',
    expectedMode: 'EXPLOIT' as ModeType,
    description: 'Temporal comparison - precise figures',
  },
];
