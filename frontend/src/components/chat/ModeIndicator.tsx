'use client';

import { motion, AnimatePresence } from 'framer-motion';
import type { ModeType } from '@/types';
import { getModeLabel, getModeDescription, getModeIcon } from '@/utils/formatters';
import { AnimatedPercentage } from '@/components/shared/AnimatedNumber';

interface ModeIndicatorProps {
  mode: ModeType;
  confidence: number;
  isTransitioning?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showDescription?: boolean;
  className?: string;
}

const modeConfig = {
  EXPLOIT: {
    gradient: 'from-blue-500 to-blue-600',
    bgGradient: 'from-blue-500/10 to-blue-600/10',
    border: 'border-blue-500/30',
    shadow: 'shadow-[0_0_20px_rgba(59,130,246,0.3)]',
    textColor: 'text-blue-600',
    icon: '⚡',
  },
  ADAPTIVE: {
    gradient: 'from-amber-500 to-orange-500',
    bgGradient: 'from-amber-500/10 to-orange-500/10',
    border: 'border-amber-500/30',
    shadow: 'shadow-[0_0_20px_rgba(245,158,11,0.3)]',
    textColor: 'text-amber-600',
    icon: '⚖️',
  },
  EXPLORE: {
    gradient: 'from-purple-500 to-violet-600',
    bgGradient: 'from-purple-500/10 to-violet-600/10',
    border: 'border-purple-500/30',
    shadow: 'shadow-[0_0_20px_rgba(139,92,246,0.3)]',
    textColor: 'text-purple-600',
    icon: '🔍',
  },
};

export default function ModeIndicator({
  mode,
  confidence,
  isTransitioning = false,
  size = 'md',
  showDescription = true,
  className = '',
}: ModeIndicatorProps) {
  // Normalize mode to uppercase and provide fallback
  const normalizedMode = (mode?.toUpperCase?.() || 'ADAPTIVE') as ModeType;
  const config = modeConfig[normalizedMode] || modeConfig.ADAPTIVE;

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={normalizedMode}
        className={`relative ${className}`}
        initial={{ opacity: 0, scale: 0.9, rotateY: -90 }}
        animate={{ opacity: 1, scale: 1, rotateY: 0 }}
        exit={{ opacity: 0, scale: 0.9, rotateY: 90 }}
        transition={{
          duration: 0.4,
          ease: [0.4, 0, 0.2, 1],
        }}
      >
        {/* Main badge */}
        <div
          className={`
            relative overflow-hidden rounded-full
            bg-gradient-to-r ${config.bgGradient}
            border ${config.border}
            ${config.shadow}
            ${sizeClasses[size]}
            flex items-center gap-2
          `}
        >
          {/* Icon */}
          <motion.span
            className="text-lg"
            animate={isTransitioning ? { rotate: [0, 360] } : undefined}
            transition={{ duration: 0.5 }}
          >
            {config.icon}
          </motion.span>

          {/* Mode name */}
          <span className={`font-semibold ${config.textColor} uppercase tracking-wide`}>
            {normalizedMode}
          </span>

          {/* Confidence */}
          <span className={`font-mono font-bold ${config.textColor}`}>
            <AnimatedPercentage value={confidence} duration={500} />
          </span>

          {/* Animated shine effect */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            initial={{ x: '-100%' }}
            animate={{ x: '100%' }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              repeatDelay: 3,
            }}
          />
        </div>

        {/* Description tooltip */}
        {showDescription && (
          <motion.div
            className="absolute top-full left-1/2 -translate-x-1/2 mt-2 whitespace-nowrap"
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <span className="text-xs text-[#6E6E73]">{getModeDescription(normalizedMode)}</span>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

// Mode selector card for feature showcase
export function ModeCard({
  mode,
  isActive = false,
  onClick,
  className = '',
}: {
  mode: ModeType;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  const normalizedMode = (mode?.toUpperCase?.() || 'ADAPTIVE') as ModeType;
  const config = modeConfig[normalizedMode] || modeConfig.ADAPTIVE;

  return (
    <motion.button
      onClick={onClick}
      className={`
        relative p-6 rounded-2xl text-left transition-all
        ${isActive ? `bg-gradient-to-br ${config.bgGradient} ${config.shadow}` : 'bg-white/50'}
        border ${isActive ? config.border : 'border-black/5'}
        hover:scale-105
        ${className}
      `}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Icon */}
      <div className="text-4xl mb-4">{config.icon}</div>

      {/* Mode name */}
      <h3 className={`text-xl font-bold mb-2 ${isActive ? config.textColor : 'text-[#1D1D1F]'}`}>
        {normalizedMode}
      </h3>

      {/* Description */}
      <p className="text-sm text-[#6E6E73]">{getModeDescription(normalizedMode)}</p>

      {/* Active indicator */}
      {isActive && (
        <motion.div
          className={`absolute top-4 right-4 w-3 h-3 rounded-full bg-gradient-to-r ${config.gradient}`}
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}
    </motion.button>
  );
}

// Inline mode badge for messages
export function ModeBadge({
  mode,
  confidence,
  className = '',
}: {
  mode: ModeType;
  confidence: number;
  className?: string;
}) {
  const normalizedMode = (mode?.toUpperCase?.() || 'ADAPTIVE') as ModeType;
  const config = modeConfig[normalizedMode] || modeConfig.ADAPTIVE;

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
        bg-gradient-to-r ${config.gradient} text-white
        ${className}
      `}
    >
      <span>{config.icon}</span>
      <span>{normalizedMode}</span>
      <span className="opacity-80">{Math.round(confidence * 100)}%</span>
    </span>
  );
}
