import { create } from 'zustand';
import type {
  KnowledgeGraphData,
  AnimationState,
  OperatorStream,
  GraphNode,
} from '@/types';

interface VisualizationState {
  graphData: KnowledgeGraphData | null;
  animationState: AnimationState;
  operatorStreams: {
    A: OperatorStream;
    B: OperatorStream;
  };
  selectedNode: GraphNode | null;
  cameraPosition: { x: number; y: number; z: number };
  zoomLevel: number;
  isGraphLoaded: boolean;

  // Actions
  setGraphData: (data: KnowledgeGraphData) => void;
  setAnimationState: (state: AnimationState) => void;
  updateOperatorStream: (operator: 'A' | 'B', updates: Partial<OperatorStream>) => void;
  setSelectedNode: (node: GraphNode | null) => void;
  setCameraPosition: (position: { x: number; y: number; z: number }) => void;
  setZoomLevel: (level: number) => void;
  setIsGraphLoaded: (loaded: boolean) => void;
  resetVisualization: () => void;
  startQueryAnimation: (pathA: string[], pathB: string[]) => void;
}

const initialOperatorStream = (operator: 'A' | 'B'): OperatorStream => ({
  operator,
  path: [],
  currentNodeIndex: 0,
  progress: 0,
  isActive: false,
  color: operator === 'A' ? '#3B82F6' : '#10B981',
  glowColor: operator === 'A' ? 'rgba(59, 130, 246, 0.35)' : 'rgba(16, 185, 129, 0.35)',
});

export const useVisualizationStore = create<VisualizationState>((set) => ({
  graphData: null,
  animationState: 'idle',
  operatorStreams: {
    A: initialOperatorStream('A'),
    B: initialOperatorStream('B'),
  },
  selectedNode: null,
  cameraPosition: { x: 0, y: 0, z: 150 },
  zoomLevel: 1,
  isGraphLoaded: false,

  setGraphData: (data) => set({ graphData: data, isGraphLoaded: true }),

  setAnimationState: (state) => set({ animationState: state }),

  updateOperatorStream: (operator, updates) =>
    set((state) => ({
      operatorStreams: {
        ...state.operatorStreams,
        [operator]: { ...state.operatorStreams[operator], ...updates },
      },
    })),

  setSelectedNode: (node) => set({ selectedNode: node }),

  setCameraPosition: (position) => set({ cameraPosition: position }),

  setZoomLevel: (level) => set({ zoomLevel: level }),

  setIsGraphLoaded: (loaded) => set({ isGraphLoaded: loaded }),

  resetVisualization: () =>
    set({
      animationState: 'idle',
      operatorStreams: {
        A: initialOperatorStream('A'),
        B: initialOperatorStream('B'),
      },
      selectedNode: null,
    }),

  startQueryAnimation: (pathA, pathB) =>
    set({
      animationState: 'query_start',
      operatorStreams: {
        A: {
          ...initialOperatorStream('A'),
          path: pathA,
          isActive: true,
        },
        B: {
          ...initialOperatorStream('B'),
          path: pathB,
          isActive: true,
        },
      },
    }),
}));
