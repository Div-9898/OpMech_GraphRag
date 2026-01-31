'use client';

import { useState, useRef, Suspense, useMemo } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line, Text, Float } from '@react-three/drei';
import * as THREE from 'three';
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  RotateCcw,
  Database,
  FileText,
  Hash,
  AlignLeft,
  ChevronRight,
  Zap,
  Info,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// Interactive Dual Operator Visualization
// ═══════════════════════════════════════════════════════════════════════════

function OperatorNode({
  position,
  color,
  size = 0.15,
  pulsing = false,
  delay = 0,
}: {
  position: [number, number, number];
  color: string;
  size?: number;
  pulsing?: boolean;
  delay?: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (meshRef.current && pulsing) {
      const scale = 1 + Math.sin(clock.elapsedTime * 3 + delay) * 0.2;
      meshRef.current.scale.setScalar(scale);
    }
  });

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[size, 32, 32]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={pulsing ? 0.8 : 0.3}
        metalness={0.3}
        roughness={0.5}
      />
    </mesh>
  );
}

// Deterministic pseudo-random function to avoid hydration mismatch
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9999) * 10000;
  return x - Math.floor(x);
}

function DualOperatorGraph({ activeOperator, isAnimating }: { activeOperator: 'A' | 'B' | 'both'; isAnimating: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  // Generate node positions using deterministic seeded random
  const nodesA = useMemo(() => {
    const nodes: [number, number, number][] = [];
    // Structured traversal pattern (grid-like)
    for (let i = 0; i < 12; i++) {
      const angle = (i / 12) * Math.PI * 2;
      const radius = 1 + (i % 3) * 0.5;
      nodes.push([Math.cos(angle) * radius - 1.5, Math.sin(angle) * radius, (seededRandom(i * 17) - 0.5) * 0.5]);
    }
    return nodes;
  }, []);

  const nodesB = useMemo(() => {
    const nodes: [number, number, number][] = [];
    // Semantic traversal pattern (organic)
    for (let i = 0; i < 12; i++) {
      const angle = (i / 12) * Math.PI * 2 + 0.3;
      const radius = 1.2 + Math.sin(i * 0.8) * 0.4;
      nodes.push([Math.cos(angle) * radius + 1.5, Math.sin(angle) * radius, (seededRandom(i * 23 + 100) - 0.5) * 0.5]);
    }
    return nodes;
  }, []);

  // Bridge nodes (shared evidence)
  const bridgeNodes: [number, number, number][] = [
    [0, 0, 0],
    [0, 0.8, 0.2],
    [0, -0.8, -0.2],
  ];

  useFrame(({ clock }) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(clock.elapsedTime * 0.2) * 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Query node at center */}
      <Float speed={2} rotationIntensity={0.3}>
        <mesh position={[0, 0, 0]}>
          <sphereGeometry args={[0.25, 32, 32]} />
          <meshStandardMaterial color="#FFD700" emissive="#FFD700" emissiveIntensity={0.5} />
        </mesh>
      </Float>

      {/* Operator A nodes */}
      {(activeOperator === 'A' || activeOperator === 'both') && nodesA.map((pos, i) => (
        <OperatorNode
          key={`a-${i}`}
          position={pos}
          color="#3B82F6"
          pulsing={isAnimating}
          delay={i * 0.2}
        />
      ))}

      {/* Operator A edges */}
      {(activeOperator === 'A' || activeOperator === 'both') && nodesA.slice(0, -1).map((pos, i) => (
        <Line
          key={`ea-${i}`}
          points={[pos, nodesA[(i + 1) % nodesA.length]]}
          color="#3B82F6"
          lineWidth={1.5}
          opacity={0.6}
          transparent
        />
      ))}

      {/* Operator B nodes */}
      {(activeOperator === 'B' || activeOperator === 'both') && nodesB.map((pos, i) => (
        <OperatorNode
          key={`b-${i}`}
          position={pos}
          color="#10B981"
          pulsing={isAnimating}
          delay={i * 0.2 + Math.PI}
        />
      ))}

      {/* Operator B edges */}
      {(activeOperator === 'B' || activeOperator === 'both') && nodesB.slice(0, -1).map((pos, i) => (
        <Line
          key={`eb-${i}`}
          points={[pos, nodesB[(i + 1) % nodesB.length]]}
          color="#10B981"
          lineWidth={1.5}
          opacity={0.6}
          transparent
        />
      ))}

      {/* Bridge edges (when both active) */}
      {activeOperator === 'both' && bridgeNodes.map((pos, i) => (
        <OperatorNode
          key={`bridge-${i}`}
          position={pos}
          color="#FFD700"
          size={0.12}
          pulsing={isAnimating}
          delay={i}
        />
      ))}

      {/* Connecting lines to query */}
      {(activeOperator === 'A' || activeOperator === 'both') && (
        <Line points={[[0, 0, 0], nodesA[0]]} color="#3B82F6" lineWidth={2} opacity={0.8} transparent />
      )}
      {(activeOperator === 'B' || activeOperator === 'both') && (
        <Line points={[[0, 0, 0], nodesB[0]]} color="#10B981" lineWidth={2} opacity={0.8} transparent />
      )}

      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={1} color="#FFFFFF" />
      <pointLight position={[-5, -5, 5]} intensity={0.5} color="#667EEA" />
    </group>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Comparison Data
// ═══════════════════════════════════════════════════════════════════════════

const operatorComparison = {
  A: {
    name: 'Operator A',
    subtitle: 'Structure-First',
    color: '#3B82F6',
    icon: Database,
    startingPoints: [
      'XBRL financial tags',
      'Direct entity matches',
      'Hierarchical document structure',
    ],
    traversalStrategy: [
      'Follow hierarchical relationships',
      'Prefer structured data paths',
      'Priority: parent → child → sibling',
    ],
    bestFor: [
      'Exact figures',
      'Financial metrics',
      'Regulatory data',
      'Time series data',
    ],
    evidenceTypes: [
      { type: 'FINANCIAL_LINE', percentage: 62, color: '#3B82F6' },
      { type: 'NOTE', percentage: 23, color: '#F59E0B' },
      { type: 'TEXT_SECTION', percentage: 15, color: '#10B981' },
    ],
  },
  B: {
    name: 'Operator B',
    subtitle: 'Narrative-First',
    color: '#10B981',
    icon: FileText,
    startingPoints: [
      'Semantic similarity',
      'Keyword expansion',
      'Topic modeling clusters',
    ],
    traversalStrategy: [
      'Follow semantic connections',
      'Prefer contextual narrative paths',
      'Priority: related → similar → adjacent',
    ],
    bestFor: [
      'Context & explanation',
      'Qualitative insights',
      'Trend analysis',
      'Risk factors',
    ],
    evidenceTypes: [
      { type: 'TEXT_SECTION', percentage: 45, color: '#10B981' },
      { type: 'NOTE', percentage: 35, color: '#F59E0B' },
      { type: 'FINANCIAL_LINE', percentage: 20, color: '#3B82F6' },
    ],
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// Main Page Component
// ═══════════════════════════════════════════════════════════════════════════

export default function DualOperatorsPage() {
  const [activeOperator, setActiveOperator] = useState<'A' | 'B' | 'both'>('both');
  const [isAnimating, setIsAnimating] = useState(true);

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
            <div className="w-16 h-16 rounded-2xl bg-[#3B82F6]/10 flex items-center justify-center">
              <Database className="w-8 h-8 text-[#3B82F6]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">Dual Operator Architecture</h1>
              <p className="text-xl text-[#6E6E73] mt-1">Two perspectives, one truth</p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Concept Introduction */}
      <Section className="!pt-0">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-[#667EEA]/5 to-[#764BA2]/5 rounded-2xl p-8 mb-12"
        >
          <h2 className="text-2xl font-bold mb-4">The Concept</h2>
          <p className="text-lg text-[#6E6E73] leading-relaxed">
            Just as quantum mechanics uses non-commuting operators to reveal hidden properties,
            OpMech uses two complementary operators to explore knowledge from different angles.
            <span className="block mt-4 font-medium text-[#1D1D1F]">
              Operator A follows structured paths through financial data, while Operator B follows
              semantic paths through narrative text. Where they converge, truth emerges.
            </span>
            <span className="block mt-4 text-[#667EEA] font-medium">
              Two-Phase Execution: At hop 1, operators explore independently. From hop 2+, each operator
              receives evidence from the other to enable convergence-aware exploration.
            </span>
          </p>
        </motion.div>

        {/* Interactive Visualization */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-12"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold">Interactive Visualization</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsAnimating(!isAnimating)}
                className="p-2 rounded-lg bg-[#F5F5F7] hover:bg-[#E5E5E5] transition-colors"
              >
                {isAnimating ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <div className="relative h-[500px] rounded-3xl overflow-hidden bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
            <Suspense fallback={<div className="w-full h-full animate-pulse" />}>
              <Canvas camera={{ position: [0, 0, 6], fov: 50 }}>
                <DualOperatorGraph activeOperator={activeOperator} isAnimating={isAnimating} />
                <OrbitControls enableZoom={true} enablePan={false} />
              </Canvas>
            </Suspense>

            {/* Controls */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2">
              {(['A', 'B', 'both'] as const).map((op) => (
                <button
                  key={op}
                  onClick={() => setActiveOperator(op)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    activeOperator === op
                      ? 'bg-white text-[#1D1D1F] shadow-lg'
                      : 'bg-white/10 text-white/70 hover:bg-white/20'
                  }`}
                >
                  {op === 'both' ? 'Both Operators' : `Operator ${op}`}
                </button>
              ))}
            </div>

            {/* Legend */}
            <div className="absolute top-6 right-6 space-y-2">
              <div className="flex items-center gap-2 text-sm text-white/80">
                <span className="w-3 h-3 rounded-full bg-[#3B82F6]" />
                Operator A (Structure)
              </div>
              <div className="flex items-center gap-2 text-sm text-white/80">
                <span className="w-3 h-3 rounded-full bg-[#10B981]" />
                Operator B (Narrative)
              </div>
              <div className="flex items-center gap-2 text-sm text-white/80">
                <span className="w-3 h-3 rounded-full bg-[#FFD700]" />
                Bridge / Query
              </div>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Operator Comparison */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-12">Operator Comparison</h2>

        <div className="grid md:grid-cols-2 gap-8">
          {(['A', 'B'] as const).map((op) => {
            const data = operatorComparison[op];
            const Icon = data.icon;

            return (
              <motion.div
                key={op}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="bg-white rounded-2xl p-8 shadow-sm"
                style={{ borderTop: `4px solid ${data.color}` }}
              >
                <div className="flex items-center gap-3 mb-6">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ background: `${data.color}15` }}
                  >
                    <Icon className="w-6 h-6" style={{ color: data.color }} />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">{data.name}</h3>
                    <p className="text-[#6E6E73]">{data.subtitle}</p>
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <h4 className="font-semibold text-sm uppercase tracking-wider text-[#6E6E73] mb-3">
                      Starting Points
                    </h4>
                    <ul className="space-y-2">
                      {data.startingPoints.map((point, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: data.color }} />
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-sm uppercase tracking-wider text-[#6E6E73] mb-3">
                      Traversal Strategy
                    </h4>
                    <ul className="space-y-2">
                      {data.traversalStrategy.map((strategy, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: data.color }} />
                          {strategy}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-sm uppercase tracking-wider text-[#6E6E73] mb-3">
                      Best For
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {data.bestFor.map((item, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 text-xs font-medium rounded-full"
                          style={{ background: `${data.color}15`, color: data.color }}
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-sm uppercase tracking-wider text-[#6E6E73] mb-3">
                      Evidence Distribution
                    </h4>
                    <div className="space-y-2">
                      {data.evidenceTypes.map((ev, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <span className="w-24 text-xs text-[#6E6E73]">{ev.type}</span>
                          <div className="flex-1 h-2 bg-[#F5F5F7] rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              whileInView={{ width: `${ev.percentage}%` }}
                              viewport={{ once: true }}
                              transition={{ duration: 0.8, delay: i * 0.1 }}
                              className="h-full rounded-full"
                              style={{ background: ev.color }}
                            />
                          </div>
                          <span className="w-10 text-xs text-right">{ev.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Section>

      {/* Why Two Operators */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-4">Why Two Operators?</h2>
        <p className="text-center text-[#6E6E73] max-w-2xl mx-auto mb-12">
          See how dual perspectives provide richer, more accurate answers
        </p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="bg-gradient-to-r from-[#3B82F6]/5 via-[#FFD700]/5 to-[#10B981]/5 rounded-2xl p-8"
        >
          <div className="mb-6 p-4 bg-white rounded-xl">
            <p className="text-sm text-[#6E6E73] mb-2">Example Query</p>
            <p className="text-lg font-semibold">&ldquo;What was Apple&apos;s revenue in FY2023?&rdquo;</p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="p-6 bg-white rounded-xl border-l-4 border-[#3B82F6]">
              <h4 className="font-bold mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#3B82F6]" />
                Operator A finds:
              </h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <Hash className="w-4 h-4 mt-0.5 text-[#3B82F6]" />
                  <span><strong>XBRL:</strong> $383,285,000,000</span>
                </li>
                <li className="flex items-start gap-2">
                  <Database className="w-4 h-4 mt-0.5 text-[#3B82F6]" />
                  <span><strong>Label:</strong> &ldquo;Net Sales&rdquo;</span>
                </li>
                <li className="flex items-start gap-2">
                  <Info className="w-4 h-4 mt-0.5 text-[#3B82F6]" />
                  <span><strong>Period:</strong> FY2023</span>
                </li>
              </ul>
            </div>

            <div className="p-6 bg-white rounded-xl border-l-4 border-[#10B981]">
              <h4 className="font-bold mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#10B981]" />
                Operator B finds:
              </h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <FileText className="w-4 h-4 mt-0.5 text-[#10B981]" />
                  <span><strong>MD&A:</strong> &ldquo;Revenue of approximately $383B&rdquo;</span>
                </li>
                <li className="flex items-start gap-2">
                  <AlignLeft className="w-4 h-4 mt-0.5 text-[#10B981]" />
                  <span><strong>Context:</strong> &ldquo;slight decrease from FY2022&rdquo;</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-6 p-6 bg-gradient-to-r from-[#667EEA] to-[#764BA2] rounded-xl text-white">
            <h4 className="font-bold mb-2 flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Combined Result:
            </h4>
            <p>
              Precise figure (<strong>$383.29B</strong>) WITH context (YoY change of -2.8% from FY2022)
            </p>
          </div>
        </motion.div>
      </Section>

      {/* Navigation */}
      <Section className="bg-[#F5F5F7] !py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/features"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Features Overview
          </Link>
          <Link
            href="/features/commutator"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: The Commutator
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
