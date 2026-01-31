'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import type { DivergenceComponents } from '@/types';
import AnimatedNumber from '@/components/shared/AnimatedNumber';

interface CommutatorGaugeProps {
  delta: number;
  deltaComponents: DivergenceComponents;
  isAnimating?: boolean;
  size?: number;
  showComponents?: boolean;
  className?: string;
}

export default function CommutatorGauge({
  delta,
  deltaComponents,
  isAnimating = false,
  size = 200,
  showComponents = true,
  className = '',
}: CommutatorGaugeProps) {
  // Calculate stroke properties
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(delta, 1);
  const strokeDashoffset = circumference * (1 - progress);

  // Get color based on delta value
  const getColor = (value: number) => {
    if (value < 0.3) return { main: '#10B981', glow: 'rgba(16, 185, 129, 0.4)' };
    if (value < 0.6) return { main: '#F59E0B', glow: 'rgba(245, 158, 11, 0.4)' };
    return { main: '#EF4444', glow: 'rgba(239, 68, 68, 0.4)' };
  };

  const colors = useMemo(() => getColor(delta), [delta]);

  // Component data for breakdown bars
  const components = [
    { key: 'delta_E', label: 'Evidence', value: deltaComponents.delta_E, color: '#3B82F6' },
    { key: 'delta_V', label: 'Structure', value: deltaComponents.delta_V, color: '#8B5CF6' },
    { key: 'delta_A', label: 'Answer', value: deltaComponents.delta_A, color: '#10B981' },
    { key: 'delta_C', label: 'Confidence', value: deltaComponents.delta_C, color: '#F59E0B' },
  ];

  return (
    <div className={`flex flex-col items-center gap-6 ${className}`}>
      {/* Main circular gauge */}
      <div className="relative" style={{ width: size, height: size }}>
        {/* SVG Gauge */}
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90"
        >
          {/* Gradient definition */}
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#EF4444" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(0, 0, 0, 0.08)"
            strokeWidth={strokeWidth}
          />

          {/* Progress circle */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.main}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            filter="url(#glow)"
          />
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="text-4xl font-bold tabular-nums"
            style={{ color: colors.main }}
            animate={isAnimating ? { scale: [1, 1.05, 1] } : undefined}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <AnimatedNumber value={delta} decimals={3} duration={800} />
          </motion.span>
          <span className="text-sm text-[#6E6E73] mt-1">Divergence (Δ)</span>
        </div>

        {/* Animated pulse ring when processing */}
        {isAnimating && (
          <motion.div
            className="absolute inset-0 rounded-full border-2"
            style={{ borderColor: colors.glow }}
            animate={{
              scale: [1, 1.1, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </div>

      {/* Commutator formula */}
      <div className="text-center">
        <span className="font-mono text-lg text-[#6E6E73]">[A, B] = AB - BA ≠ 0</span>
      </div>

      {/* Component breakdown */}
      {showComponents && (
        <div className="w-full max-w-xs space-y-3">
          {components.map((comp, index) => (
            <motion.div
              key={comp.key}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <div className="flex justify-between text-sm mb-1">
                <span className="text-[#6E6E73]">Δ_{comp.label.charAt(0)}</span>
                <span className="font-mono" style={{ color: comp.color }}>
                  {comp.value.toFixed(2)}
                </span>
              </div>
              <div className="h-2 bg-black/5 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: comp.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${comp.value * 100}%` }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                />
              </div>
            </motion.div>
          ))}

          {/* Combined divergence bar */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="pt-3 mt-3 border-t border-black/10"
          >
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-[#1D1D1F]">Combined Δ</span>
              <span className="font-mono font-bold" style={{ color: colors.main }}>
                {delta.toFixed(3)}
              </span>
            </div>
            <div className="h-3 bg-black/5 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{
                  background: 'linear-gradient(90deg, #10B981 0%, #F59E0B 50%, #EF4444 100%)',
                  backgroundSize: '200% 100%',
                  backgroundPosition: `${delta * 100}% 0`,
                }}
                initial={{ width: 0 }}
                animate={{ width: `${delta * 100}%` }}
                transition={{ duration: 0.8 }}
              />
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

// Compact version for inline display
export function CommutatorGaugeCompact({
  delta,
  className = '',
}: {
  delta: number;
  className?: string;
}) {
  const getColor = (value: number) => {
    if (value < 0.3) return '#10B981';
    if (value < 0.6) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-sm text-[#6E6E73]">Δ:</span>
      <div className="flex items-center gap-1">
        <div className="w-16 h-2 bg-black/5 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: getColor(delta) }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(delta, 1) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <span
          className="font-mono text-sm font-medium"
          style={{ color: getColor(delta) }}
        >
          {delta.toFixed(3)}
        </span>
      </div>
    </div>
  );
}
