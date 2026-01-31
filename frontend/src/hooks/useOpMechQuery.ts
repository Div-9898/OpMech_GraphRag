'use client';

import { useState, useCallback } from 'react';
import { useQueryStore } from '@/stores/queryStore';
import { useVisualizationStore } from '@/stores/visualizationStore';
import { useMetricsStore } from '@/stores/metricsStore';
import type { ChatMessage, QueryResponse, ModeType, TrustDecision, QueryType } from '@/types';
import { generateId } from '@/utils/formatters';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Type for the raw API response from OpMech backend
interface OpMechAPIResponse {
  answer: string;
  mode: ModeType;
  confidence: number;
  // Individual operator answers (from documentation)
  answer_A?: string;
  answer_B?: string;
  reasoning?: string;
  metrics?: {
    hops_used?: number;
    final_delta?: number;
    delta_E?: number;
    delta_V?: number;
    delta_A?: number;
    delta_C?: number;
    trust_decision?: string;
    reliability_A?: number;
    reliability_B?: number;
    // Path confidence per operator
    path_confidence_A?: number;
    path_confidence_B?: number;
    // Financial evidence ratio
    financial_ratio_A?: number;
    financial_ratio_B?: number;
    query_type?: string;
    query_complexity?: string;
    // Evidence counts
    evidence_count_A?: number;
    evidence_count_B?: number;
    trajectory?: Array<{
      hop: number;
      delta: number;
      // Per-hop divergence components
      delta_E?: number;
      delta_V?: number;
      delta_A?: number;
      delta_C?: number;
      nodesA?: number;
      nodesB?: number;
      nodes_A?: number;  // Backend sends snake_case
      nodes_B?: number;
      bridge_seeds?: number;
    }>;
  };
  evidence?: {
    evidence_A?: Array<{ type: string; content: string; score?: number }>;
    evidence_B?: Array<{ type: string; content: string; score?: number }>;
  };
  visualization?: {
    traversal_A?: { nodes: string[]; edges: string[] };
    traversal_B?: { nodes: string[]; edges: string[] };
    bridge_edges?: string[];
    final_evidence_nodes?: string[];
  };
}

// Transform API response to internal format
function transformAPIResponse(apiResponse: OpMechAPIResponse): QueryResponse {
  const metrics = apiResponse.metrics || {};
  const evidence = apiResponse.evidence || {};

  // Count evidence by type
  const evidenceA = evidence.evidence_A || [];
  const evidenceB = evidence.evidence_B || [];
  const allEvidence = [...evidenceA, ...evidenceB];

  const evidenceCounts = {
    FINANCIAL_LINE: allEvidence.filter(e => e.type === 'FINANCIAL_LINE' || e.type === 'financial').length,
    TEXT_SECTION: allEvidence.filter(e => e.type === 'TEXT_SECTION' || e.type === 'text').length,
    NOTE: allEvidence.filter(e => e.type === 'NOTE' || e.type === 'note').length,
  };

  // Build trajectory from API data with full divergence components
  const trajectory = metrics.trajectory?.map(t => ({
    hop: t.hop,
    delta: t.delta,
    // Per-hop divergence components (from documentation)
    delta_E: t.delta_E || 0,
    delta_V: t.delta_V || 0,
    delta_A: t.delta_A || 0,
    delta_C: t.delta_C || 0,
    nodesA: t.nodesA || t.nodes_A || 0,
    nodesB: t.nodesB || t.nodes_B || 0,
    bridgeSeeds: t.bridge_seeds || 0,
  })) || [];

  return {
    answer: apiResponse.answer,
    mode: apiResponse.mode,
    confidence: apiResponse.confidence,
    // Individual operator answers
    answerA: apiResponse.answer_A || '',
    answerB: apiResponse.answer_B || '',
    metrics: {
      hopsUsed: metrics.hops_used || 0,
      finalDelta: metrics.final_delta || 0,
      deltaComponents: {
        delta_E: metrics.delta_E || 0,
        delta_V: metrics.delta_V || 0,
        delta_A: metrics.delta_A || 0,
        delta_C: metrics.delta_C || 0,
      },
      trustDecision: (metrics.trust_decision as TrustDecision) || 'MERGE_WEIGHTED',
      reliabilityA: metrics.reliability_A || 0,
      reliabilityB: metrics.reliability_B || 0,
      // Path confidence per operator
      pathConfidenceA: metrics.path_confidence_A || 0,
      pathConfidenceB: metrics.path_confidence_B || 0,
      // Financial evidence ratio
      financialRatioA: metrics.financial_ratio_A || 0,
      financialRatioB: metrics.financial_ratio_B || 0,
      queryType: (metrics.query_type as QueryType) || 'descriptive',
      queryComplexity: metrics.query_complexity || 'medium',
      // Evidence counts
      evidenceCountA: metrics.evidence_count_A || evidenceA.length,
      evidenceCountB: metrics.evidence_count_B || evidenceB.length,
      evidenceA: evidenceA.map((e, i) => ({
        id: `evidence-a-${i}`,
        type: e.type as 'FINANCIAL_LINE' | 'TEXT_SECTION' | 'NOTE' | 'ENTITY',
        content: e.content,
        score: e.score || 0,
        source: 'A' as const,
      })),
      evidenceB: evidenceB.map((e, i) => ({
        id: `evidence-b-${i}`,
        type: e.type as 'FINANCIAL_LINE' | 'TEXT_SECTION' | 'NOTE' | 'ENTITY',
        content: e.content,
        score: e.score || 0,
        source: 'B' as const,
      })),
      trajectory,
    },
    visualization: {
      traversalA: { nodes: [], edges: [] },
      traversalB: { nodes: [], edges: [] },
      bridgeEdges: [],
      finalEvidenceNodes: apiResponse.visualization?.final_evidence_nodes || [],
    },
  };
}

