'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  Shield,
  Database,
  Table,
  FileText,
  StickyNote,
  User,
  Check,
  X,
  HelpCircle,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// Evidence Hierarchy Pyramid
// ═══════════════════════════════════════════════════════════════════════════

const evidenceHierarchy = [
  { type: 'XBRL', authority: 100, color: '#3B82F6', icon: Database, desc: 'Audited, machine-readable' },
  { type: 'Financial Tables', authority: 90, color: '#6366F1', icon: Table, desc: 'Structured data' },
  { type: 'Text Sections', authority: 40, color: '#8B5CF6', icon: FileText, desc: 'May lack context' },
  { type: 'Notes', authority: 30, color: '#A855F7', icon: StickyNote, desc: 'Explanatory' },
  { type: 'Entities', authority: 20, color: '#D946EF', icon: User, desc: 'Need context' },
];

// ═══════════════════════════════════════════════════════════════════════════
// Trust Decision Rules
// ═══════════════════════════════════════════════════════════════════════════

const trustRules = [
  {
    queryType: 'Numerical (A wins)',
    icon: Database,
    color: '#3B82F6',
    rule: 'TRUST_A if Operator A has > 55% FINANCIAL_LINE evidence',
    example: {
      operatorA: { financialLine: 8, total: 13 },
      operatorB: { financialLine: 5, total: 13 },
      decision: 'TRUST_A',
      reason: '8/13 = 62% → Trust Operator A (Structure-First)',
    },
  },
  {
    queryType: 'Numerical (B wins)',
    icon: FileText,
    color: '#10B981',
    rule: 'TRUST_B if Operator B has > 55% FINANCIAL_LINE evidence',
    example: {
      operatorA: { financialLine: 4, total: 12 },
      operatorB: { financialLine: 9, total: 12 },
      decision: 'TRUST_B',
      reason: '9/12 = 75% → Trust Operator B (Narrative-First)',
    },
  },
  {
    queryType: 'Opinion',
    icon: HelpCircle,
    color: '#8B5CF6',
    rule: 'MERGE_EQUAL - Combine both perspectives equally',
    example: {
      reason: 'No single "right" answer exists, so present both views with equal weight',
    },
  },
  {
    queryType: 'Causal',
    icon: Shield,
    color: '#F59E0B',
    rule: 'MERGE_WEIGHTED - Weight by reliability score',
    example: {
      reason: 'Balance quantitative data with qualitative context based on operator reliability',
    },
  },
  {
    queryType: 'High Divergence',
    icon: X,
    color: '#EF4444',
    rule: 'CONFLICT - When δ > 0.6 and answers contradict',
    example: {
      reason: 'Operators found fundamentally different evidence - present both viewpoints separately for user consideration',
    },
  },
];

// ═══════════════════════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════════════════════

