'use client';

import { useState, useRef, Suspense } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Float, Sphere, MeshDistortMaterial, Line } from '@react-three/drei';
import * as THREE from 'three';
import {
  GitBranch,
  Gauge,
  Target,
  Shield,
  Network,
  ChevronRight,
  ArrowRight,
  Zap,
  Database,
  Brain,
  Workflow,
  Check,
  Play,
} from 'lucide-react';
import { PageWrapper, Section, PageHeader } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// Animated Pipeline Component
// ═══════════════════════════════════════════════════════════════════════════

function PipelineNode({ position, label, isActive, delay = 0 }: {
  position: [number, number, number];
  label: string;
  isActive: boolean;
  delay?: number
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (meshRef.current && isActive) {
      meshRef.current.scale.setScalar(1 + Math.sin(clock.elapsedTime * 2 + delay) * 0.1);
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.3}>
      <mesh ref={meshRef} position={position}>
        <sphereGeometry args={[0.3, 32, 32]} />
        <meshStandardMaterial
          color={isActive ? '#667EEA' : '#94A3B8'}
          emissive={isActive ? '#667EEA' : '#000000'}
          emissiveIntensity={isActive ? 0.5 : 0}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>
    </Float>
  );
}

function AnimatedPipeline() {
  const [activeStep, setActiveStep] = useState(0);

  useFrame(({ clock }) => {
    setActiveStep(Math.floor(clock.elapsedTime * 0.5) % 6);
  });

  const nodes: [number, number, number][] = [
    [-3, 0, 0],   // Query
    [-1.5, 0, 0], // Classifier
    [0, 1, 0],    // Operator A
    [0, -1, 0],   // Operator B
    [1.5, 0, 0],  // Commutator
    [3, 0, 0],    // Output
  ];

  return (
    <>
      {nodes.map((pos, i) => (
        <PipelineNode
          key={i}
          position={pos}
          label=""
          isActive={i <= activeStep}
          delay={i * 0.5}
        />
      ))}

      {/* Connection lines */}
      <Line points={[nodes[0], nodes[1]]} color={activeStep >= 1 ? '#667EEA' : '#94A3B8'} lineWidth={2} />
      <Line points={[nodes[1], nodes[2]]} color={activeStep >= 2 ? '#3B82F6' : '#94A3B8'} lineWidth={2} />
      <Line points={[nodes[1], nodes[3]]} color={activeStep >= 2 ? '#10B981' : '#94A3B8'} lineWidth={2} />
      <Line points={[nodes[2], nodes[4]]} color={activeStep >= 4 ? '#667EEA' : '#94A3B8'} lineWidth={2} />
      <Line points={[nodes[3], nodes[4]]} color={activeStep >= 4 ? '#667EEA' : '#94A3B8'} lineWidth={2} />
      <Line points={[nodes[4], nodes[5]]} color={activeStep >= 5 ? '#FFD700' : '#94A3B8'} lineWidth={2} />

      <ambientLight intensity={0.5} />
      <pointLight position={[5, 5, 5]} intensity={1} />
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Feature Data
// ═══════════════════════════════════════════════════════════════════════════

const features = [
  {
    id: 'dual-operators',
    icon: GitBranch,
    title: 'Dual Operator Architecture',
    subtitle: 'Two perspectives, one truth',
    description: 'Two complementary operators explore the knowledge graph from different angles: Operator A follows structured paths (XBRL, hierarchical), while Operator B follows narrative paths (MD&A, semantic).',
    highlights: [
      'Structure-first vs Narrative-first approaches',
      'Independent evidence collection',
      'Complementary strengths for different query types',
    ],
    color: '#3B82F6',
    href: '/features/dual-operators',
  },
  {
    id: 'commutator',
    icon: Gauge,
    title: 'The Commutator',
    subtitle: 'Measuring perspective divergence',
    description: 'Inspired by quantum mechanics, the commutator measures how much the operators\' perspectives diverge. [A,B] = AB - BA ≠ 0 reveals fundamental uncertainty in knowledge retrieval.',
    highlights: [
      'Evidence overlap (Δ_E)',
      'Structural overlap (Δ_V)',
      'Answer agreement (Δ_A)',
      'Confidence agreement (Δ_C)',
    ],
    color: '#8B5CF6',
    href: '/features/commutator',
  },
  {
    id: 'mode-selection',
    icon: Target,
    title: 'Intelligent Mode Selection',
    subtitle: 'EXPLOIT, ADAPTIVE, EXPLORE',
    description: 'Based on divergence analysis, OpMech automatically selects the optimal response strategy. Low divergence → EXPLOIT with high confidence. High divergence → EXPLORE multiple perspectives.',
    highlights: [
      'EXPLOIT: Direct answers when operators agree',
      'ADAPTIVE: Balanced analysis with nuance',
      'EXPLORE: Multiple viewpoints when perspectives differ',
    ],
    color: '#F59E0B',
    href: '/features/mode-selection',
  },
  {
    id: 'trust-decision',
    icon: Shield,
    title: 'Trust & Evidence Scoring',
    subtitle: 'Knowing which source to believe',
    description: 'When operators disagree, the trust decision system determines which evidence to prioritize based on query type and evidence authority hierarchy.',
    highlights: [
      'Evidence authority pyramid (XBRL → Tables → Text → Notes)',
      'Query-aware trust decisions',
      'Numerical queries trust structured data',
    ],
    color: '#10B981',
    href: '/features/trust-decision',
  },
  {
    id: 'graph-construction',
    icon: Network,
    title: 'MoE Graph Construction',
    subtitle: '7 specialized experts',
    description: 'A Mixture-of-Experts approach builds the knowledge graph using 7 specialized experts, each focusing on different aspects of SEC filings.',
    highlights: [
      'Entity Expert: Companies, products, people',
      'Financial Expert: XBRL tags, metrics',
      'Relationship Expert: Semantic connections',
      'Temporal Expert: Time-based links',
    ],
    color: '#EC4899',
    href: '/features/graph-construction',
  },
];

const pipelineSteps = [
  { label: 'Query', description: 'User question enters the system', icon: Zap },
  { label: 'Classifier', description: 'Query type and complexity analysis', icon: Brain },
  { label: 'Operators', description: 'Dual traversal begins', icon: GitBranch },
  { label: 'Commutator', description: 'Divergence measurement', icon: Gauge },
  { label: 'Mode Select', description: 'Strategy determination', icon: Target },
  { label: 'Response', description: 'Unified answer generation', icon: Check },
];

// ═══════════════════════════════════════════════════════════════════════════
// Main Page Component
// ═══════════════════════════════════════════════════════════════════════════

export default function FeaturesPage() {
  return (
    <PageWrapper>
      {/* Hero Section */}
      <Section className="pt-24">
        <PageHeader
          badge="System Overview"
          title="How OpMech Works"
          subtitle="A novel approach to knowledge retrieval that combines dual operators with commutator-guided explore/exploit strategies"
        />

        {/* Animated Pipeline Visualization */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="relative h-[400px] rounded-3xl overflow-hidden bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14] mb-16"
        >
          <Suspense fallback={<div className="w-full h-full animate-pulse" />}>
            <Canvas camera={{ position: [0, 0, 8], fov: 50 }}>
              <AnimatedPipeline />
              <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.3} />
            </Canvas>
          </Suspense>

          {/* Pipeline labels */}
          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 to-transparent">
            <div className="flex justify-between max-w-4xl mx-auto">
              {pipelineSteps.map((step, idx) => (
                <div key={step.label} className="text-center">
                  <step.icon className="w-5 h-5 mx-auto mb-1 text-white/60" />
                  <div className="text-xs text-white/80 font-medium">{step.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Click prompt */}
          <div className="absolute top-4 right-4 px-3 py-1.5 bg-white/10 backdrop-blur-sm rounded-full text-white/60 text-xs">
            Click any component to learn more
          </div>
        </motion.div>
      </Section>

      {/* Feature Deep Dives */}
      <Section className="bg-[#F5F5F7] !pt-0">
        <div className="space-y-6">
          {features.map((feature, idx) => (
            <motion.div
              key={feature.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
            >
              <Link href={feature.href} className="block group">
                <div className="bg-white rounded-2xl p-8 md:p-10 shadow-sm border border-black/5 hover:shadow-xl hover:border-[#667EEA]/20 transition-all duration-300">
                  <div className="flex flex-col md:flex-row md:items-start gap-8">
                    {/* Icon and number */}
                    <div className="flex items-center gap-4 md:flex-col md:items-start">
                      <span className="text-4xl font-bold text-[#E5E5E5]">0{idx + 1}</span>
                      <div
                        className="w-16 h-16 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform"
                        style={{ background: `${feature.color}15` }}
                      >
                        <feature.icon className="w-8 h-8" style={{ color: feature.color }} />
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-2xl font-bold mb-1">{feature.title}</h3>
                          <p className="text-[#6E6E73] mb-4">{feature.subtitle}</p>
                        </div>
                        <ArrowRight
                          className="w-6 h-6 text-[#667EEA] opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all"
                        />
                      </div>

                      <p className="text-[#6E6E73] leading-relaxed mb-6">
                        {feature.description}
                      </p>

                      <div className="grid sm:grid-cols-2 gap-3">
                        {feature.highlights.map((highlight, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 text-sm"
                          >
                            <div
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ background: feature.color }}
                            />
                            <span className="text-[#6E6E73]">{highlight}</span>
                          </div>
                        ))}
                      </div>

                      <div className="mt-6 inline-flex items-center gap-2 text-sm font-semibold opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: feature.color }}>
                        Explore in detail
                        <ChevronRight className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* Quick Stats */}
      <Section dark>
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold">System Performance</h2>
          <p className="mt-2 text-white/60">Measured on Apple SEC filings dataset</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { value: '100%', label: 'Mode Accuracy' },
            { value: '100%', label: 'Answer Quality' },
            { value: '93%', label: 'Traversal Reduction' },
            { value: '4.2', label: 'Avg Hops' },
          ].map((stat, idx) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className="text-center"
            >
              <div className="text-4xl md:text-5xl font-bold mb-2">{stat.value}</div>
              <div className="text-sm text-white/60 uppercase tracking-wider">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* CTA */}
      <Section>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="text-center"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to See OpMech in Action?
          </h2>
          <p className="text-lg text-[#6E6E73] max-w-2xl mx-auto mb-8">
            Experience the dual-operator system live. Ask questions about Apple&apos;s SEC filings and watch the system think.
          </p>
          <Link
            href="/demo"
            className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white font-semibold rounded-full shadow-lg shadow-[#667EEA]/30 hover:shadow-xl hover:shadow-[#667EEA]/40 transition-all hover:-translate-y-0.5"
          >
            <Play className="w-5 h-5" />
            Launch Live Demo
            <ArrowRight className="w-4 h-4" />
          </Link>
        </motion.div>
      </Section>
    </PageWrapper>
  );
}
