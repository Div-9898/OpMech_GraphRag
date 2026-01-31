'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, ChevronUp, FileText, Hash, StickyNote } from 'lucide-react';
import type { ChatMessage, NodeType } from '@/types';
import { ModeBadge } from './ModeIndicator';
import { formatTimeAgo } from '@/utils/formatters';

interface MessageBubbleProps {
  message: ChatMessage;
  isLatest?: boolean;
}

export default function MessageBubble({ message, isLatest = false }: MessageBubbleProps) {
  const [showEvidence, setShowEvidence] = useState(isLatest);
  const isUser = message.role === 'user';

  return (
    <motion.div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className={`max-w-[85%] ${isUser ? '' : 'flex gap-3'}`}>
        {/* Assistant avatar */}
        {!isUser && (
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center flex-shrink-0">
            <span className="text-white text-sm font-bold">OM</span>
          </div>
        )}

        <div className="flex-1">
          {/* Message bubble */}
          <div
            className={`
              relative p-4 rounded-2xl
              ${
                isUser
                  ? 'bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white rounded-br-sm'
                  : 'bg-white/90 backdrop-blur-xl border border-black/5 rounded-bl-sm shadow-sm'
              }
            `}
          >
            {/* Mode badge for assistant messages */}
            {!isUser && message.metadata && (
              <div className="flex items-center gap-2 mb-3">
                <ModeBadge
                  mode={message.metadata.mode}
                  confidence={message.metadata.confidence}
                />
              </div>
            )}

            {/* Message content */}
            <p className={`text-[15px] leading-relaxed ${isUser ? 'text-white' : 'text-[#1D1D1F]'}`}>
              {message.content}
            </p>

            {/* Evidence panel for assistant messages */}
            {!isUser && message.metadata && (
              <div className="mt-4">
                {/* Toggle button */}
                <button
                  onClick={() => setShowEvidence(!showEvidence)}
                  className="flex items-center gap-2 text-sm text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
                >
                  {showEvidence ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                  <span>Evidence Sources</span>
                </button>

                {/* Evidence details */}
                {showEvidence && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-3 p-4 rounded-xl bg-black/[0.03] border border-black/5"
                  >
                    {/* Evidence by Operator */}
                    <div className="space-y-3 mb-4">
                      {/* Operator A Evidence */}
                      <div className="p-2 rounded-lg bg-[#3B82F6]/5 border border-[#3B82F6]/10">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[#3B82F6]" />
                            <span className="text-xs font-medium text-[#3B82F6]">Operator A</span>
                          </div>
                          <span className="text-xs text-[#6E6E73]">
                            {message.metadata.evidenceTypesA?.FINANCIAL_LINE || 0} fin, {message.metadata.evidenceTypesA?.TEXT_SECTION || 0} text, {message.metadata.evidenceTypesA?.NOTE || 0} notes
                          </span>
                        </div>
                      </div>

                      {/* Operator B Evidence */}
                      <div className="p-2 rounded-lg bg-[#10B981]/5 border border-[#10B981]/10">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-[#10B981]" />
                            <span className="text-xs font-medium text-[#10B981]">Operator B</span>
                          </div>
                          <span className="text-xs text-[#6E6E73]">
                            {message.metadata.evidenceTypesB?.FINANCIAL_LINE || 0} fin, {message.metadata.evidenceTypesB?.TEXT_SECTION || 0} text, {message.metadata.evidenceTypesB?.NOTE || 0} notes
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Metrics */}
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[#6E6E73]">Hops:</span>
                        <span className="font-mono text-[#1D1D1F]">
                          {message.metadata.hopsUsed}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#6E6E73]">Divergence:</span>
                        <span
                          className="font-mono"
                          style={{
                            color:
                              message.metadata.finalDelta < 0.25
                                ? '#10B981'
                                : message.metadata.finalDelta < 0.60
                                ? '#F59E0B'
                                : '#EF4444',
                          }}
                        >
                          {message.metadata.finalDelta.toFixed(3)}
                        </span>
                      </div>
                    </div>

                    {/* Divergence Components */}
                    <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-black/5">
                      <div className="text-center">
                        <div className="text-[10px] text-[#6E6E73]">Δ_E</div>
                        <div className="text-xs font-mono text-[#10B981]">{(message.metadata.deltaE || 0).toFixed(2)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[10px] text-[#6E6E73]">Δ_V</div>
                        <div className="text-xs font-mono text-[#3B82F6]">{(message.metadata.deltaV || 0).toFixed(2)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[10px] text-[#6E6E73]">Δ_A</div>
                        <div className="text-xs font-mono text-[#F59E0B]">{(message.metadata.deltaA || 0).toFixed(2)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[10px] text-[#6E6E73]">Δ_C</div>
                        <div className="text-xs font-mono text-[#8B5CF6]">{(message.metadata.deltaC || 0).toFixed(2)}</div>
                      </div>
                    </div>

                    {/* Trust decision */}
                    <div className="mt-3 pt-3 border-t border-black/5 text-sm">
                      <span className="text-[#6E6E73]">Trust: </span>
                      <span className="font-medium text-[#1D1D1F]">
                        {getTrustLabel(message.metadata.trustDecision)}
                      </span>
                    </div>
                  </motion.div>
                )}
              </div>
            )}
          </div>

          {/* Timestamp */}
          <div
            className={`mt-1 text-xs text-[#86868B] ${isUser ? 'text-right' : 'text-left'}`}
          >
            {formatTimeAgo(message.timestamp)}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// Evidence type badge component
function EvidenceTypeBadge({ type, count }: { type: NodeType; count: number }) {
  const config = {
    FINANCIAL_LINE: {
      icon: Hash,
      color: '#3B82F6',
      bg: 'bg-blue-50',
      label: 'Financial',
    },
    TEXT_SECTION: {
      icon: FileText,
      color: '#10B981',
      bg: 'bg-green-50',
      label: 'Text',
    },
    NOTE: {
      icon: StickyNote,
      color: '#F59E0B',
      bg: 'bg-amber-50',
      label: 'Note',
    },
    ENTITY: {
      icon: Hash,
      color: '#8B5CF6',
      bg: 'bg-purple-50',
      label: 'Entity',
    },
  };

  const { icon: Icon, color, bg, label } = config[type];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium ${bg}`}
      style={{ color }}
    >
      <Icon className="w-3.5 h-3.5" />
      {label} ({count})
    </span>
  );
}

// Trust decision label (from documentation: TRUST_A, TRUST_B, MERGE_EQUAL, MERGE_WEIGHTED, CONFLICT)
function getTrustLabel(decision: string): string {
  const labels: Record<string, string> = {
    TRUST_A: 'Operator A (Structure-First)',
    TRUST_B: 'Operator B (Narrative-First)',
    MERGE_EQUAL: 'Equal Merge (Both Valid)',
    MERGE_WEIGHTED: 'Weighted Merge (Reliability-Based)',
    CONFLICT: 'Conflict (Manual Review)',
  };
  return labels[decision] || decision;
}
