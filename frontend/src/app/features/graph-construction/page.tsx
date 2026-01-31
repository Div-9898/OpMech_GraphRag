'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  ArrowDown,
  Network,
  Database,
  FileText,
  Table,
  Users,
  Calendar,
  Zap,
  Layers,
  GitBranch,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';
import { useState } from 'react';

// MoE Experts - Run SEQUENTIALLY, each receives output from previous expert
// Order matters! Each expert builds on discoveries from previous experts
const moeExperts = [
  {
    id: 'entity',
    name: 'Entity Extractor',
    icon: Users,
    color: '#3B82F6',
    order: 1,
    description: 'Extracts named entities using LLM',
    specialty: 'Companies, products, people, segments, risk factors',
    receives: 'Original document nodes + embeddings',
    outputs: 'New ENTITY nodes + MENTIONS_ENTITY edges',
    edgeTypes: ['MENTIONS_ENTITY', 'ENTITY_RELATED_TO'],
    confidenceRange: '0.70 - 0.85',
  },
  {
    id: 'crossref',
    name: 'Cross-Reference Hunter',
    icon: Network,
    color: '#10B981',
    order: 2,
    description: 'Detects explicit cross-references in text',
    specialty: 'Note refs, item refs, section links, footnotes',
    receives: 'Nodes + entities from Expert 1',
    outputs: 'REFERS_TO edges linking referenced content',
    edgeTypes: ['REFERS_TO', 'EXPLAINS'],
    confidenceRange: '0.70 - 0.95',
  },
  {
    id: 'causal',
    name: 'Causal Chain Builder',
    icon: GitBranch,
    color: '#EC4899',
    order: 3,
    description: 'Identifies cause-effect relationships',
    specialty: 'Financial impacts, risk factors, revenue drivers',
    receives: 'Graph with entities + cross-references',
    outputs: 'Causal chains linking causes to effects',
    edgeTypes: ['CAUSED_BY', 'LEADS_TO'],
    confidenceRange: '0.60 - 0.80',
  },
  {
    id: 'temporal',
    name: 'Temporal Linker',
    icon: Calendar,
    color: '#F59E0B',
    order: 4,
    description: 'Links same items across time periods',
    specialty: 'XBRL tag matching, YoY comparisons',
    receives: 'Graph with causal relationships',
    outputs: 'Temporal edges connecting periods',
    edgeTypes: ['TEMPORAL_NEXT'],
    confidenceRange: '0.70 - 0.95',
  },
  {
    id: 'table_text',
    name: 'Table-Text Connector',
    icon: Table,
    color: '#8B5CF6',
    order: 5,
    description: 'Links tabular data to explanatory text',
    specialty: 'Numeric value matching, XBRL concept linking',
    receives: 'Graph with temporal relationships',
    outputs: 'Table-to-text explanation edges',
    edgeTypes: ['EXPLAINS_LINE_ITEM', 'DISCUSSES'],
    confidenceRange: '0.60 - 0.85',
  },
  {
    id: 'semantic',
    name: 'Semantic Bridge',
    icon: Zap,
    color: '#6366F1',
    order: 6,
    description: 'Creates semantic similarity edges & ensures connectivity',
    specialty: 'Similarity-based links, connectivity fallback',
    receives: 'Complete graph from all previous experts',
    outputs: 'Final enriched knowledge graph',
    edgeTypes: ['SEMANTICALLY_SIMILAR', 'BRIDGE'],
    confidenceRange: '0.70 - 1.0',
  },
];

// Graph Statistics
const graphStats = [
  { label: 'Avg Nodes per Filing', value: '2,847' },
  { label: 'Avg Edges per Filing', value: '8,234' },
  { label: 'Node Types', value: '14' },
  { label: 'Edge Types', value: '23' },
];

