'use client';

import { Suspense } from 'react';
import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';

// Stores
import { useQueryStore } from '@/stores/queryStore';
import { useVisualizationStore } from '@/stores/visualizationStore';
import { useOpMechQuery } from '@/hooks/useOpMechQuery';

// Components
import ChatInterface from '@/components/chat/ChatInterface';
import ModeIndicator from '@/components/chat/ModeIndicator';
import { CommutatorGaugeCompact } from '@/components/visualization/CommutatorGauge';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import GlassCard from '@/components/shared/GlassCard';

// Dynamic import for 3D visualization
const KnowledgeGraph3D = dynamic(
  () => import('@/components/visualization/KnowledgeGraph3D'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14] rounded-2xl">
        <LoadingSpinner size="lg" variant="dual-operator" />
      </div>
    ),
  }
);

export default function DemoSection() {
  const { messages, isProcessing, currentResponse } = useQueryStore();
  const { animationState } = useVisualizationStore();
  const { sendQuery } = useOpMechQuery();

  return (
    <section className="py-24 bg-[#FAFAFA]">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-[#1D1D1F] mb-4">
            Live Demo
          </h2>
          <p className="text-xl text-[#6E6E73] max-w-2xl mx-auto">
            Watch dual operators explore the knowledge graph in real-time as you ask
            questions about Apple&apos;s SEC filings.
          </p>
        </motion.div>

        {/* Demo interface */}
        <div className="grid lg:grid-cols-5 gap-6">
          {/* 3D Visualization - takes 3 columns */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="lg:col-span-3"
          >
            <div className="relative h-[500px] lg:h-[600px] rounded-2xl overflow-hidden shadow-2xl border border-white/10">
              {/* 3D Graph Canvas */}
              <Suspense
                fallback={
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
                    <LoadingSpinner size="lg" variant="dual-operator" />
                  </div>
                }
              >
                <KnowledgeGraph3D
                  animationState={animationState}
                  showStats={true}
                />
              </Suspense>

              {/* Status overlay - top */}
              <div className="absolute top-4 left-4 right-4 flex flex-wrap gap-2 z-20 pointer-events-none">
                {/* Mode indicator */}
                {currentResponse && (
                  <div className="pointer-events-auto">
                    <ModeIndicator
                      mode={currentResponse.mode}
                      confidence={currentResponse.confidence}
                      isTransitioning={isProcessing}
                      size="sm"
                      showDescription={false}
                    />
                  </div>
                )}

                {/* Divergence */}
                {currentResponse && (
                  <div className="px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-sm border border-black/5 pointer-events-auto">
                    <CommutatorGaugeCompact delta={currentResponse.metrics.finalDelta} />
                  </div>
                )}

                {/* Processing indicator */}
                {isProcessing && (
                  <div className="px-3 py-1.5 rounded-full bg-[#667EEA]/10 border border-[#667EEA]/20 flex items-center gap-2 pointer-events-auto">
                    <div className="w-2 h-2 rounded-full bg-[#667EEA] animate-pulse" />
                    <span className="text-xs font-medium text-[#667EEA]">
                      Processing...
                    </span>
                  </div>
                )}
              </div>

              {/* Metrics overlay - bottom left (above the stats from graph) */}
              {currentResponse && (
                <div className="absolute bottom-20 left-4 flex flex-wrap gap-2 z-20 pointer-events-none">
                  <StatPill
                    label="Hops"
                    value={currentResponse.metrics.hopsUsed.toString()}
                  />
                  <StatPill
                    label="Trust"
                    value={formatTrustDecision(currentResponse.metrics.trustDecision)}
                  />
                </div>
              )}
            </div>
          </motion.div>

          {/* Chat Interface - takes 2 columns */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="lg:col-span-2"
          >
            <GlassCard hover={false} className="h-[500px] lg:h-[600px] overflow-hidden">
              <ChatInterface
                messages={messages}
                isProcessing={isProcessing}
                onSendMessage={sendQuery}
              />
            </GlassCard>
          </motion.div>
        </div>

        {/* Quick stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          <QuickStat label="Knowledge Nodes" value="1,737" />
          <QuickStat label="Graph Edges" value="26,842" />
          <QuickStat label="Evidence Types" value="4" />
          <QuickStat label="Max Hops" value="5" />
        </motion.div>
      </div>
    </section>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-sm border border-black/5">
      <span className="text-xs text-[#6E6E73]">{label}: </span>
      <span className="text-xs font-semibold text-[#1D1D1F]">{value}</span>
    </div>
  );
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center p-4 rounded-xl bg-white/60 border border-black/5">
      <div className="text-2xl font-bold text-[#1D1D1F]">{value}</div>
      <div className="text-sm text-[#6E6E73]">{label}</div>
    </div>
  );
}

function formatTrustDecision(decision: string): string {
  const labels: Record<string, string> = {
    TRUST_A: 'Op A',
    TRUST_B: 'Op B',
    MERGE_EQUAL: 'Equal',
    MERGE_WEIGHTED: 'Weighted',
  };
  return labels[decision] || decision;
}
