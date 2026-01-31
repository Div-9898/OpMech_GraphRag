'use client';

import Link from 'next/link';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  AlertTriangle,
  Cpu,
  Activity,
  Target,
  Zap,
  Lightbulb,
  ChevronRight,
  Info,
  TrendingDown,
  Clock,
  Layers,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// LIMITATIONS PAGE - Matching Frontend Design System
// Clean, Apple-inspired aesthetic with honest engineering transparency
// ═══════════════════════════════════════════════════════════════════════════

// Animated Token Gauge (matching commutator gauge style)
function TokenGauge({ size = 200 }: { size?: number }) {
  const maxTokens = 4096;
  const usedTokens = 3847;
  const percentage = usedTokens / maxTokens;

  const springValue = useSpring(0, { stiffness: 50, damping: 20 });
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    springValue.set(percentage);
    return springValue.on('change', (v) => setDisplayValue(v));
  }, [springValue, percentage]);

  const getColor = (v: number) => {
    if (v < 0.7) return '#10B981';
    if (v < 0.9) return '#F59E0B';
    return '#EF4444';
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

        {/* Overflow threshold marker */}
        <circle
          cx="100"
          cy="100"
          r="80"
          fill="none"
          stroke="#FEE2E2"
          strokeWidth="16"
          strokeDasharray={`${circumference * 0.75 * 0.1} ${circumference}`}
          strokeDashoffset={-circumference * 0.75 * 0.9}
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
        <span className="text-3xl font-bold" style={{ color: getColor(displayValue) }}>
          {Math.round(displayValue * maxTokens).toLocaleString()}
        </span>
        <span className="text-sm text-[#6E6E73] mt-1">/ {maxTokens.toLocaleString()} tokens</span>
      </div>
    </div>
  );
}

// Progress Bar Component
function ProgressBar({
  label,
  value,
  maxValue,
  color,
  showOverflow = false,
}: {
  label: string;
  value: number;
  maxValue: number;
  color: string;
  showOverflow?: boolean;
}) {
  const percentage = (value / maxValue) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[#6E6E73]">{label}</span>
        <span className="font-mono font-medium">{value.toLocaleString()}</span>
      </div>
      <div className="relative h-3 bg-[#F5F5F7] rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${Math.min(percentage, 100)}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ background: color }}
        />
        {showOverflow && (
          <div className="absolute top-0 bottom-0 right-[10%] w-0.5 bg-[#EF4444]" />
        )}
      </div>
    </div>
  );
}