// Expert Card Component
function ExpertCard({
  expert,
  isActive,
  onActivate,
}: {
  expert: (typeof moeExperts)[0];
  isActive: boolean;
  onActivate: () => void;
}) {
  const Icon = expert.icon;

  return (
    <motion.button
      onClick={onActivate}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`relative p-4 rounded-xl text-left transition-all duration-300 w-full ${
        isActive
          ? 'bg-white shadow-lg ring-2'
          : 'bg-[#F5F5F7] hover:bg-white hover:shadow-md'
      }`}
      style={{
        borderColor: isActive ? expert.color : 'transparent',
        '--tw-ring-color': isActive ? expert.color : 'transparent',
      } as React.CSSProperties}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${expert.color}15` }}
        >
          <Icon className="w-5 h-5" style={{ color: expert.color }} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span
              className="px-1.5 py-0.5 text-[10px] rounded font-bold text-white"
              style={{ background: expert.color }}
            >
              {expert.order}
            </span>
            <h3 className="font-bold text-sm">{expert.name}</h3>
          </div>
          <p className="text-xs text-[#6E6E73] mt-0.5">{expert.description}</p>
        </div>
      </div>

      {isActive && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 pt-4 border-t border-[#E5E7EB]"
        >
          <div className="space-y-3">
            {/* Receives from previous */}
            <div className="bg-[#F5F5F7] rounded-lg p-2">
              <div className="text-xs font-medium text-[#6E6E73] mb-1 flex items-center gap-1">
                <ArrowRight className="w-3 h-3 rotate-180" />
                Receives
              </div>
              <div className="text-xs text-[#1D1D1F]">{expert.receives}</div>
            </div>

            <div>
              <div className="text-xs font-medium text-[#6E6E73] mb-1">
                Specialty
              </div>
              <div className="text-sm">{expert.specialty}</div>
            </div>

            <div>
              <div className="text-xs font-medium text-[#6E6E73] mb-1">
                Edge Types Created
              </div>
              <div className="flex flex-wrap gap-1">
                {expert.edgeTypes.map((edge) => (
                  <span
                    key={edge}
                    className="px-2 py-0.5 text-xs rounded-full border"
                    style={{ borderColor: expert.color, color: expert.color }}
                  >
                    {edge}
                  </span>
                ))}
              </div>
            </div>

            {/* Outputs to next */}
            <div className="bg-[#667EEA]/5 rounded-lg p-2">
              <div className="text-xs font-medium text-[#667EEA] mb-1 flex items-center gap-1">
                <ArrowRight className="w-3 h-3" />
                Outputs
              </div>
              <div className="text-xs text-[#1D1D1F]">{expert.outputs}</div>
            </div>

            <div className="text-xs text-[#6E6E73]">
              Confidence: {expert.confidenceRange}
            </div>
          </div>
        </motion.div>
      )}
    </motion.button>
  );
}

// Static pre-computed node positions to avoid any hydration issues
const STATIC_NODES = [
  { id: 0, x: 85, y: 50, size: 6 },
  { id: 1, x: 80, y: 67, size: 5 },
  { id: 2, x: 68, y: 80, size: 7 },
  { id: 3, x: 50, y: 85, size: 5 },
  { id: 4, x: 32, y: 80, size: 6 },
  { id: 5, x: 20, y: 67, size: 7 },
  { id: 6, x: 15, y: 50, size: 5 },
  { id: 7, x: 20, y: 33, size: 6 },
  { id: 8, x: 32, y: 20, size: 7 },
  { id: 9, x: 50, y: 15, size: 5 },
  { id: 10, x: 68, y: 20, size: 6 },
  { id: 11, x: 80, y: 33, size: 5 },
];

const STATIC_EDGES = [
  { from: 0, to: 3 },
  { from: 0, to: 6 },
  { from: 1, to: 4 },
  { from: 1, to: 7 },
  { from: 2, to: 5 },
  { from: 2, to: 8 },
  { from: 3, to: 9 },
  { from: 4, to: 10 },
  { from: 5, to: 11 },
  { from: 6, to: 9 },
  { from: 7, to: 10 },
  { from: 8, to: 11 },
];

// Animated Graph Visualization - uses static values to avoid hydration errors
function GraphVisualization({ activeExpert }: { activeExpert: string | null }) {
  const expert = moeExperts.find((e) => e.id === activeExpert);
  const baseColor = expert?.color || '#667EEA';

  return (
    <div className="relative w-full h-64 bg-gradient-to-br from-[#0A0A0F] to-[#1A1A2E] rounded-xl overflow-hidden">
      <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="1" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Edges */}
        {STATIC_EDGES.map((edge, idx) => (
          <motion.line
            key={idx}
            x1={STATIC_NODES[edge.from].x}
            y1={STATIC_NODES[edge.from].y}
            x2={STATIC_NODES[edge.to].x}
            y2={STATIC_NODES[edge.to].y}
            stroke={baseColor}
            strokeOpacity={0.3}
            strokeWidth={0.3}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.5, delay: idx * 0.02 }}
          />
        ))}

        {/* Nodes */}
        {STATIC_NODES.map((node, idx) => (
          <motion.circle
            key={idx}
            cx={node.x}
            cy={node.y}
            r={node.size}
            fill={baseColor}
            fillOpacity={0.8}
            filter="url(#glow)"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3, delay: idx * 0.05 }}
          />
        ))}

        {/* Center hub */}
        <motion.circle
          cx={50}
          cy={50}
          r={8}
          fill={baseColor}
          filter="url(#glow)"
          initial={{ scale: 0 }}
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      </svg>

      {/* Expert label */}
      {expert && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute bottom-4 left-4 px-3 py-1.5 rounded-lg text-white text-sm font-medium"
          style={{ background: `${expert.color}CC` }}
        >
          Expert {expert.order}: {expert.name}
        </motion.div>
      )}

      {!expert && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white/50 text-sm">Select an expert to visualize</span>
        </div>
      )}
    </div>
  );
}

// Main Page
export default function GraphConstructionPage() {
  const [activeExpert, setActiveExpert] = useState<string | null>('entity');

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
            <div className="w-16 h-16 rounded-2xl bg-[#667EEA]/10 flex items-center justify-center">
              <Network className="w-8 h-8 text-[#667EEA]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">
                Graph Construction
              </h1>
              <p className="text-xl text-[#6E6E73] mt-1">
                MoE-powered knowledge extraction
              </p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Introduction */}
      <Section className="!pt-0">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-[#667EEA]/5 to-[#764BA2]/5 rounded-2xl p-8 mb-12"
        >
          <h2 className="text-2xl font-bold mb-4">
            Mixture of Experts Architecture
          </h2>
          <p className="text-lg text-[#6E6E73] mb-6">
            OpMech uses 6 specialized experts that run <strong>sequentially</strong>.
            Each expert receives the output from the previous expert, progressively
            enriching the knowledge graph. <strong>Order matters</strong> - later experts
            build on relationships discovered by earlier ones.
          </p>

          {/* Sequential Flow Indicator */}
          <div className="bg-white/60 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-2 text-sm font-medium text-[#667EEA] mb-3">
              <Layers className="w-4 h-4" />
              Sequential Pipeline (Output → Input)
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {moeExperts.map((expert, idx) => (
                <div key={expert.id} className="flex items-center">
                  <div
                    className="px-2 py-1 rounded text-xs font-medium text-white flex items-center gap-1"
                    style={{ background: expert.color }}
                  >
                    <span className="font-bold">{expert.order}.</span>
                    <span>{expert.name.split(' ')[0]}</span>
                  </div>
                  {idx < moeExperts.length - 1 && (
                    <ArrowRight className="w-4 h-4 mx-1 text-[#6E6E73] flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-[#6E6E73] mt-3">
              Each expert receives the accumulated graph from all previous experts
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {graphStats.map((stat, idx) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + idx * 0.1 }}
                className="bg-white rounded-xl p-4 text-center"
              >
                <div className="text-2xl font-bold text-[#667EEA]">
                  {stat.value}
                </div>
                <div className="text-sm text-[#6E6E73]">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </Section>

      {/* Interactive Expert Explorer */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-4">
          The 6-Expert Sequential Pipeline
        </h2>
        <p className="text-center text-[#6E6E73] mb-8 max-w-2xl mx-auto">
          Each expert runs in strict order, receiving the enriched graph from all
          previous experts. Click on each expert to see what it receives and outputs.
        </p>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Expert List */}
          <div className="space-y-3">
            {moeExperts.map((expert, idx) => (
              <div key={expert.id} className="relative">
                <ExpertCard
                  expert={expert}
                  isActive={activeExpert === expert.id}
                  onActivate={() => setActiveExpert(expert.id)}
                />
                {idx < moeExperts.length - 1 && (
                  <div className="flex justify-center py-2">
                    <ArrowDown className="w-5 h-5 text-[#667EEA]" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Graph Visualization */}
          <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
            <GraphVisualization activeExpert={activeExpert} />

            {/* Processing Info */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl p-6"
            >
              <h3 className="font-bold mb-4 flex items-center gap-2">
                <Layers className="w-5 h-5 text-[#667EEA]" />
                Why Sequential Order Matters
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-[#3B82F6]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-[#3B82F6]">1</span>
                  </div>
                  <div>
                    <div className="font-medium">Entity Extraction First</div>
                    <div className="text-[#6E6E73]">
                      Creates ENTITY nodes that later experts can reference
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-[#10B981]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-[#10B981]">2</span>
                  </div>
                  <div>
                    <div className="font-medium">Cross-Refs Enable Causality</div>
                    <div className="text-[#6E6E73]">
                      Causal expert uses cross-reference edges to find related content
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-[#F59E0B]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-[#F59E0B]">4</span>
                  </div>
                  <div>
                    <div className="font-medium">Temporal Links Causal Chains</div>
                    <div className="text-[#6E6E73]">
                      Links causal relationships across time periods
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-[#6366F1]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-[#6366F1]">6</span>
                  </div>
                  <div>
                    <div className="font-medium">Semantic Bridge Last</div>
                    <div className="text-[#6E6E73]">
                      Fills connectivity gaps after all structured edges exist
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </Section>

      {/* Pipeline Flow */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-12">
          The Construction Pipeline
        </h2>

        <div className="max-w-4xl mx-auto">
          <div className="relative">
            {/* Connector line */}
            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#667EEA] via-[#764BA2] to-[#10B981] hidden md:block" />

            {[
              {
                icon: FileText,
                title: 'Document Parsing',
                desc: 'SEC filings (10-K, 10-Q, 8-K) are parsed into structured nodes: FINANCIAL_LINE (XBRL), TABLE_ROW, TEXT_SECTION, and NOTE nodes with metadata.',
                color: '#3B82F6',
              },
              {
                icon: Users,
                title: 'Expert 1: Entity Extraction',
                desc: 'Extracts named entities (companies, products, people, segments) using LLM. Creates ENTITY nodes and MENTIONS_ENTITY edges. These entities are available to all subsequent experts.',
                color: '#3B82F6',
              },
              {
                icon: Network,
                title: 'Expert 2-5: Sequential Edge Discovery',
                desc: 'CrossRef → Causal → Temporal → TableText. Each expert receives the enriched graph and adds its specialized edge types. Later experts leverage edges from earlier ones.',
                color: '#8B5CF6',
              },
              {
                icon: Zap,
                title: 'Expert 6: Semantic Bridge',
                desc: 'Final expert creates similarity edges and BRIDGE edges to ensure graph connectivity. Sees the complete graph with all previous expert contributions.',
                color: '#6366F1',
              },
              {
                icon: Database,
                title: 'Neo4j Storage',
                desc: 'The fully enriched graph is persisted to Neo4j with full-text indexes for efficient dual-operator traversal.',
                color: '#10B981',
              },
            ].map((step, idx) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.1 }}
                  className="relative flex items-start gap-6 mb-8 last:mb-0"
                >
                  <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0 relative z-10"
                    style={{ background: `${step.color}15` }}
                  >
                    <Icon className="w-8 h-8" style={{ color: step.color }} />
                  </div>
                  <div className="flex-1 bg-white rounded-xl p-6 shadow-sm border border-[#E5E7EB]">
                    <h3 className="font-bold text-lg mb-2">{step.title}</h3>
                    <p className="text-[#6E6E73]">{step.desc}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </Section>

      {/* Key Benefit */}
      <Section className="bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Why Sequential MoE?</h2>
          <p className="text-xl opacity-90 mb-6">
            By running experts sequentially, each one builds on discoveries from
            previous experts. The Causal Chain Builder can reference cross-reference
            edges. The Temporal Linker can connect causal chains across periods.
            The Semantic Bridge sees the complete graph for optimal connectivity.
          </p>
          <div className="flex justify-center gap-6 flex-wrap">
            <div className="text-center">
              <div className="text-4xl font-bold">94%</div>
              <div className="text-sm opacity-80">Extraction Accuracy</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold">6</div>
              <div className="text-sm opacity-80">Sequential Experts</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold">23</div>
              <div className="text-sm opacity-80">Edge Types</div>
            </div>
          </div>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/features/trust-decision"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Trust Decision
          </Link>
          <Link
            href="/architecture"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: Architecture Overview
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
