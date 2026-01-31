'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  Zap,
  Scale,
  Search,
  ChevronRight,
  Check,
  AlertCircle,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// Mode Data
// ═══════════════════════════════════════════════════════════════════════════

const modes = [
  {
    id: 'exploit',
    name: 'EXPLOIT',
    icon: Zap,
    color: '#10B981',  // Green - high confidence
    threshold: 'Δ < 0.25 (τ_low)',
    triggers: ['Low divergence', 'Strong answer agreement', 'High-authority evidence'],
    description: 'Direct, confident answer from authoritative source',
    reason: 'Operators agree - we KNOW the answer',
    example: {
      query: 'What was Apple\'s total revenue in FY2023?',
      answer: 'Apple\'s total revenue for fiscal year 2023 was $383.29 billion, as reported in the audited financial statements.',
      confidence: 89,
      hops: 2,
      trust: 'TRUST_A (Structure-First)',
    },
  },
  {
    id: 'adaptive',
    name: 'ADAPTIVE',
    icon: Scale,
    color: '#F59E0B',  // Amber - balanced
    threshold: '0.25 ≤ Δ < 0.60',
    triggers: ['Medium divergence', 'Partial overlap', 'Causal queries'],
    description: 'Balanced analysis with nuanced context',
    reason: 'Operators partially agree - provide depth',
    example: {
      query: 'What factors drove iPhone revenue changes?',
      answer: 'iPhone revenue decreased from $394.33B to $383.29B in FY2023. Key factors include:\n• Market saturation in developed economies\n• Foreign exchange headwinds\n• Extended upgrade cycles...',
      confidence: 75,
      hops: 4,
      trust: 'MERGE_WEIGHTED',
    },
  },
  {
    id: 'explore',
    name: 'EXPLORE',
    icon: Search,
    color: '#EF4444',  // Red - high divergence/uncertainty
    threshold: 'Δ ≥ 0.60 (τ_high)',
    triggers: ['High divergence', 'Opinion query', 'Conflicting evidence'],
    description: 'Multiple perspectives presented for consideration',
    reason: 'Operators disagree - explore different viewpoints',
    example: {
      query: 'Is Apple\'s margin pressure cyclical or structural?',
      answer: '### Multiple Perspectives\n\n**Perspective A (Structure-First):**\nOperating margins show seasonal patterns...\n\n**Perspective B (Narrative-First):**\nCompetitive pressures suggest structural shift...',
      confidence: 45,
      hops: 4,
      trust: 'MERGE_EQUAL or CONFLICT',
    },
  },
];

// ═══════════════════════════════════════════════════════════════════════════
// Mode Visualizer Slider
// ═══════════════════════════════════════════════════════════════════════════

function ModeSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const getActiveMode = (v: number) => {
    if (v < 0.25) return 'exploit';
    if (v < 0.60) return 'adaptive';
    return 'explore';
  };

  const activeMode = getActiveMode(value);

  return (
    <div className="space-y-4">
      <div className="relative h-16">
        {/* Track */}
        <div className="absolute top-1/2 left-0 right-0 h-3 -translate-y-1/2 rounded-full overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-[#10B981] via-[#F59E0B] to-[#EF4444]" />
        </div>

        {/* Zone labels */}
        <div className="absolute top-full mt-2 left-0 right-0 flex">
          <div className="flex-1 text-center">
            <span className={`text-xs font-medium ${activeMode === 'exploit' ? 'text-[#10B981]' : 'text-[#6E6E73]'}`}>
              EXPLOIT
            </span>
          </div>
          <div className="flex-1 text-center">
            <span className={`text-xs font-medium ${activeMode === 'adaptive' ? 'text-[#F59E0B]' : 'text-[#6E6E73]'}`}>
              ADAPTIVE
            </span>
          </div>
          <div className="flex-1 text-center">
            <span className={`text-xs font-medium ${activeMode === 'explore' ? 'text-[#EF4444]' : 'text-[#6E6E73]'}`}>
              EXPLORE
            </span>
          </div>
        </div>

        {/* Threshold markers */}
        <div
          className="absolute top-0 bottom-0 w-px bg-white/50"
          style={{ left: '25%' }}
        >
          <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-[#6E6E73] whitespace-nowrap">
            τ_low = 0.25
          </span>
        </div>
        <div
          className="absolute top-0 bottom-0 w-px bg-white/50"
          style={{ left: '60%' }}
        >
          <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-[#6E6E73] whitespace-nowrap">
            τ_high = 0.60
          </span>
        </div>

        {/* Slider thumb */}
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white shadow-lg border-4 cursor-grab active:cursor-grabbing"
          style={{
            left: `calc(${value * 100}% - 16px)`,
            borderColor: activeMode === 'exploit' ? '#10B981' : activeMode === 'adaptive' ? '#F59E0B' : '#EF4444',
          }}
          drag="x"
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={0}
          onDrag={(_, info) => {
            const container = document.querySelector('.slider-container');
            if (container) {
              const rect = container.getBoundingClientRect();
              const newValue = Math.max(0, Math.min(1, (info.point.x - rect.left) / rect.width));
              onChange(newValue);
            }
          }}
        />

        {/* Input overlay */}
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="slider-container absolute inset-0 w-full opacity-0 cursor-pointer"
        />
      </div>

      <div className="text-center text-lg">
        <span className="text-[#6E6E73]">Δ = </span>
        <span className="font-bold">{value.toFixed(2)}</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Mode Card
// ═══════════════════════════════════════════════════════════════════════════

function ModeDetailCard({ mode, isActive }: { mode: typeof modes[0]; isActive: boolean }) {
  const Icon = mode.icon;

  return (
    <motion.div
      animate={{
        scale: isActive ? 1 : 0.95,
        opacity: isActive ? 1 : 0.5,
      }}
      className="bg-white rounded-2xl shadow-sm overflow-hidden transition-shadow"
      style={{
        boxShadow: isActive ? `0 20px 50px ${mode.color}25` : 'none',
      }}
    >
      {/* Header */}
      <div
        className="px-6 py-4"
        style={{ background: `linear-gradient(135deg, ${mode.color} 0%, ${mode.color}CC 100%)` }}
      >
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center gap-3">
            <Icon className="w-6 h-6" />
            <div>
              <div className="font-bold text-lg">{mode.name}</div>
              <div className="text-sm opacity-80">{mode.threshold}</div>
            </div>
          </div>
          {isActive && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center"
            >
              <Check className="w-5 h-5" />
            </motion.div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4">
        <div>
          <div className="text-sm font-medium text-[#6E6E73] mb-2">When triggered by:</div>
          <div className="flex flex-wrap gap-2">
            {mode.triggers.map((trigger) => (
              <span
                key={trigger}
                className="px-2 py-1 text-xs rounded-full"
                style={{ background: `${mode.color}15`, color: mode.color }}
              >
                {trigger}
              </span>
            ))}
          </div>
        </div>

        <div>
          <div className="text-sm font-medium text-[#6E6E73] mb-1">What happens:</div>
          <p className="font-medium">{mode.description}</p>
          <p className="text-sm text-[#6E6E73] mt-1">{mode.reason}</p>
        </div>

        {/* Example */}
        <div className="border-t border-[#F5F5F7] pt-4">
          <div className="text-sm font-medium text-[#6E6E73] mb-3">Example:</div>
          <div className="bg-[#F5F5F7] rounded-xl p-4">
            <div className="text-sm font-medium mb-2">Q: {mode.example.query}</div>
            <div className="text-sm text-[#6E6E73] whitespace-pre-line mb-3">
              A: {mode.example.answer.slice(0, 150)}...
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span>
                Confidence: <strong style={{ color: mode.color }}>{mode.example.confidence}%</strong>
              </span>
              <span>Hops: {mode.example.hops}</span>
              <span>Trust: {mode.example.trust}</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════════════════════

export default function ModeSelectionPage() {
  const [divergence, setDivergence] = useState(0.42);

  const getActiveMode = (v: number) => {
    if (v < 0.25) return 'exploit';
    if (v < 0.60) return 'adaptive';
    return 'explore';
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
            <div className="w-16 h-16 rounded-2xl bg-[#F59E0B]/10 flex items-center justify-center">
              <Scale className="w-8 h-8 text-[#F59E0B]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">Intelligent Mode Selection</h1>
              <p className="text-xl text-[#6E6E73] mt-1">The right answer, the right way</p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Intro */}
      <Section className="!pt-0">
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-lg text-[#6E6E73] max-w-3xl"
        >
          Based on divergence analysis, OpMech automatically selects the optimal response strategy for each query.
          This ensures users get the most appropriate type of answer based on how much the operators agree.
        </motion.p>
      </Section>

      {/* Interactive Mode Visualizer */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-4">Mode Selection Visualizer</h2>
        <p className="text-center text-[#6E6E73] max-w-2xl mx-auto mb-12">
          Drag the slider to see how divergence affects mode selection
        </p>

        <div className="max-w-3xl mx-auto mb-16">
          <ModeSlider value={divergence} onChange={setDivergence} />
        </div>

        {/* Mode Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {modes.map((mode) => (
            <ModeDetailCard
              key={mode.id}
              mode={mode}
              isActive={getActiveMode(divergence) === mode.id}
            />
          ))}
        </div>
      </Section>

      {/* Decision Flow */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-12">Decision Flow</h2>

        <div className="max-w-4xl mx-auto">
          <div className="relative">
            {/* Flow lines */}
            <div className="absolute left-8 top-12 bottom-12 w-0.5 bg-[#E5E7EB]" />

            {/* Steps */}
            {[
              { step: 1, title: 'Phase 1: Independent Exploration', desc: 'Both operators explore the graph independently at hop 1' },
              { step: 2, title: 'Compute Divergence', desc: 'Calculate Δ from components (Δ_E, Δ_V, Δ_A, Δ_C) after each hop' },
              { step: 3, title: 'Phase 2: Convergence-Aware', desc: 'From hop 2+, operators share evidence to guide convergence' },
              { step: 4, title: 'Check Thresholds', desc: 'Compare Δ against τ_low (0.25) and τ_high (0.60)' },
              { step: 5, title: 'Select Mode', desc: 'Choose EXPLOIT, ADAPTIVE, or EXPLORE based on final divergence' },
              { step: 6, title: 'Generate Response', desc: 'Format answer with trust decision (TRUST_A, TRUST_B, MERGE, CONFLICT)' },
            ].map((item, idx) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                className="relative flex items-start gap-6 mb-8"
              >
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center text-white font-bold text-xl flex-shrink-0 z-10">
                  {item.step}
                </div>
                <div className="pt-3">
                  <h3 className="font-bold text-lg">{item.title}</h3>
                  <p className="text-[#6E6E73]">{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="bg-[#F5F5F7] !py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/features/commutator"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            The Commutator
          </Link>
          <Link
            href="/features/trust-decision"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: Trust Decision
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