// Hop Visualization Component
function HopVisualization() {
  const hops = [
    { hop: 1, delta: 0.78 },
    { hop: 2, delta: 0.65 },
    { hop: 3, delta: 0.52 },
    { hop: 4, delta: 0.41 },
    { hop: 5, delta: 0.33 },
    { hop: 6, delta: 0.28 },
  ];

  const idealStop = 4;
  const threshold = 0.25;

  return (
    <div className="bg-white rounded-2xl p-6 border border-black/5">
      <div className="flex items-center justify-between mb-6">
        <h4 className="font-semibold text-[#1D1D1F]">Hop Trajectory Example</h4>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#10B981]" />
            <span className="text-[#6E6E73]">Ideal Stop</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
            <span className="text-[#6E6E73]">Hard Stop</span>
          </div>
        </div>
      </div>

      <div className="relative h-48">
        {/* Threshold line */}
        <div
          className="absolute left-0 right-0 border-t-2 border-dashed border-[#10B981]/50"
          style={{ top: `${(1 - threshold) * 100}%` }}
        >
          <span className="absolute -top-5 left-0 text-xs text-[#10B981] font-mono">
            Δ = 0.25 (threshold)
          </span>
        </div>

        {/* Bars */}
        <div className="absolute inset-0 flex items-end justify-between gap-4 pt-8">
          {hops.map((hop, idx) => {
            const isIdeal = idx === idealStop - 1;
            const isHardStop = idx === hops.length - 1;
            const color = isHardStop
              ? '#EF4444'
              : isIdeal
              ? '#10B981'
              : '#3B82F6';

            return (
              <motion.div
                key={hop.hop}
                initial={{ height: 0 }}
                whileInView={{ height: `${hop.delta * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className="relative flex-1 rounded-t-lg"
                style={{ background: `linear-gradient(to top, ${color}, ${color}90)` }}
              >
                {/* Delta value */}
                <div
                  className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-mono"
                  style={{ color }}
                >
                  {hop.delta.toFixed(2)}
                </div>

                {/* Hop label */}
                <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-[#6E6E73]">
                  H{hop.hop}
                </div>

                {/* Markers */}
                {isIdeal && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.8 }}
                    className="absolute -top-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-semibold text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded-full"
                  >
                    IDEAL
                  </motion.div>
                )}
                {isHardStop && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 1 }}
                    className="absolute -top-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-semibold text-[#EF4444] bg-[#EF4444]/10 px-2 py-0.5 rounded-full"
                  >
                    HARD STOP
                  </motion.div>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="mt-12 p-4 bg-[#FEF3C7] rounded-xl flex items-start gap-3">
        <Info className="w-5 h-5 text-[#D97706] flex-shrink-0 mt-0.5" />
        <p className="text-sm text-[#92400E]">
          Query continued 2 hops beyond optimal convergence point, wasting compute.
        </p>
      </div>
    </div>
  );
}

// Limitation Card Component
function LimitationCard({
  number,
  title,
  severity,
  icon: Icon,
  color,
  children,
}: {
  number: string;
  title: string;
  severity: 'critical' | 'moderate';
  icon: React.ElementType;
  color: string;
  children: React.ReactNode;
}) {
  const severityConfig = {
    critical: {
      bg: 'bg-[#FEE2E2]',
      text: 'text-[#DC2626]',
      label: 'Critical',
    },
    moderate: {
      bg: 'bg-[#FEF3C7]',
      text: 'text-[#D97706]',
      label: 'Moderate',
    },
  };

  const config = severityConfig[severity];

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="bg-white rounded-3xl border border-black/5 shadow-sm hover:shadow-lg transition-shadow overflow-hidden"
    >
      {/* Header */}
      <div className="px-8 py-6 border-b border-black/5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{ background: `${color}15` }}
            >
              <Icon className="w-7 h-7" style={{ color }} />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-sm font-mono text-[#6E6E73]">#{number}</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${config.bg} ${config.text}`}>
                  {config.label}
                </span>
              </div>
              <h3 className="text-xl font-bold text-[#1D1D1F]">{title}</h3>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-8">{children}</div>
    </motion.div>
  );
}

// Impact Item
function ImpactItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <ChevronRight className="w-4 h-4 text-[#EF4444] flex-shrink-0 mt-1" />
      <span className="text-[#1D1D1F]">{children}</span>
    </div>
  );
}

// Ideal Stop Condition Card
function IdealCondition({
  queryType,
  condition,
  color,
}: {
  queryType: string;
  condition: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-4 p-4 bg-[#F5F5F7] rounded-xl">
      <Target className="w-5 h-5 flex-shrink-0" style={{ color }} />
      <div>
        <span className="text-xs font-semibold text-[#6E6E73] uppercase tracking-wider">
          {queryType}
        </span>
        <p className="text-sm text-[#1D1D1F] font-medium mt-0.5">{condition}</p>
      </div>
    </div>
  );
}

// Proposed Fix Card
function ProposedFix({
  title,
  description,
  priority,
  icon: Icon,
  color,
}: {
  title: string;
  description: string;
  priority: 'high' | 'medium';
  icon: React.ElementType;
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="bg-white rounded-2xl p-6 border border-black/5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-4">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: `${color}15` }}
        >
          <Icon className="w-6 h-6" style={{ color }} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="font-semibold text-[#1D1D1F]">{title}</h4>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                priority === 'high'
                  ? 'bg-[#EF4444]/10 text-[#EF4444]'
                  : 'bg-[#F59E0B]/10 text-[#F59E0B]'
              }`}
            >
              {priority} priority
            </span>
          </div>
          <p className="text-sm text-[#6E6E73]">{description}</p>
        </div>
      </div>
    </motion.div>
  );
}

// Main Page Component
export default function LimitationsPage() {
  return (
    <PageWrapper>
      {/* Hero Section */}
      <Section className="pt-24 pb-12">
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
          className="max-w-3xl"
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 rounded-2xl bg-[#F59E0B]/10 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-[#F59E0B]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
                <span className="gradient-text">Known Limitations</span>
              </h1>
              <p className="text-lg text-[#6E6E73] mt-1">
                Transparency in engineering
              </p>
            </div>
          </div>

          <p className="text-lg text-[#6E6E73] leading-relaxed">
            The following limitations have been identified during development and testing.
            We document them openly to support reproducibility and collaborative improvement.
          </p>
        </motion.div>
      </Section>

      {/* Limitation 1: Context Window */}
      <Section className="!pt-0">
        <LimitationCard
          number="01"
          title="Context Window Constraint"
          severity="critical"
          icon={Cpu}
          color="#EF4444"
        >
          <div className="grid lg:grid-cols-2 gap-8">
            <div>
              <p className="text-[#6E6E73] mb-6">
                The <span className="font-semibold text-[#1D1D1F]">Qwen2.5-7B</span> model
                operates with a <span className="font-semibold text-[#EF4444]">4,096 token</span> context
                limit. When combining operator evidence, ground truth injection, and instructions,
                context overflow occurs.
              </p>

              <div className="space-y-4 mb-6">
                <ProgressBar label="Evidence A" value={1847} maxValue={4096} color="#3B82F6" />
                <ProgressBar label="Evidence B" value={1432} maxValue={4096} color="#10B981" />
                <ProgressBar label="Instructions" value={568} maxValue={4096} color="#8B5CF6" />
                <div className="pt-2 border-t border-[#E5E7EB]">
                  <ProgressBar
                    label="Total"
                    value={3847}
                    maxValue={4096}
                    color="#EF4444"
                    showOverflow
                  />
                </div>
              </div>

              <h4 className="font-semibold text-[#1D1D1F] mb-3">Symptoms</h4>
              <div className="space-y-1">
                <ImpactItem>Truncated responses mid-sentence</ImpactItem>
                <ImpactItem>Ground truth values pushed out of context window</ImpactItem>
                <ImpactItem>Hallucinated financial figures when XBRL data unavailable</ImpactItem>
              </div>
            </div>

            <div className="flex flex-col items-center justify-center">
              <TokenGauge size={220} />
              <div className="mt-6 p-4 bg-[#FEE2E2] rounded-xl text-center max-w-xs">
                <p className="text-sm font-semibold text-[#DC2626]">
                  Impact: Values off by 3-7x from actual XBRL data
                </p>
              </div>
            </div>
          </div>
        </LimitationCard>
      </Section>

      {/* Limitation 2: Fixed Hop Limit */}
      <Section className="!pt-8">
        <LimitationCard
          number="02"
          title="Fixed Hop Limit"
          severity="moderate"
          icon={Activity}
          color="#F59E0B"
        >
          <div className="space-y-6">
            <p className="text-[#6E6E73]">
              The system hard-stops at <span className="font-semibold text-[#F59E0B]">6 hops</span> regardless
              of convergence status. Ideally, stopping conditions should be adaptive based on query type.
            </p>

            <div>
              <h4 className="font-semibold text-[#1D1D1F] mb-4">Ideal Stopping Conditions</h4>
              <div className="grid md:grid-cols-3 gap-4">
                <IdealCondition
                  queryType="Factual Query"
                  condition="Stop when Δ < 0.25 (converged)"
                  color="#10B981"
                />
                <IdealCondition
                  queryType="Opinion Query"
                  condition="Stop when trajectory stabilizes"
                  color="#3B82F6"
                />
                <IdealCondition
                  queryType="Causal Query"
                  condition="Stop when both evidence types found"
                  color="#8B5CF6"
                />
              </div>
            </div>

            <HopVisualization />

            <div className="p-4 bg-[#FEF3C7] rounded-xl">
              <p className="text-sm text-[#92400E]">
                <span className="font-semibold">Impact:</span> Some queries terminate before optimal
                convergence; others continue unnecessarily, wasting compute and potentially degrading
                answer quality.
              </p>
            </div>
          </div>
        </LimitationCard>
      </Section>

      {/* Proposed Fixes */}
      <Section className="bg-[#F5F5F7]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#667EEA]/10 to-[#764BA2]/10 rounded-full mb-4">
            <Lightbulb className="w-4 h-4 text-[#667EEA]" />
            <span className="text-sm font-semibold text-[#667EEA]">Roadmap</span>
          </div>
          <h2 className="text-3xl font-bold text-[#1D1D1F]">Proposed Fixes</h2>
          <p className="text-[#6E6E73] mt-2">Active areas of research and development</p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          <ProposedFix
            title="Context Extension"
            description="Upgrade to Qwen2.5-7B-Instruct with 32K context window, or implement sliding window attention for evidence chunking."
            priority="high"
            icon={Cpu}
            color="#3B82F6"
          />
          <ProposedFix
            title="Adaptive Stopping"
            description="Implement query-type-aware stopping conditions using trajectory analysis and convergence detection algorithms."
            priority="medium"
            icon={Activity}
            color="#8B5CF6"
          />
          <ProposedFix
            title="Evidence Pruning"
            description="Context-aware evidence selection to prioritize high-relevance content and reduce token usage."
            priority="high"
            icon={Layers}
            color="#10B981"
          />
          <ProposedFix
            title="Importance Scoring"
            description="Add evidence importance scoring to ensure critical XBRL data is never truncated from context."
            priority="medium"
            icon={Target}
            color="#F59E0B"
          />
        </div>
      </Section>

      {/* Closing */}
      <Section>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-2xl mx-auto text-center"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#10B981]/10 rounded-full mb-6">
            <Zap className="w-4 h-4 text-[#10B981]" />
            <span className="text-sm font-semibold text-[#10B981]">Open Research</span>
          </div>

          <p className="text-lg text-[#6E6E73] leading-relaxed mb-8">
            These limitations represent active areas of research. We document them openly to
            support reproducibility and collaborative improvement.
          </p>

          <p className="text-[#6E6E73] italic">
            &ldquo;Knowing your system&apos;s boundaries is the first step to expanding them.&rdquo;
          </p>
        </motion.div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <Link
            href="/metrics"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Metrics
          </Link>
          <Link
            href="/demo"
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white rounded-full font-semibold hover:shadow-lg transition-all"
          >
            Try Demo
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
