'use client';

import { Suspense, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {
  ArrowLeft,
  Zap,
  Scale,
  Compass,
  ChevronDown,
  ChevronUp,
  Hash,
  FileText,
  StickyNote,
  GitBranch,
  Activity,
  Layers,
  Network,
  Target,
  Send,
  Sparkles,
  Info,
  Split,
} from 'lucide-react';

// Stores
import { useQueryStore } from '@/stores/queryStore';
import { useVisualizationStore } from '@/stores/visualizationStore';
import { useOpMechQuery } from '@/hooks/useOpMechQuery';

// Types
import type { ModeType, ChatMessage } from '@/types';
import { MODE_COLORS, DEMO_QUERIES } from '@/types';

// Components
import { TypingIndicator } from '@/components/shared/LoadingSpinner';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import ModeIndicator from '@/components/chat/ModeIndicator';

// Dynamic import for 3D visualization
const KnowledgeGraph3D = dynamic(
  () => import('@/components/visualization/KnowledgeGraph3D'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center bg-[#0a0a14]">
        <LoadingSpinner size="lg" variant="dual-operator" />
      </div>
    ),
  }
);

// ═══════════════════════════════════════════════════════════════════════════
// Mode Selection Button - Light Theme
// ═══════════════════════════════════════════════════════════════════════════
function ModeButton({
  mode,
  isSelected,
  onClick,
  disabled,
}: {
  mode: ModeType;
  isSelected: boolean;
  onClick: () => void;
  disabled: boolean;
}) {
  const icons = {
    EXPLOIT: Zap,
    ADAPTIVE: Scale,
    EXPLORE: Compass,
  };
  const Icon = icons[mode];
  const colors = MODE_COLORS[mode];

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      className={`relative flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all ${
        isSelected
          ? 'text-white shadow-lg'
          : 'text-[#6E6E73] hover:text-[#1D1D1F] bg-[#F5F5F7] hover:bg-[#E5E7EB]'
      } disabled:opacity-50 disabled:cursor-not-allowed`}
      style={{
        background: isSelected ? colors.gradient : undefined,
        boxShadow: isSelected ? `0 4px 14px ${colors.glow}` : undefined,
      }}
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
    >
      <Icon className="w-4 h-4" />
      <span>{mode}</span>
    </motion.button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Response Panel Component - Light Theme
// ═══════════════════════════════════════════════════════════════════════════
function ResponsePanel({ message }: { message: ChatMessage }) {
  const [isEvidenceExpanded, setIsEvidenceExpanded] = useState(true);
  const [isDivergenceExpanded, setIsDivergenceExpanded] = useState(false);
  const [isOperatorAnswersExpanded, setIsOperatorAnswersExpanded] = useState(false);
  const metadata = message.metadata;

  if (!metadata) return null;

  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Mode & Confidence Header */}
      <div className="flex items-center justify-between">
        <ModeIndicator
          mode={metadata.mode}
          confidence={metadata.confidence}
          isTransitioning={false}
          size="md"
          showDescription={false}
        />
        <div className="flex items-center gap-3">
          <span className="text-xs px-2 py-1 rounded-md bg-[#F5F5F7] text-[#6E6E73]">
            {metadata.queryType} ({metadata.queryComplexity || 'medium'})
          </span>
          <div className="text-xs text-[#6E6E73] font-mono">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Full Answer */}
      <div className="p-5 rounded-2xl bg-white border border-[#E5E7EB] shadow-sm">
        <p className="text-[#1D1D1F] leading-relaxed text-[15px] whitespace-pre-wrap">
          {message.content}
        </p>
      </div>

      {/* Individual Operator Answers */}
      {(metadata.answerA || metadata.answerB) && (
        <div className="rounded-2xl bg-[#F5F5F7] border border-[#E5E7EB] overflow-hidden">
          <button
            onClick={() => setIsOperatorAnswersExpanded(!isOperatorAnswersExpanded)}
            className="w-full flex items-center justify-between p-4 hover:bg-[#E5E7EB] transition-colors"
          >
            <div className="flex items-center gap-2">
              <Split className="w-4 h-4 text-[#6E6E73]" />
              <span className="font-medium text-[#1D1D1F]">Individual Operator Answers</span>
              {metadata.mode === 'EXPLORE' && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-[#EF4444]/10 text-[#EF4444]">
                  High Divergence
                </span>
              )}
            </div>
            {isOperatorAnswersExpanded ? (
              <ChevronUp className="w-4 h-4 text-[#6E6E73]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[#6E6E73]" />
            )}
          </button>

          <AnimatePresence>
            {isOperatorAnswersExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="p-4 pt-0 space-y-4">
                  {metadata.answerA && (
                    <div className="p-4 rounded-xl bg-[#3B82F6]/5 border border-[#3B82F6]/20">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 rounded-full bg-[#3B82F6]" />
                        <span className="text-sm font-medium text-[#3B82F6]">Operator A (Structure-First)</span>
                        {metadata.pathConfidenceA !== undefined && (
                          <span className="text-xs text-[#6E6E73] ml-auto">
                            confidence: {((metadata.pathConfidenceA || 0) * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <p className="text-[#1D1D1F] text-sm leading-relaxed whitespace-pre-wrap">
                        {metadata.answerA}
                      </p>
                    </div>
                  )}

                  {metadata.answerB && (
                    <div className="p-4 rounded-xl bg-[#10B981]/5 border border-[#10B981]/20">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 rounded-full bg-[#10B981]" />
                        <span className="text-sm font-medium text-[#10B981]">Operator B (Narrative-First)</span>
                        {metadata.pathConfidenceB !== undefined && (
                          <span className="text-xs text-[#6E6E73] ml-auto">
                            confidence: {((metadata.pathConfidenceB || 0) * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <p className="text-[#1D1D1F] text-sm leading-relaxed whitespace-pre-wrap">
                        {metadata.answerB}
                      </p>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Evidence Sources by Operator */}
      <div className="rounded-2xl bg-[#F5F5F7] border border-[#E5E7EB] overflow-hidden">
        <button
          onClick={() => setIsEvidenceExpanded(!isEvidenceExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-[#E5E7EB] transition-colors"
        >
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#6E6E73]" />
            <span className="font-medium text-[#1D1D1F]">Evidence Sources</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white text-[#6E6E73] border border-[#E5E7EB]">
              {(metadata.evidenceTypes?.FINANCIAL_LINE || 0) +
                (metadata.evidenceTypes?.TEXT_SECTION || 0) +
                (metadata.evidenceTypes?.NOTE || 0)}{' '}
              total
            </span>
          </div>
          {isEvidenceExpanded ? (
            <ChevronUp className="w-4 h-4 text-[#6E6E73]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#6E6E73]" />
          )}
        </button>

        <AnimatePresence>
          {isEvidenceExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="p-4 pt-0 space-y-4">
                {/* Operator A Evidence */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-3 h-3 rounded-full bg-[#3B82F6]" />
                    <span className="text-[#1D1D1F] font-medium">Operator A (Structure-First)</span>
                    <span className="text-xs text-[#6E6E73]">
                      reliability: {((metadata.reliabilityA || 0) * 100).toFixed(0)}%
                    </span>
                    {metadata.financialRatioA !== undefined && metadata.financialRatioA > 0 && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[#3B82F6]/10 text-[#3B82F6]">
                        {((metadata.financialRatioA || 0) * 100).toFixed(0)}% XBRL
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 pl-5">
                    <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-[#3B82F6]/20">
                      <Hash className="w-3 h-3 text-[#3B82F6]" />
                      <span className="text-xs text-[#6E6E73]">Financial</span>
                      <span className="ml-auto text-sm font-mono font-bold text-[#3B82F6]">
                        {metadata.evidenceTypesA?.FINANCIAL_LINE || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-[#10B981]/20">
                      <FileText className="w-3 h-3 text-[#10B981]" />
                      <span className="text-xs text-[#6E6E73]">Text</span>
                      <span className="ml-auto text-sm font-mono font-bold text-[#10B981]">
                        {metadata.evidenceTypesA?.TEXT_SECTION || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-[#F59E0B]/20">
                      <StickyNote className="w-3 h-3 text-[#F59E0B]" />
                      <span className="text-xs text-[#6E6E73]">Notes</span>
                      <span className="ml-auto text-sm font-mono font-bold text-[#F59E0B]">
                        {metadata.evidenceTypesA?.NOTE || 0}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Operator B Evidence */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-3 h-3 rounded-full bg-[#10B981]" />
                    <span className="text-[#1D1D1F] font-medium">Operator B (Narrative-First)</span>
                    <span className="text-xs text-[#6E6E73]">
                      reliability: {((metadata.reliabilityB || 0) * 100).toFixed(0)}%
                    </span>
                    {metadata.financialRatioB !== undefined && metadata.financialRatioB > 0 && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[#10B981]/10 text-[#10B981]">
                        {((metadata.financialRatioB || 0) * 100).toFixed(0)}% XBRL
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 pl-5">
                    <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-[#3B82F6]/20">
                      <Hash className="w-3 h-3 text-[#3B82F6]" />
                      <span className="text-xs text-[#6E6E73]">Financial</span>
                      <span className="ml-auto text-sm font-mono font-bold text-[#3B82F6]">
                        {metadata.evidenceTypesB?.FINANCIAL_LINE || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-[#10B981]/20">
                      <FileText className="w-3 h-3 text-[#10B981]" />
                      <span className="text-xs text-[#6E6E73]">Text</span>
                      <span className="ml-auto text-sm font-mono font-bold text-[#10B981]">
                        {metadata.evidenceTypesB?.TEXT_SECTION || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-[#F59E0B]/20">
                      <StickyNote className="w-3 h-3 text-[#F59E0B]" />
                      <span className="text-xs text-[#6E6E73]">Notes</span>
                      <span className="ml-auto text-sm font-mono font-bold text-[#F59E0B]">
                        {metadata.evidenceTypesB?.NOTE || 0}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="Hops Used"
          value={metadata.hopsUsed.toString()}
          icon={GitBranch}
          color="#667EEA"
        />
        <MetricCard
          label="Divergence (Δ)"
          value={metadata.finalDelta.toFixed(3)}
          icon={Activity}
          color={metadata.finalDelta < 0.3 ? '#10B981' : metadata.finalDelta < 0.6 ? '#F59E0B' : '#EF4444'}
          isHighlight
        />
        <MetricCard
          label="Trust Decision"
          value={formatTrustDecision(metadata.trustDecision)}
          icon={Target}
          color="#8B5CF6"
        />
        <MetricCard
          label="Query Type"
          value={metadata.queryType}
          icon={Info}
          color="#EC4899"
        />
      </div>

      {/* Divergence Components */}
      <div className="rounded-2xl bg-[#F5F5F7] border border-[#E5E7EB] overflow-hidden">
        <button
          onClick={() => setIsDivergenceExpanded(!isDivergenceExpanded)}
          className="w-full flex items-center justify-between p-4 hover:bg-[#E5E7EB] transition-colors"
        >
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#6E6E73]" />
            <span className="font-medium text-[#1D1D1F]">Divergence Components</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white text-[#6E6E73] border border-[#E5E7EB]">
              Δ = {metadata.finalDelta.toFixed(3)}
            </span>
          </div>
          {isDivergenceExpanded ? (
            <ChevronUp className="w-4 h-4 text-[#6E6E73]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#6E6E73]" />
          )}
        </button>

        <AnimatePresence>
          {isDivergenceExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="p-4 pt-0 grid grid-cols-2 gap-3">
                <DivergenceBar label="Δ_E (Evidence)" value={metadata.deltaE || 0} color="#3B82F6" />
                <DivergenceBar label="Δ_V (Structural)" value={metadata.deltaV || 0} color="#10B981" />
                <DivergenceBar label="Δ_A (Answer)" value={metadata.deltaA || 0} color="#F59E0B" />
                <DivergenceBar label="Δ_C (Confidence)" value={metadata.deltaC || 0} color="#8B5CF6" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Trajectory Visualization */}
      {metadata.trajectory && metadata.trajectory.length > 0 && (
        <div className="p-4 rounded-2xl bg-white border border-[#E5E7EB] shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Network className="w-4 h-4 text-[#6E6E73]" />
            <span className="font-medium text-[#1D1D1F] text-sm">Traversal Trajectory</span>
          </div>
          <div className="space-y-2">
            {metadata.trajectory.map((hop, index) => (
              <motion.div
                key={hop.hop}
                className="p-3 rounded-xl bg-[#F5F5F7] border border-[#E5E7EB]"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center text-xs font-bold text-white shrink-0">
                    {hop.hop}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-xs text-[#6E6E73] mb-1">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${hop.hop === 1 ? 'bg-[#8B5CF6]/10 text-[#8B5CF6]' : 'bg-[#F59E0B]/10 text-[#F59E0B]'}`}>
                        {hop.hop === 1 ? 'Independent' : 'Convergence'}
                      </span>
                      <span>A: {hop.nodesA}</span>
                      <span>|</span>
                      <span>B: {hop.nodesB}</span>
                      {hop.bridgeSeeds > 0 && (
                        <>
                          <span>|</span>
                          <span className="text-[#F59E0B]">Bridge: {hop.bridgeSeeds}</span>
                        </>
                      )}
                    </div>
                    <div className="h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                      <div className="flex h-full">
                        <motion.div
                          className="h-full bg-[#3B82F6]"
                          initial={{ width: 0 }}
                          animate={{ width: `${(hop.nodesA / Math.max(hop.nodesA + hop.nodesB, 1)) * 100}%` }}
                          transition={{ delay: index * 0.1 + 0.2, duration: 0.5 }}
                        />
                        <motion.div
                          className="h-full bg-[#10B981]"
                          initial={{ width: 0 }}
                          animate={{ width: `${(hop.nodesB / Math.max(hop.nodesA + hop.nodesB, 1)) * 100}%` }}
                          transition={{ delay: index * 0.1 + 0.3, duration: 0.5 }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="text-xs font-mono font-bold text-[#1D1D1F] w-16 text-right">
                    Δ={hop.delta.toFixed(3)}
                  </div>
                </div>
                {/* Per-hop divergence components */}
                <div className="mt-2 pt-2 border-t border-[#E5E7EB] grid grid-cols-4 gap-2">
                  <div className="text-center">
                    <div className="text-[10px] text-[#6E6E73]">Δ_E</div>
                    <div className="text-xs font-mono text-[#10B981]">{(hop.delta_E || 0).toFixed(2)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-[#6E6E73]">Δ_V</div>
                    <div className="text-xs font-mono text-[#3B82F6]">{(hop.delta_V || 0).toFixed(2)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-[#6E6E73]">Δ_A</div>
                    <div className="text-xs font-mono text-[#F59E0B]">{(hop.delta_A || 0).toFixed(2)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-[#6E6E73]">Δ_C</div>
                    <div className="text-xs font-mono text-[#8B5CF6]">{(hop.delta_C || 0).toFixed(2)}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-4 mt-4 pt-3 border-t border-[#E5E7EB]">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#3B82F6]" />
              <span className="text-xs text-[#6E6E73]">Operator A</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#10B981]" />
              <span className="text-xs text-[#6E6E73]">Operator B</span>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Divergence Bar Component - Light Theme
// ═══════════════════════════════════════════════════════════════════════════
function DivergenceBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-[#6E6E73]">{label}</span>
        <span className="text-xs font-mono font-bold" style={{ color }}>
          {value.toFixed(3)}
        </span>
      </div>
      <div className="h-1.5 bg-[#E5E7EB] rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(value * 100, 100)}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Metric Card Component - Light Theme
// ═══════════════════════════════════════════════════════════════════════════
function MetricCard({
  label,
  value,
  icon: Icon,
  color,
  isHighlight = false,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  color: string;
  isHighlight?: boolean;
}) {
  return (
    <motion.div
      className={`p-4 rounded-xl border transition-all ${
        isHighlight
          ? 'bg-white border-[#E5E7EB] shadow-sm'
          : 'bg-[#F5F5F7] border-[#E5E7EB]'
      }`}
      whileHover={{ scale: 1.02, borderColor: color }}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="text-xs text-[#6E6E73]">{label}</span>
      </div>
      <div
        className="text-xl font-bold font-mono"
        style={{ color: isHighlight ? color : '#1D1D1F' }}
      >
        {value}
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Stats Panel Component - Light Theme
// ═══════════════════════════════════════════════════════════════════════════
function StatsPanel() {
  const stats = [
    { label: 'Nodes', value: '1,737', icon: Layers },
    { label: 'Edges', value: '26,842', icon: Network },
    { label: 'Evidence Types', value: '4', icon: FileText },
    { label: 'Max Hops', value: '5', icon: GitBranch },
  ];

  return (
    <div className="hidden lg:flex items-center gap-3">
      {stats.map((stat, index) => (
        <motion.div
          key={stat.label}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#F5F5F7] border border-[#E5E7EB]"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <stat.icon className="w-3.5 h-3.5 text-[#6E6E73]" />
          <span className="text-xs text-[#6E6E73]">{stat.label}:</span>
          <span className="text-sm font-mono font-bold text-[#1D1D1F]">{stat.value}</span>
        </motion.div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════════════════
function formatTrustDecision(decision: string): string {
  const labels: Record<string, string> = {
    TRUST_A: 'Op A',
    TRUST_B: 'Op B',
    MERGE_EQUAL: 'Equal',
    MERGE_WEIGHTED: 'Weighted',
  };
  return labels[decision] || decision;
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Demo Page Component - Light Theme
// ═══════════════════════════════════════════════════════════════════════════
export default function DemoPage() {
  const { messages, isProcessing, currentResponse } = useQueryStore();
  const { animationState } = useVisualizationStore();
  const { sendQuery } = useOpMechQuery();

  const [inputValue, setInputValue] = useState('');
  const [selectedMode, setSelectedMode] = useState<ModeType | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isProcessing) {
      sendQuery(inputValue.trim());
      setInputValue('');
    }
  };

  const handleSuggestionClick = (query: string) => {
    setInputValue(query);
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-[#1D1D1F] overflow-hidden">
      {/* Ambient Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[800px] h-[800px] bg-[#667EEA]/5 rounded-full blur-[200px]" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-[#764BA2]/5 rounded-full blur-[200px]" />
      </div>

      {/* Top Header Bar */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-black/5">
        <div className="flex items-center justify-between px-6 h-16">
          {/* Left: Back + Logo */}
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Back</span>
            </Link>
            <div className="w-px h-6 bg-[#E5E7EB]" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center">
                <span className="text-white text-xs font-bold">OM</span>
              </div>
              <span className="font-semibold">OpMech Demo</span>
            </div>
          </div>

          {/* Center: Stats */}
          <StatsPanel />

          {/* Right: Mode Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#6E6E73] mr-2 hidden sm:inline">Mode Override:</span>
            {(['EXPLOIT', 'ADAPTIVE', 'EXPLORE'] as ModeType[]).map((mode) => (
              <ModeButton
                key={mode}
                mode={mode}
                isSelected={selectedMode === mode}
                onClick={() => setSelectedMode(selectedMode === mode ? null : mode)}
                disabled={isProcessing}
              />
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-16 h-screen flex">
        {/* Left Panel: 3D Visualization (keep dark for contrast) */}
        <div className="w-[60%] h-full relative border-r border-[#E5E7EB]">
          <Suspense
            fallback={
              <div className="w-full h-full flex items-center justify-center bg-[#0a0a14]">
                <LoadingSpinner size="lg" variant="dual-operator" />
              </div>
            }
          >
            <KnowledgeGraph3D animationState={animationState} showStats={false} />
          </Suspense>

          {/* Overlay Status Indicators */}
          <div className="absolute top-6 left-6 right-6 flex items-start justify-between pointer-events-none">
            <AnimatePresence>
              {animationState !== 'idle' && (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="px-4 py-2 rounded-full bg-black/60 backdrop-blur-xl border border-white/20 pointer-events-auto"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[#667EEA] animate-pulse" />
                    <span className="text-sm font-medium text-white">
                      {animationState.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {currentResponse && !isProcessing && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="pointer-events-auto"
              >
                <ModeIndicator
                  mode={currentResponse.mode}
                  confidence={currentResponse.confidence}
                  isTransitioning={false}
                  size="md"
                />
              </motion.div>
            )}
          </div>

          {/* Bottom Metrics Overlay */}
          <div className="absolute bottom-6 left-6 right-6 flex items-end justify-between pointer-events-none">
            {currentResponse && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="px-5 py-3 rounded-2xl bg-black/60 backdrop-blur-xl border border-white/20 pointer-events-auto"
              >
                <div className="flex items-center gap-4">
                  <div className="text-xs text-white/70">Divergence</div>
                  <div className="flex items-center gap-2">
                    <div className="w-32 h-2 bg-white/20 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{
                          backgroundColor:
                            currentResponse.metrics.finalDelta < 0.3
                              ? '#10B981'
                              : currentResponse.metrics.finalDelta < 0.6
                              ? '#F59E0B'
                              : '#EF4444',
                        }}
                        initial={{ width: 0 }}
                        animate={{
                          width: `${Math.min(currentResponse.metrics.finalDelta * 100, 100)}%`,
                        }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                      />
                    </div>
                    <span className="font-mono text-sm font-bold text-white">
                      {currentResponse.metrics.finalDelta.toFixed(3)}
                    </span>
                  </div>
                </div>
              </motion.div>
            )}

            <div className="flex items-center gap-4 px-4 py-2 rounded-xl bg-black/40 backdrop-blur-xl border border-white/10">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#3B82F6]" />
                <span className="text-xs text-white/70">Op A (Structure)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#10B981]" />
                <span className="text-xs text-white/70">Op B (Narrative)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel: Chat & Response - Light Theme */}
        <div className="w-[40%] h-full flex flex-col bg-white">
          {/* Chat Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <motion.div
                className="flex flex-col items-center justify-center h-full text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-[#667EEA]/10 to-[#764BA2]/10 border border-[#E5E7EB] flex items-center justify-center mb-6">
                  <Sparkles className="w-12 h-12 text-[#667EEA]" />
                </div>
                <h2 className="text-2xl font-bold text-[#1D1D1F] mb-3">
                  Knowledge Graph Explorer
                </h2>
                <p className="text-[#6E6E73] max-w-md mb-8 leading-relaxed">
                  Ask questions about Apple&apos;s SEC filings and watch the dual-operator
                  system traverse the knowledge graph in real-time.
                </p>

                {/* Suggested Queries */}
                <div className="w-full max-w-md space-y-2">
                  <p className="text-xs text-[#6E6E73] mb-3">Suggested queries:</p>
                  {DEMO_QUERIES.slice(0, 4).map((demo, index) => (
                    <motion.button
                      key={index}
                      onClick={() => handleSuggestionClick(demo.query)}
                      className="w-full text-left p-4 rounded-xl bg-[#F5F5F7] border border-[#E5E7EB] hover:bg-white hover:border-[#667EEA]/30 hover:shadow-md transition-all group"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      whileHover={{ scale: 1.01 }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm text-[#1D1D1F] group-hover:text-[#667EEA] transition-colors">
                            {demo.query}
                          </p>
                          <p className="text-xs text-[#6E6E73] mt-1">{demo.description}</p>
                        </div>
                        <span
                          className="text-xs px-2 py-1 rounded-md ml-3 font-medium"
                          style={{
                            backgroundColor: `${MODE_COLORS[demo.expectedMode].primary}15`,
                            color: MODE_COLORS[demo.expectedMode].primary,
                          }}
                        >
                          {demo.expectedMode}
                        </span>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <>
                {messages.map((message) => (
                  <div key={message.id}>
                    {message.role === 'user' ? (
                      <motion.div
                        className="flex justify-end"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                      >
                        <div className="max-w-[85%] px-5 py-3 rounded-2xl rounded-br-sm bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white shadow-lg">
                          {message.content}
                        </div>
                      </motion.div>
                    ) : (
                      <ResponsePanel message={message} />
                    )}
                  </div>
                ))}

                {/* Typing Indicator */}
                <AnimatePresence>
                  {isProcessing && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="flex items-start gap-3"
                    >
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#667EEA]/10 to-[#764BA2]/10 border border-[#E5E7EB] flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-[#667EEA]" />
                      </div>
                      <div className="p-4 rounded-2xl rounded-bl-sm bg-[#F5F5F7] border border-[#E5E7EB]">
                        <TypingIndicator />
                        <span className="text-xs text-[#6E6E73] mt-2 block">
                          Dual operators analyzing...
                        </span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-[#E5E7EB] bg-[#F5F5F7]">
            <form onSubmit={handleSubmit} className="relative">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about Apple's SEC filings..."
                disabled={isProcessing}
                className="w-full px-5 py-4 pr-14 rounded-xl bg-white border border-[#E5E7EB] focus:border-[#667EEA] focus:ring-2 focus:ring-[#667EEA]/20 outline-none transition-all text-[#1D1D1F] placeholder:text-[#6E6E73] disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!inputValue.trim() || isProcessing}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-lg bg-gradient-to-r from-[#667EEA] to-[#764BA2] flex items-center justify-center text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:shadow-lg hover:shadow-[#667EEA]/25"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
