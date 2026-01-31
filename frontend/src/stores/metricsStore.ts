import { create } from 'zustand';
import type { QueryMetrics, ModeType, DivergenceComponents } from '@/types';

interface QueryHistoryItem {
  query: string;
  mode: ModeType;
  delta: number;
  confidence: number;
  timestamp: Date;
}

interface MetricsState {
  currentMetrics: QueryMetrics | null;
  modeAccuracy: number;
  answerQuality: number;
  trustAccuracy: number;
  queryHistory: QueryHistoryItem[];
  totalQueries: number;
  averageDelta: number;
  averageConfidence: number;

  // Actions
  setCurrentMetrics: (metrics: QueryMetrics) => void;
  addToHistory: (item: QueryHistoryItem) => void;
  updateAccuracies: (mode: number, answer: number, trust: number) => void;
  clearHistory: () => void;
  reset: () => void;
}

export const useMetricsStore = create<MetricsState>((set, get) => ({
  currentMetrics: null,
  modeAccuracy: 100,
  answerQuality: 100,
  trustAccuracy: 100,
  queryHistory: [],
  totalQueries: 0,
  averageDelta: 0,
  averageConfidence: 0,

  setCurrentMetrics: (metrics) => set({ currentMetrics: metrics }),

  addToHistory: (item) =>
    set((state) => {
      const newHistory = [...state.queryHistory, item];
      const totalQueries = newHistory.length;
      const averageDelta =
        newHistory.reduce((sum, i) => sum + i.delta, 0) / totalQueries;
      const averageConfidence =
        newHistory.reduce((sum, i) => sum + i.confidence, 0) / totalQueries;

      return {
        queryHistory: newHistory,
        totalQueries,
        averageDelta,
        averageConfidence,
      };
    }),

  updateAccuracies: (mode, answer, trust) =>
    set({
      modeAccuracy: mode,
      answerQuality: answer,
      trustAccuracy: trust,
    }),

  clearHistory: () =>
    set({
      queryHistory: [],
      totalQueries: 0,
      averageDelta: 0,
      averageConfidence: 0,
    }),

  reset: () =>
    set({
      currentMetrics: null,
      modeAccuracy: 100,
      answerQuality: 100,
      trustAccuracy: 100,
      queryHistory: [],
      totalQueries: 0,
      averageDelta: 0,
      averageConfidence: 0,
    }),
}));
