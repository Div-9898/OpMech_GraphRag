'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  Clock,
  Target,
  Zap,
  Award,
  ArrowRight,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';
import { useState, useEffect } from 'react';

// Performance Metrics
const performanceMetrics = [
  {
    label: 'Answer Accuracy',
    value: 94.2,
    unit: '%',
    change: +3.8,
    benchmark: 87.4,
    description: 'Correctness on FinQA benchmark',
  },
  {
    label: 'Response Time',
    value: 1.8,
    unit: 's',
    change: -0.4,
    benchmark: 2.5,
    description: 'Average query-to-answer latency',
  },
  {
    label: 'Evidence Recall',
    value: 91.7,
    unit: '%',
    change: +5.2,
    benchmark: 82.3,
    description: 'Relevant evidence retrieval rate',
  },
  {
    label: 'Hallucination Rate',
    value: 2.1,
    unit: '%',
    change: -1.9,
    benchmark: 8.7,
    description: 'False information in responses',
  },
];

// Comparison Data
const comparisonData = [
  {
    metric: 'Numerical Accuracy',
    opmech: 96.4,
    baseline: 78.2,
    improvement: '+18.2%',
  },
  {
    metric: 'Multi-hop Reasoning',
    opmech: 89.1,
    baseline: 61.5,
    improvement: '+27.6%',
  },
  {
    metric: 'Evidence Attribution',
    opmech: 94.8,
    baseline: 45.3,
    improvement: '+49.5%',
  },
  {
    metric: 'Context Utilization',
    opmech: 91.2,
    baseline: 72.8,
    improvement: '+18.4%',
  },
];

// Mode Distribution
const modeDistribution = [
  { mode: 'EXPLOIT', percentage: 45, color: '#10B981', desc: 'High confidence, single source' },
  { mode: 'ADAPTIVE', percentage: 35, color: '#F59E0B', desc: 'Moderate divergence, weighted merge' },
  { mode: 'EXPLORE', percentage: 20, color: '#EF4444', desc: 'High divergence, comprehensive search' },
];

// Animated Counter Component
function AnimatedValue({
  value,
  unit,
  duration = 1.5,
}: {
  value: number;
  unit: string;
  duration?: number;
}) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(value * eased);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [value, duration]);

  return (
    <span>
      {displayValue.toFixed(1)}
      {unit}
    </span>
  );
}

// Metric Card Component
function MetricCard({
  metric,
  index,
}: {
  metric: (typeof performanceMetrics)[0];
  index: number;
}) {
  const isPositive = metric.label === 'Hallucination Rate' ? metric.change < 0 : metric.change > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1 }}
      className="bg-white rounded-2xl p-6 shadow-sm border border-[#E5E7EB]"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-sm text-[#6E6E73] mb-1">{metric.label}</div>
          <div className="text-4xl font-bold">
            <AnimatedValue value={metric.value} unit={metric.unit} />
          </div>
        </div>
        <div
          className={`flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${
            isPositive ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-[#EF4444]/10 text-[#EF4444]'
          }`}
        >
          {isPositive ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
          {Math.abs(metric.change)}
          {metric.unit}
        </div>
      </div>

      <div className="text-sm text-[#6E6E73] mb-3">{metric.description}</div>

      {/* Comparison bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span>vs. Baseline ({metric.benchmark}{metric.unit})</span>
          <span className="text-[#667EEA] font-medium">
            {((metric.value / metric.benchmark - 1) * 100).toFixed(0)}% better
          </span>
        </div>
        <div className="h-2 bg-[#F5F5F7] rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            whileInView={{ width: `${(metric.value / Math.max(metric.value, metric.benchmark)) * 100}%` }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: 0.5 }}
            className="h-full bg-gradient-to-r from-[#667EEA] to-[#764BA2] rounded-full"
          />
        </div>
      </div>
    </motion.div>
  );
}

// Bar Chart Component
function ComparisonChart() {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#E5E7EB]">
      <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-[#667EEA]" />
        OpMech vs. Baseline RAG
      </h3>

      <div className="space-y-6">
        {comparisonData.map((item, idx) => (
          <motion.div
            key={item.metric}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: idx * 0.1 }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{item.metric}</span>
              <span className="text-sm text-[#10B981] font-medium">
                {item.improvement}
              </span>
            </div>
            <div className="relative h-8 flex gap-1">
              {/* OpMech bar */}
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${item.opmech}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: idx * 0.1 }}
                className="h-full bg-gradient-to-r from-[#667EEA] to-[#764BA2] rounded-lg flex items-center justify-end pr-2"
              >
                <span className="text-xs text-white font-medium">
                  {item.opmech}%
                </span>
              </motion.div>
            </div>
            <div className="relative h-6 flex gap-1 mt-1">
              {/* Baseline bar */}
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${item.baseline}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: idx * 0.1 + 0.2 }}
                className="h-full bg-[#E5E7EB] rounded-lg flex items-center justify-end pr-2"
              >
                <span className="text-xs text-[#6E6E73] font-medium">
                  {item.baseline}%
                </span>
              </motion.div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="flex items-center gap-6 mt-6 pt-4 border-t border-[#E5E7EB]">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-gradient-to-r from-[#667EEA] to-[#764BA2]" />
          <span className="text-sm text-[#6E6E73]">OpMech-GraphRAG</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-[#E5E7EB]" />
          <span className="text-sm text-[#6E6E73]">Baseline RAG</span>
        </div>
      </div>
    </div>
  );
}

