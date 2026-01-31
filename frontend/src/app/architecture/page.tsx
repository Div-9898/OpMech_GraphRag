'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Database,
  Server,
  Globe,
  Cpu,
  Layers,
  GitBranch,
  Shield,
  Zap,
  ArrowRight,
  Box,
  Binary,
  Network,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';
import { useState } from 'react';

// Architecture Layers
const architectureLayers = [
  {
    id: 'frontend',
    name: 'Presentation Layer',
    icon: Globe,
    color: '#3B82F6',
    tech: ['Next.js 16', 'React 19', 'Three.js', 'Framer Motion'],
    description: 'Interactive UI with 3D graph visualization and real-time updates',
    components: [
      '3D Knowledge Graph Viewer',
      'Query Interface',
      'Evidence Browser',
      'Metrics Dashboard',
    ],
  },
  {
    id: 'api',
    name: 'API Layer',
    icon: Server,
    color: '#8B5CF6',
    tech: ['FastAPI', 'Pydantic', 'WebSockets'],
    description: 'RESTful API with streaming responses and WebSocket support',
    components: [
      '/query - Main query endpoint',
      '/graph - Graph traversal',
      '/metrics - Performance metrics',
      '/health - System health checks',
    ],
  },
  {
    id: 'orchestration',
    name: 'Orchestration Layer',
    icon: Cpu,
    color: '#EC4899',
    tech: ['OpMech Core', 'Commutator', 'Mode Selector'],
    description: 'Dual-operator system with divergence-based mode selection',
    components: [
      'Operator A (Structure-First)',
      'Operator B (Narrative-First)',
      'Commutator (Divergence)',
      'Trust Decision Engine',
    ],
  },
  {
    id: 'rag',
    name: 'RAG Engine',
    icon: Network,
    color: '#F59E0B',
    tech: ['GraphRAG', 'Neo4j Cypher', 'Vector Search'],
    description: 'Graph-augmented retrieval with multi-hop reasoning',
    components: [
      'Subgraph Extraction',
      'Evidence Collection',
      'Context Ranking',
      'Prompt Assembly',
    ],
  },
  {
    id: 'llm',
    name: 'LLM Layer',
    icon: Binary,
    color: '#10B981',
    tech: ['vLLM', 'Qwen2.5-7B', 'OpenAI API'],
    description: 'High-performance inference with configurable model backends',
    components: [
      'Query Classification',
      'Response Generation',
      'Evidence Synthesis',
      'Multi-turn Context',
    ],
  },
  {
    id: 'storage',
    name: 'Storage Layer',
    icon: Database,
    color: '#EF4444',
    tech: ['Neo4j 5.15', 'APOC', 'Full-text Indexes'],
    description: 'Graph database optimized for financial document knowledge',
    components: [
      'Knowledge Graph',
      'Vector Embeddings',
      'Document Store',
      'Query Cache',
    ],
  },
];

// Data Flow Steps
const dataFlowSteps = [
  { label: 'User Query', icon: Globe, color: '#3B82F6' },
  { label: 'API Gateway', icon: Server, color: '#8B5CF6' },
  { label: 'Dual Operators', icon: GitBranch, color: '#EC4899' },
  { label: 'Graph Traversal', icon: Network, color: '#F59E0B' },
  { label: 'LLM Inference', icon: Cpu, color: '#10B981' },
  { label: 'Response', icon: Zap, color: '#3B82F6' },
];

// Layer Card Component
function LayerCard({
  layer,
  isActive,
  onClick,
}: {
  layer: (typeof architectureLayers)[0];
  isActive: boolean;
  onClick: () => void;
}) {
  const Icon = layer.icon;

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      className={`w-full p-4 rounded-xl text-left transition-all duration-300 ${
        isActive
          ? 'bg-white shadow-lg ring-2'
          : 'bg-[#F5F5F7] hover:bg-white hover:shadow-md'
      }`}
      style={{ '--tw-ring-color': isActive ? layer.color : 'transparent' } as React.CSSProperties}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ background: `${layer.color}15` }}
        >
          <Icon className="w-6 h-6" style={{ color: layer.color }} />
        </div>
        <div>
          <h3 className="font-bold">{layer.name}</h3>
          <p className="text-sm text-[#6E6E73]">{layer.description}</p>
        </div>
      </div>
    </motion.button>
  );
}

