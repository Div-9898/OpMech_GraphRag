import { create } from 'zustand';
import type { ChatMessage, QueryResponse } from '@/types';

interface QueryState {
  currentQuery: string;
  isProcessing: boolean;
  messages: ChatMessage[];
  currentResponse: QueryResponse | null;
  error: string | null;

  // Actions
  setCurrentQuery: (query: string) => void;
  setIsProcessing: (processing: boolean) => void;
  addMessage: (message: ChatMessage) => void;
  setCurrentResponse: (response: QueryResponse | null) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  reset: () => void;
}

export const useQueryStore = create<QueryState>((set) => ({
  currentQuery: '',
  isProcessing: false,
  messages: [],
  currentResponse: null,
  error: null,

  setCurrentQuery: (query) => set({ currentQuery: query }),

  setIsProcessing: (processing) => set({ isProcessing: processing }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setCurrentResponse: (response) => set({ currentResponse: response }),

  setError: (error) => set({ error }),

  clearMessages: () => set({ messages: [] }),

  reset: () =>
    set({
      currentQuery: '',
      isProcessing: false,
      messages: [],
      currentResponse: null,
      error: null,
    }),
}));