// Mode Distribution Chart
function ModeDistributionChart() {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#E5E7EB]">
      <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
        <Target className="w-5 h-5 text-[#667EEA]" />
        Mode Selection Distribution
      </h3>

      <div className="flex items-center gap-6 mb-6">
        {/* Pie chart visualization */}
        <div className="relative w-32 h-32">
          <svg viewBox="0 0 100 100" className="transform -rotate-90">
            {(() => {
              let cumulativePercentage = 0;
              return modeDistribution.map((mode, idx) => {
                const strokeDasharray = `${mode.percentage} ${100 - mode.percentage}`;
                const strokeDashoffset = -cumulativePercentage;
                cumulativePercentage += mode.percentage;

                return (
                  <motion.circle
                    key={mode.mode}
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke={mode.color}
                    strokeWidth="20"
                    strokeDasharray={strokeDasharray}
                    strokeDashoffset={strokeDashoffset}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.2 }}
                    pathLength="100"
                  />
                );
              });
            })()}
          </svg>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-3">
          {modeDistribution.map((mode) => (
            <div key={mode.mode} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ background: mode.color }}
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{mode.mode}</span>
                  <span className="text-sm text-[#6E6E73]">
                    {mode.percentage}%
                  </span>
                </div>
                <div className="text-xs text-[#6E6E73]">{mode.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Main Page
export default function MetricsPage() {
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
              <BarChart3 className="w-8 h-8 text-[#667EEA]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">
                Performance Metrics
              </h1>
              <p className="text-xl text-[#6E6E73] mt-1">
                Benchmarks and system performance analysis
              </p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Key Metrics Grid */}
      <Section className="!pt-0">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {performanceMetrics.map((metric, idx) => (
            <MetricCard key={metric.label} metric={metric} index={idx} />
          ))}
        </div>
      </Section>

      {/* Comparison Section */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-4">
          Benchmark Comparison
        </h2>
        <p className="text-center text-[#6E6E73] mb-12 max-w-2xl mx-auto">
          OpMech-GraphRAG significantly outperforms traditional RAG approaches
          across key financial QA metrics.
        </p>

        <div className="grid lg:grid-cols-2 gap-8">
          <ComparisonChart />
          <ModeDistributionChart />
        </div>
      </Section>

      {/* Key Achievements */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-12">
          Key Achievements
        </h2>

        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {[
            {
              icon: Award,
              title: 'FinQA Benchmark',
              value: '94.2%',
              desc: 'Accuracy on financial question answering',
              color: '#10B981',
            },
            {
              icon: Clock,
              title: 'Sub-2s Latency',
              value: '1.8s',
              desc: 'Average response time with full graph traversal',
              color: '#3B82F6',
            },
            {
              icon: Zap,
              title: 'Real-time Updates',
              value: '<100ms',
              desc: 'Graph visualization update latency',
              color: '#F59E0B',
            },
          ].map((achievement, idx) => {
            const Icon = achievement.icon;
            return (
              <motion.div
                key={achievement.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                className="text-center p-6"
              >
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
                  style={{ background: `${achievement.color}15` }}
                >
                  <Icon
                    className="w-8 h-8"
                    style={{ color: achievement.color }}
                  />
                </div>
                <div
                  className="text-4xl font-bold mb-2"
                  style={{ color: achievement.color }}
                >
                  {achievement.value}
                </div>
                <div className="font-medium mb-1">{achievement.title}</div>
                <div className="text-sm text-[#6E6E73]">{achievement.desc}</div>
              </motion.div>
            );
          })}
        </div>
      </Section>

      {/* CTA Section */}
      <Section className="bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">See It In Action</h2>
          <p className="text-xl opacity-90 mb-8">
            Try the interactive demo to see how OpMech-GraphRAG handles real
            financial queries with full transparency into the reasoning process.
          </p>
          <Link
            href="/demo"
            className="inline-flex items-center gap-2 px-8 py-4 bg-white text-[#667EEA] rounded-full font-semibold hover:shadow-lg transition-all"
          >
            <TrendingUp className="w-5 h-5" />
            Launch Interactive Demo
          </Link>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/architecture"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Architecture
          </Link>
          <Link
            href="/team"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Next: Meet the Team
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
