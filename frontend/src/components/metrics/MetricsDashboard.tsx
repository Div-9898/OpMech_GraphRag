'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { AnimatedCounter, AnimatedPercentage } from '@/components/shared/AnimatedNumber';
import DivergenceChart from './DivergenceChart';
import EvidenceBreakdown from './EvidenceBreakdown';

interface MetricsDashboardProps {
  className?: string;
}

export default function MetricsDashboard({ className = '' }: MetricsDashboardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section ref={ref} className={`py-24 bg-white ${className}`}>
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-[#1D1D1F] mb-4">
            Performance Metrics
          </h2>
          <p className="text-xl text-[#6E6E73] max-w-2xl mx-auto">
            Real-time performance tracking across all query dimensions
          </p>
        </motion.div>

        {/* Top metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <MetricCard
            title="Mode Accuracy"
            value={100}
            subtitle="3/3 correct"
            color="#10B981"
            delay={0.2}
            isInView={isInView}
          />
          <MetricCard
            title="Answer Quality"
            value={100}
            subtitle="3/3 correct"
            color="#3B82F6"
            delay={0.3}
            isInView={isInView}
          />
          <MetricCard
            title="Trust Accuracy"
            value={100}
            subtitle="3/3 correct"
            color="#8B5CF6"
            delay={0.4}
            isInView={isInView}
          />
        </div>

        {/* Charts row */}
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Divergence over hops */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.5 }}
            className="glass-card p-6"
          >
            <h3 className="text-xl font-bold text-[#1D1D1F] mb-6">
              Divergence Over Hops
            </h3>
            <DivergenceChart />
          </motion.div>

          {/* Evidence & Traversal */}
          <div className="space-y-6">
            {/* Evidence Distribution */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.6 }}
              className="glass-card p-6"
            >
              <h3 className="text-xl font-bold text-[#1D1D1F] mb-6">
                Evidence Distribution
              </h3>
              <EvidenceBreakdown />
            </motion.div>

            {/* Traversal Efficiency */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.7 }}
              className="glass-card p-6"
            >
              <h3 className="text-xl font-bold text-[#1D1D1F] mb-4">
                Traversal Efficiency
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-[#6E6E73]">Before optimization:</span>
                  <span className="font-mono font-bold text-[#1D1D1F]">
                    <AnimatedCounter value={1134} /> nodes
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#6E6E73]">After optimization:</span>
                  <span className="font-mono font-bold text-[#10B981]">
                    <AnimatedCounter value={76} /> nodes
                  </span>
                </div>
                <div className="h-px bg-black/10" />
                <div className="flex justify-between items-center">
                  <span className="text-[#6E6E73]">Reduction:</span>
                  <span className="font-mono font-bold text-[#10B981]">93%</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-[#6E6E73]">No edge caps hit</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-[#6E6E73]">Smart scoring enabled</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  color,
  delay,
  isInView,
}: {
  title: string;
  value: number;
  subtitle: string;
  color: string;
  delay: number;
  isInView: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay }}
      className="metric-card"
    >
      <div className="metric-value" style={{ color }}>
        {isInView ? <AnimatedPercentage value={value / 100} duration={1500} /> : '0%'}
      </div>
      <h3 className="text-lg font-semibold text-[#1D1D1F] mt-2">{title}</h3>
      <p className="metric-label">{subtitle}</p>

      {/* Progress bar */}
      <div className="mt-4 h-2 bg-black/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={isInView ? { width: `${value}%` } : { width: 0 }}
          transition={{ delay: delay + 0.3, duration: 1 }}
        />
      </div>
    </motion.div>
  );
}