export function useOpMechQuery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    addMessage,
    setIsProcessing,
    setCurrentResponse,
    setError: setStoreError,
  } = useQueryStore();

  const { setAnimationState } = useVisualizationStore();
  const { setCurrentMetrics, addToHistory } = useMetricsStore();

  const sendQuery = useCallback(
    async (query: string) => {
      if (!query.trim()) return;

      setIsLoading(true);
      setError(null);
      setIsProcessing(true);
      setAnimationState('query_start');

      // Add user message
      const userMessage: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: query,
        timestamp: new Date(),
      };
      addMessage(userMessage);

      try {
        // Start operator animation
        setAnimationState('operator_a_traversing');

        // Make real API call to OpMech backend
        console.log('Sending query to OpMech API:', query);

        const response = await fetch(`${API_URL}/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`API error (${response.status}): ${errorText}`);
        }

        setAnimationState('operator_b_traversing');

        const apiData: OpMechAPIResponse = await response.json();

        // Debug: Log the raw API response
        console.log('OpMech API Response:', apiData);

        // Validate the response has an actual answer
        if (!apiData.answer || apiData.answer.trim() === '') {
          throw new Error('Empty answer received from API');
        }

        setAnimationState('convergence');

        // Transform API response to internal format
        const data = transformAPIResponse(apiData);

        setCurrentResponse(data);
        setCurrentMetrics(data.metrics);

        // Add to history
        addToHistory({
          query,
          mode: data.mode,
          delta: data.metrics.finalDelta,
          confidence: data.confidence,
          timestamp: new Date(),
        });

        // Count evidence types per operator
        const evidenceTypesA = {
          FINANCIAL_LINE: data.metrics.evidenceA.filter(e => e.type === 'FINANCIAL_LINE').length,
          TEXT_SECTION: data.metrics.evidenceA.filter(e => e.type === 'TEXT_SECTION').length,
          NOTE: data.metrics.evidenceA.filter(e => e.type === 'NOTE').length,
        };
        const evidenceTypesB = {
          FINANCIAL_LINE: data.metrics.evidenceB.filter(e => e.type === 'FINANCIAL_LINE').length,
          TEXT_SECTION: data.metrics.evidenceB.filter(e => e.type === 'TEXT_SECTION').length,
          NOTE: data.metrics.evidenceB.filter(e => e.type === 'NOTE').length,
        };
        const evidenceCounts = {
          FINANCIAL_LINE: evidenceTypesA.FINANCIAL_LINE + evidenceTypesB.FINANCIAL_LINE,
          TEXT_SECTION: evidenceTypesA.TEXT_SECTION + evidenceTypesB.TEXT_SECTION,
          NOTE: evidenceTypesA.NOTE + evidenceTypesB.NOTE,
        };

        // Add assistant message with the REAL answer from the API
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: data.answer, // THE ACTUAL ANSWER FROM THE API
          timestamp: new Date(),
          metadata: {
            mode: data.mode,
            confidence: data.confidence,
            trustDecision: data.metrics.trustDecision,
            queryType: data.metrics.queryType,
            queryComplexity: data.metrics.queryComplexity,
            hopsUsed: data.metrics.hopsUsed,
            finalDelta: data.metrics.finalDelta,
            // Individual operator answers (for EXPLORE mode)
            answerA: data.answerA,
            answerB: data.answerB,
            // Divergence components
            deltaE: data.metrics.deltaComponents.delta_E,
            deltaV: data.metrics.deltaComponents.delta_V,
            deltaA: data.metrics.deltaComponents.delta_A,
            deltaC: data.metrics.deltaComponents.delta_C,
            // Reliability scores
            reliabilityA: data.metrics.reliabilityA,
            reliabilityB: data.metrics.reliabilityB,
            // Path confidence per operator
            pathConfidenceA: data.metrics.pathConfidenceA,
            pathConfidenceB: data.metrics.pathConfidenceB,
            // Financial evidence ratio
            financialRatioA: data.metrics.financialRatioA,
            financialRatioB: data.metrics.financialRatioB,
            // Evidence counts
            evidenceCountA: data.metrics.evidenceCountA,
            evidenceCountB: data.metrics.evidenceCountB,
            // Evidence per operator by type
            evidenceTypesA,
            evidenceTypesB,
            // Combined (backwards compatible)
            evidenceTypes: evidenceCounts,
            trajectory: data.metrics.trajectory,
          },
        };
        addMessage(assistantMessage);

        setAnimationState('complete');
      } catch (err) {
        console.error('OpMech query error:', err);
        const errorMessage = err instanceof Error ? err.message : 'An error occurred';
        setError(errorMessage);
        setStoreError(errorMessage);

        // Add error message to chat
        const errorChatMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: `Error: ${errorMessage}. Please ensure the OpMech backend is running at ${API_URL}.`,
          timestamp: new Date(),
        };
        addMessage(errorChatMessage);

        setAnimationState('idle');
      } finally {
        setIsLoading(false);
        setIsProcessing(false);
        setTimeout(() => setAnimationState('idle'), 2000);
      }
    },
    [
      addMessage,
      setIsProcessing,
      setCurrentResponse,
      setStoreError,
      setAnimationState,
      setCurrentMetrics,
      addToHistory,
    ]
  );

  return {
    sendQuery,
    isLoading,
    error,
  };
}
