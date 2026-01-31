'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { motion, useSpring, useTransform } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  Info,
  Zap,
  Target,
  Search,
  Play,
  Send,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// Animated Divergence Gauge
// ═══════════════════════════════════════════════════════════════════════════

function DivergenceGauge({ value, size = 200 }: { value: number; size?: number }) {
  const springValue = useSpring(value, { stiffness: 100, damping: 20 });
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    return springValue.on('change', (v) => setDisplayValue(v));
  }, [springValue]);

  useEffect(() => {
    springValue.set(value);
  }, [value, springValue]);

  const getColor = (v: number) => {
    if (v < 0.25) return '#10B981'; // Green - EXPLOIT
    if (v < 0.60) return '#F59E0B'; // Orange - ADAPTIVE
    return '#EF4444'; // Red - EXPLORE
  };

  const circumference = 2 * Math.PI * 80;
  const strokeDashoffset = circumference - (circumference * 0.75 * displayValue);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg viewBox="0 0 200 200" className="w-full h-full -rotate-135">
        {/* Background arc */}
        <circle
          cx="100"
          cy="100"
          r="80"
          fill="none"
          stroke="#E5E7EB"
          strokeWidth="16"
          strokeDasharray={circumference * 0.75}
          strokeLinecap="round"
        />

        {/* Value arc */}
        <motion.circle
          cx="100"
          cy="100"
          r="80"
          fill="none"
          stroke={getColor(displayValue)}
          strokeWidth="16"
          strokeDasharray={circumference * 0.75}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 10px ${getColor(displayValue)}40)` }}
        />
      </svg>

      {/* Center display */}
      <div className="absolute inset-0 flex flex-col items-center justify-center rotate-0">
        <span className="text-4xl font-bold" style={{ color: getColor(displayValue) }}>
          {displayValue.toFixed(3)}
        </span>
        <span className="text-sm text-[#6E6E73] mt-1">Divergence (Δ)</span>
      </div>

      {/* Threshold markers */}
      <div className="absolute bottom-4 left-0 right-0 flex justify-between px-4 text-xs text-[#6E6E73]">
        <span>0</span>
        <span>τ_low (0.25)</span>
        <span>τ_high (0.60)</span>
        <span>1</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Component Bar
// ═══════════════════════════════════════════════════════════════════════════

function ComponentBar({
  label,
  value,
  description,
  color,
}: {
  label: string;
  value: number;
  description: string;
  color: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono font-semibold">{label}</span>
          <span className="text-xs text-[#6E6E73]">{description}</span>
        </div>
        <span className="font-mono text-sm">{value.toFixed(2)}</span>
      </div>
      <div className="h-3 bg-[#F5F5F7] rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ background: color }}
        />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Mode Card
// ═══════════════════════════════════════════════════════════════════════════

function ModeCard({
  mode,
  range,
  description,
  meaning,
  color,
  isActive,
}: {
  mode: string;
  range: string;
  description: string;
  meaning: string;
  color: string;
  isActive: boolean;
}) {
  return (
    <motion.div
      animate={{
        scale: isActive ? 1.02 : 1,
        borderColor: isActive ? color : '#E5E7EB',
      }}
      className="p-6 bg-white rounded-xl border-2 transition-shadow"
      style={{
        boxShadow: isActive ? `0 8px 30px ${color}30` : 'none',
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="px-3 py-1 text-sm font-bold rounded-full text-white"
          style={{ background: color }}
        >
          {mode}
        </span>
        <span className="text-sm text-[#6E6E73]">{range}</span>
      </div>
      <p className="font-medium mb-1">{description}</p>
      <p className="text-sm text-[#6E6E73]">{meaning}</p>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Page Component
// ═══════════════════════════════════════════════════════════════════════════

export default function CommutatorPage() {
  const [divergence, setDivergence] = useState(0.335);
  const [deltaE, setDeltaE] = useState(0.63);
  const [deltaV, setDeltaV] = useState(0.57);
  const [deltaA, setDeltaA] = useState(0.03);
  const [deltaC, setDeltaC] = useState(0.11);
  const [demoQuery, setDemoQuery] = useState('What was Apple\'s revenue in FY2023?');

  const getActiveMode = (d: number) => {
    if (d < 0.25) return 'EXPLOIT';
    if (d < 0.60) return 'ADAPTIVE';
    return 'EXPLORE';
  };

  const runDemo = (type: 'revenue' | 'opinion' | 'margin') => {
    const presets = {
      revenue: { d: 0.18, e: 0.85, v: 0.72, a: 0.92, c: 0.88, query: 'What was Apple\'s revenue in FY2023?' },
      opinion: { d: 0.71, e: 0.32, v: 0.28, a: 0.15, c: 0.21, query: 'Is Apple overvalued compared to peers?' },
      margin: { d: 0.42, e: 0.55, v: 0.48, a: 0.45, c: 0.52, query: 'Why did iPhone sales change?' },
    };
    const p = presets[type];
    setDivergence(p.d);
    setDeltaE(p.e);
    setDeltaV(p.v);
    setDeltaA(p.a);
    setDeltaC(p.c);
    setDemoQuery(p.query);
  };

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
            <div className="w-16 h-16 rounded-2xl bg-[#8B5CF6]/10 flex items-center justify-center">
              <Target className="w-8 h-8 text-[#8B5CF6]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">The Commutator</h1>
              <p className="text-xl text-[#6E6E73] mt-1">Measuring perspective divergence</p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Math Section */}
      <Section className="!pt-0">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-[#8B5CF6]/5 to-[#667EEA]/5 rounded-2xl p-8 mb-12"
        >
          <h2 className="text-2xl font-bold mb-4">The Math (Made Simple)</h2>

          <div className="bg-white/80 backdrop-blur rounded-xl p-6 mb-6">
            <div className="text-center mb-6">
              <span className="font-mono text-3xl font-bold text-[#8B5CF6]">
                [A, B] = AB - BA ≠ 0
              </span>
            </div>

            <div className="space-y-4 text-[#6E6E73]">
              <p>
                In <strong className="text-[#1D1D1F]">quantum mechanics</strong>, when operators don&apos;t commute,
                it reveals fundamental uncertainty (like position and momentum).
              </p>
              <p>
                In <strong className="text-[#1D1D1F]">OpMech</strong>, when operators diverge, it reveals
                how much the perspectives differ on a question.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-[#8B5CF6]/10 rounded-xl">
            <Info className="w-5 h-5 text-[#8B5CF6] mt-0.5 flex-shrink-0" />
            <p className="text-sm text-[#6E6E73]">
              <strong className="text-[#1D1D1F]">Key insight:</strong> The commutator isn&apos;t just measuring disagreement—it&apos;s
              measuring how the order of operations affects the result. This gives us deep insight into the
              nature of the question itself.
            </p>
          </div>
        </motion.div>
      </Section>

      {/* Interactive Divergence Section */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-4">Divergence Components</h2>
        <p className="text-center text-[#6E6E73] max-w-2xl mx-auto mb-12">
          Drag the slider to see how divergence affects mode selection
        </p>

        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Gauge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="flex justify-center"
          >
            <DivergenceGauge value={divergence} size={280} />
          </motion.div>

          {/* Components */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="space-y-6"
          >
            <ComponentBar
              label="Δ_E"
              value={deltaE}
              description="Evidence Overlap"
              color="#3B82F6"
            />
            <ComponentBar
              label="Δ_V"
              value={deltaV}
              description="Structural Overlap"
              color="#8B5CF6"
            />
            <ComponentBar
              label="Δ_A"
              value={deltaA}
              description="Answer Agreement"
              color="#10B981"
            />
            <ComponentBar
              label="Δ_C"
              value={deltaC}
              description="Confidence Agreement"
              color="#F59E0B"
            />

            {/* Slider */}
            <div className="pt-4">
              <label className="block text-sm font-medium mb-2">
                Adjust Combined Divergence (Δ)
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={divergence}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  setDivergence(v);
                  // Simulate component changes
                  setDeltaE(0.5 + v * 0.3 + Math.random() * 0.1);
                  setDeltaV(0.4 + v * 0.4 + Math.random() * 0.1);
                  setDeltaA(1 - v * 0.8 + Math.random() * 0.1);
                  setDeltaC(0.8 - v * 0.5 + Math.random() * 0.1);
                }}
                className="w-full h-2 bg-gradient-to-r from-[#10B981] via-[#F59E0B] to-[#EF4444] rounded-full appearance-none cursor-pointer"
              />
            </div>
          </motion.div>
        </div>
      </Section>

      {/* What Divergence Tells Us */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-12">What Divergence Tells Us</h2>

        <div className="grid md:grid-cols-3 gap-6">
          <ModeCard
            mode="EXPLOIT"
            range="Δ < 0.25"
            description="Operators AGREE"
            meaning="High confidence, direct answer from authoritative source"
            color="#10B981"
            isActive={getActiveMode(divergence) === 'EXPLOIT'}
          />
          <ModeCard
            mode="ADAPTIVE"
            range="0.25 ≤ Δ < 0.60"
            description="Operators PARTIALLY AGREE"
            meaning="Balanced analysis with nuanced context"
            color="#F59E0B"
            isActive={getActiveMode(divergence) === 'ADAPTIVE'}
          />
          <ModeCard
            mode="EXPLORE"
            range="Δ ≥ 0.60"
            description="Operators DISAGREE"
            meaning="Multiple viewpoints presented for consideration"
            color="#EF4444"
            isActive={getActiveMode(divergence) === 'EXPLORE'}
          />
        </div>
      </Section>

      {/* Live Example */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-4">Live Example</h2>
        <p className="text-center text-[#6E6E73] max-w-2xl mx-auto mb-8">
          Try different query types and watch the divergence change
        </p>

        <div className="max-w-3xl mx-auto">
          <div className="bg-white rounded-2xl p-6 shadow-sm mb-6">
            <div className="flex items-center gap-4 mb-4">
              <input
                type="text"
                value={demoQuery}
                onChange={(e) => setDemoQuery(e.target.value)}
                className="flex-1 px-4 py-3 bg-[#F5F5F7] rounded-xl border border-transparent focus:border-[#667EEA] focus:outline-none transition-colors"
                placeholder="Enter a query..."
              />
              <button className="p-3 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white rounded-xl">
                <Send className="w-5 h-5" />
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="text-sm text-[#6E6E73]">Suggested:</span>
              <button
                onClick={() => runDemo('revenue')}
                className="px-3 py-1 text-sm bg-[#10B981]/10 text-[#10B981] rounded-full hover:bg-[#10B981]/20 transition-colors"
              >
                Revenue Query (Low Δ → EXPLOIT)
              </button>
              <button
                onClick={() => runDemo('margin')}
                className="px-3 py-1 text-sm bg-[#F59E0B]/10 text-[#F59E0B] rounded-full hover:bg-[#F59E0B]/20 transition-colors"
              >
                Causal Query (Medium Δ → ADAPTIVE)
              </button>
              <button
                onClick={() => runDemo('opinion')}
                className="px-3 py-1 text-sm bg-[#EF4444]/10 text-[#EF4444] rounded-full hover:bg-[#EF4444]/20 transition-colors"
              >
                Opinion Query (High Δ → EXPLORE)
              </button>
            </div>
          </div>

          {/* Result display */}
          <motion.div
            key={divergence}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl p-6 shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span
                  className="px-4 py-1.5 text-sm font-bold rounded-full text-white"
                  style={{
                    background:
                      getActiveMode(divergence) === 'EXPLOIT'
                        ? '#10B981'
                        : getActiveMode(divergence) === 'ADAPTIVE'
                        ? '#F59E0B'
                        : '#EF4444',
                  }}
                >
                  {getActiveMode(divergence)}
                </span>
                <span className="text-[#6E6E73]">
                  Divergence: <strong className="text-[#1D1D1F]">{divergence.toFixed(3)}</strong>
                </span>
              </div>
              <Zap className="w-5 h-5 text-[#667EEA]" />
            </div>

            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-lg font-bold text-[#3B82F6]">{deltaE.toFixed(2)}</div>
                <div className="text-xs text-[#6E6E73]">Δ_E</div>
              </div>
              <div>
                <div className="text-lg font-bold text-[#8B5CF6]">{deltaV.toFixed(2)}</div>
                <div className="text-xs text-[#6E6E73]">Δ_V</div>
              </div>
              <div>
                <div className="text-lg font-bold text-[#10B981]">{deltaA.toFixed(2)}</div>
                <div className="text-xs text-[#6E6E73]">Δ_A</div>
              </div>
              <div>
                <div className="text-lg font-bold text-[#F59E0B]">{deltaC.toFixed(2)}</div>
                <div className="text-xs text-[#6E6E73]">Δ_C</div>
              </div>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/features/dual-operators"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Dual Operators
          </Link>
          <Link
            href="/features/mode-selection"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: Mode Selection
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