// Architecture Diagram
function ArchitectureDiagram({
  activeLayer,
}: {
  activeLayer: string | null;
}) {
  return (
    <div className="relative bg-gradient-to-br from-[#0A0A0F] to-[#1A1A2E] rounded-2xl p-8 min-h-[400px]">
      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />

      {/* Layers visualization */}
      <div className="relative z-10 space-y-3">
        {architectureLayers.map((layer, idx) => {
          const Icon = layer.icon;
          const isActive = activeLayer === layer.id;

          return (
            <motion.div
              key={layer.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{
                opacity: isActive ? 1 : 0.5,
                x: 0,
                scale: isActive ? 1.02 : 1,
              }}
              transition={{ delay: idx * 0.05 }}
              className={`flex items-center gap-4 p-4 rounded-xl transition-all ${
                isActive ? 'bg-white/10' : 'bg-white/5'
              }`}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ background: `${layer.color}30` }}
              >
                <Icon className="w-5 h-5" style={{ color: layer.color }} />
              </div>
              <div className="flex-1">
                <div className="text-white font-medium text-sm">
                  {layer.name}
                </div>
                <div className="flex gap-2 mt-1 flex-wrap">
                  {layer.tech.map((t) => (
                    <span
                      key={t}
                      className="px-2 py-0.5 text-xs rounded-full"
                      style={{
                        background: `${layer.color}20`,
                        color: layer.color,
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              {idx < architectureLayers.length - 1 && (
                <div className="text-white/30">
                  <ArrowRight className="w-4 h-4 rotate-90" />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Connection lines */}
      <svg
        className="absolute left-4 top-0 h-full pointer-events-none"
        width="20"
        style={{ zIndex: 0 }}
      >
        <line
          x1="10"
          y1="40"
          x2="10"
          y2="100%"
          stroke="url(#gradient)"
          strokeWidth="2"
          strokeDasharray="4 4"
        />
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="50%" stopColor="#EC4899" />
            <stop offset="100%" stopColor="#EF4444" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

// Main Page
export default function ArchitecturePage() {
  const [activeLayer, setActiveLayer] = useState<string>('orchestration');
  const selectedLayer = architectureLayers.find((l) => l.id === activeLayer);

  return (
    <PageWrapper>
      {/* Header */}
      <Section className="pt-24 pb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-2xl bg-[#667EEA]/10 flex items-center justify-center">
              <Layers className="w-8 h-8 text-[#667EEA]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">
                System Architecture
              </h1>
              <p className="text-xl text-[#6E6E73] mt-1">
                A deep dive into OpMech-GraphRAG internals
              </p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Data Flow */}
      <Section className="!pt-0">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-[#667EEA]/5 to-[#764BA2]/5 rounded-2xl p-8 mb-12"
        >
          <h2 className="text-2xl font-bold mb-6 text-center">
            Query Processing Flow
          </h2>

          <div className="flex items-center justify-between max-w-4xl mx-auto overflow-x-auto pb-4">
            {dataFlowSteps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div key={step.label} className="flex items-center">
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="flex flex-col items-center"
                  >
                    <div
                      className="w-14 h-14 rounded-xl flex items-center justify-center mb-2"
                      style={{ background: `${step.color}15` }}
                    >
                      <Icon className="w-6 h-6" style={{ color: step.color }} />
                    </div>
                    <span className="text-xs text-center font-medium whitespace-nowrap">
                      {step.label}
                    </span>
                  </motion.div>
                  {idx < dataFlowSteps.length - 1 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: idx * 0.1 + 0.05 }}
                      className="mx-2 text-[#6E6E73]"
                    >
                      <ArrowRight className="w-5 h-5" />
                    </motion.div>
                  )}
                </div>
              );
            })}
          </div>
        </motion.div>
      </Section>

      {/* Interactive Architecture Explorer */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-4">
          Architecture Layers
        </h2>
        <p className="text-center text-[#6E6E73] mb-12 max-w-2xl mx-auto">
          Click on each layer to explore its components and technology stack.
        </p>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Layer List */}
          <div className="space-y-3">
            {architectureLayers.map((layer) => (
              <LayerCard
                key={layer.id}
                layer={layer}
                isActive={activeLayer === layer.id}
                onClick={() => setActiveLayer(layer.id)}
              />
            ))}
          </div>

          {/* Visualization & Details */}
          <div className="space-y-6">
            <ArchitectureDiagram activeLayer={activeLayer} />

            {/* Layer Details */}
            {selectedLayer && (
              <motion.div
                key={selectedLayer.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-xl p-6 shadow-sm"
              >
                <h3
                  className="font-bold text-lg mb-4"
                  style={{ color: selectedLayer.color }}
                >
                  {selectedLayer.name} Components
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {selectedLayer.components.map((component) => (
                    <div
                      key={component}
                      className="flex items-center gap-2 p-3 bg-[#F5F5F7] rounded-lg text-sm"
                    >
                      <Box
                        className="w-4 h-4 flex-shrink-0"
                        style={{ color: selectedLayer.color }}
                      />
                      {component}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </Section>

      {/* Key Design Decisions */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-12">
          Key Design Decisions
        </h2>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {[
            {
              icon: GitBranch,
              title: 'Dual-Operator Design',
              desc: 'Two complementary retrieval strategies ensure comprehensive coverage of both structured and unstructured information.',
              color: '#3B82F6',
            },
            {
              icon: Shield,
              title: 'Evidence-Based Trust',
              desc: 'Trust decisions are based on evidence type hierarchy, not arbitrary heuristics. XBRL > Tables > Text.',
              color: '#10B981',
            },
            {
              icon: Zap,
              title: 'Adaptive Mode Selection',
              desc: 'The system automatically chooses between exploit, explore, or merge strategies based on operator divergence.',
              color: '#F59E0B',
            },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                className="bg-white rounded-2xl p-6 shadow-sm border border-[#E5E7EB]"
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{ background: `${item.color}15` }}
                >
                  <Icon className="w-6 h-6" style={{ color: item.color }} />
                </div>
                <h3 className="font-bold text-lg mb-2">{item.title}</h3>
                <p className="text-[#6E6E73]">{item.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </Section>

      {/* Tech Stack Summary */}
      <Section className="bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8">
            Technology Stack
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { category: 'Frontend', items: ['Next.js', 'React', 'Three.js'] },
              { category: 'Backend', items: ['FastAPI', 'Pydantic', 'vLLM'] },
              { category: 'Database', items: ['Neo4j', 'APOC', 'Full-text'] },
              { category: 'ML', items: ['Qwen2.5', 'GraphRAG', 'MoE'] },
            ].map((stack) => (
              <div key={stack.category} className="text-center">
                <div className="text-sm opacity-70 mb-2">{stack.category}</div>
                <div className="space-y-1">
                  {stack.items.map((item) => (
                    <div
                      key={item}
                      className="px-3 py-1 bg-white/20 rounded-full text-sm"
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/features/graph-construction"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Graph Construction
          </Link>
          <Link
            href="/metrics"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: Metrics Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