export default function TrustDecisionPage() {
  return (
    <PageWrapper>
      {/* Header */}
      <Section className="pt-24 pb-8">
        <Link
          href="/features"
          className="inline-flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Features
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-2xl bg-[#10B981]/10 flex items-center justify-center">
              <Shield className="w-8 h-8 text-[#10B981]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">Trust & Evidence Scoring</h1>
              <p className="text-xl text-[#6E6E73] mt-1">Knowing which source to believe</p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* The Challenge */}
      <Section className="!pt-0">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-[#10B981]/5 to-[#3B82F6]/5 rounded-2xl p-8 mb-12"
        >
          <h2 className="text-2xl font-bold mb-4">The Challenge</h2>
          <p className="text-lg text-[#6E6E73] mb-6">
            When operators find different evidence, which do we trust?
          </p>

          <div className="bg-white rounded-xl p-6">
            <div className="grid md:grid-cols-2 gap-6">
              <div className="p-4 bg-[#3B82F6]/5 rounded-lg border-l-4 border-[#3B82F6]">
                <div className="font-semibold mb-1">Operator A says:</div>
                <div className="text-[#3B82F6] font-mono">&ldquo;$383.29 billion&rdquo;</div>
                <div className="text-sm text-[#6E6E73] mt-1">(from XBRL)</div>
              </div>
              <div className="p-4 bg-[#10B981]/5 rounded-lg border-l-4 border-[#10B981]">
                <div className="font-semibold mb-1">Operator B says:</div>
                <div className="text-[#10B981] font-mono">&ldquo;$394.33 billion&rdquo;</div>
                <div className="text-sm text-[#6E6E73] mt-1">(from narrative text)</div>
              </div>
            </div>
            <div className="text-center mt-6 text-2xl">
              Which is correct? 🤔
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Evidence Authority Hierarchy */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-12">Evidence Authority Hierarchy</h2>

        <div className="max-w-2xl mx-auto">
          <div className="relative">
            {evidenceHierarchy.map((item, idx) => {
              const Icon = item.icon;
              const width = 100 - idx * 15;

              return (
                <motion.div
                  key={item.type}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.1 }}
                  className="relative mb-3"
                  style={{ marginLeft: `${idx * 7.5}%`, marginRight: `${idx * 7.5}%` }}
                >
                  <div
                    className="p-4 rounded-xl text-white relative overflow-hidden"
                    style={{ background: item.color }}
                  >
                    <div className="flex items-center justify-between relative z-10">
                      <div className="flex items-center gap-3">
                        <Icon className="w-5 h-5" />
                        <div>
                          <div className="font-bold">{item.type}</div>
                          <div className="text-sm opacity-80">{item.desc}</div>
                        </div>
                      </div>
                      <div className="text-2xl font-bold">{item.authority}%</div>
                    </div>

                    {idx === 0 && (
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs bg-white/20 px-2 py-1 rounded">
                        Highest authority
                      </div>
                    )}
                    {idx === evidenceHierarchy.length - 1 && (
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs bg-white/20 px-2 py-1 rounded">
                        Lowest authority
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </Section>

      {/* Trust Decision Logic */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-12">Trust Decision Logic</h2>

        <div className="max-w-4xl mx-auto space-y-6">
          {trustRules.map((rule, idx) => {
            const Icon = rule.icon;

            return (
              <motion.div
                key={rule.queryType}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                className="bg-white rounded-2xl p-6 shadow-sm border border-[#E5E7EB]"
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `${rule.color}15` }}
                  >
                    <Icon className="w-6 h-6" style={{ color: rule.color }} />
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-lg">For {rule.queryType.toUpperCase()} queries:</h3>
                    </div>

                    <div className="bg-[#F5F5F7] rounded-lg p-4 mb-4 font-mono text-sm">
                      {rule.rule}
                    </div>

                    {'operatorA' in rule.example && rule.example.operatorA && rule.example.operatorB && (
                      <div className="grid md:grid-cols-3 gap-4 text-sm">
                        <div className="p-3 bg-[#3B82F6]/5 rounded-lg">
                          <div className="font-medium text-[#3B82F6] mb-1">Operator A:</div>
                          <div>{rule.example.operatorA.financialLine} FINANCIAL_LINE nodes</div>
                        </div>
                        <div className="p-3 bg-[#10B981]/5 rounded-lg">
                          <div className="font-medium text-[#10B981] mb-1">Operator B:</div>
                          <div>{rule.example.operatorB.financialLine} FINANCIAL_LINE nodes</div>
                        </div>
                        <div className="p-3 bg-[#F59E0B]/5 rounded-lg">
                          <div className="font-medium text-[#F59E0B] mb-1">Decision:</div>
                          <div className="flex items-center gap-1">
                            <Check className="w-4 h-4 text-[#10B981]" />
                            {rule.example.reason}
                          </div>
                        </div>
                      </div>
                    )}

                    {'reason' in rule.example && !('operatorA' in rule.example) && (
                      <p className="text-[#6E6E73]">{rule.example.reason}</p>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Section>

      {/* Key Insight */}
      <Section className="bg-gradient-to-r from-[#10B981] to-[#3B82F6] text-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Key Insight</h2>
          <p className="text-xl opacity-90 mb-6">
            The trust decision isn&apos;t just about picking a winner—it&apos;s about understanding
            what type of answer the query requires and which evidence best serves that need.
          </p>
          <div className="flex justify-center gap-3 flex-wrap">
            <div className="px-4 py-2 bg-white/20 rounded-full text-sm">
              Numerical → TRUST_A or TRUST_B (55% threshold)
            </div>
            <div className="px-4 py-2 bg-white/20 rounded-full text-sm">
              Opinion → MERGE_EQUAL
            </div>
            <div className="px-4 py-2 bg-white/20 rounded-full text-sm">
              Causal → MERGE_WEIGHTED
            </div>
            <div className="px-4 py-2 bg-white/20 rounded-full text-sm">
              High Δ → CONFLICT
            </div>
          </div>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/features/mode-selection"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Mode Selection
          </Link>
          <Link
            href="/features/graph-construction"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: Graph Construction
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
