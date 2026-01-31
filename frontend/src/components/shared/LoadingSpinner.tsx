'use client';

import { motion } from 'framer-motion';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'dual-operator' | 'convergence';
  className?: string;
}

export default function LoadingSpinner({
  size = 'md',
  variant = 'default',
  className = '',
}: LoadingSpinnerProps) {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
  };

  if (variant === 'dual-operator') {
    return (
      <div className={`relative ${sizes[size]} ${className}`}>
        {/* Operator A ring */}
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-transparent border-t-[#3B82F6]"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, ease: 'linear', repeat: Infinity }}
        />
        {/* Operator B ring */}
        <motion.div
          className="absolute inset-1 rounded-full border-2 border-transparent border-t-[#10B981]"
          animate={{ rotate: -360 }}
          transition={{ duration: 1.5, ease: 'linear', repeat: Infinity }}
        />
        {/* Center dot */}
        <motion.div
          className="absolute inset-0 m-auto w-2 h-2 rounded-full bg-gradient-to-r from-[#667EEA] to-[#764BA2]"
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      </div>
    );
  }

  if (variant === 'convergence') {
    return (
      <div className={`relative ${sizes[size]} ${className}`}>
        <motion.div
          className="absolute inset-0"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, ease: 'linear', repeat: Infinity }}
        >
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-[#3B82F6]" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-[#10B981]" />
        </motion.div>
        <motion.div
          className="absolute inset-2 rounded-full border-2 border-dashed border-[#667EEA]/30"
          animate={{ rotate: -360 }}
          transition={{ duration: 4, ease: 'linear', repeat: Infinity }}
        />
      </div>
    );
  }

  return (
    <motion.div
      className={`${sizes[size]} rounded-full border-2 border-transparent border-t-[#667EEA] border-r-[#764BA2] ${className}`}
      animate={{ rotate: 360 }}
      transition={{ duration: 1, ease: 'linear', repeat: Infinity }}
    />
  );
}

// Typing dots indicator
export function TypingIndicator({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 rounded-full bg-[#86868B]"
          animate={{
            y: [0, -8, 0],
            backgroundColor: ['#86868B', '#3B82F6', '#86868B'],
          }}
          transition={{
            duration: 1.4,
            repeat: Infinity,
            delay: i * 0.2,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
}

// Progress bar
export function ProgressBar({
  progress,
  variant = 'default',
  className = '',
}: {
  progress: number;
  variant?: 'default' | 'gradient';
  className?: string;
}) {
  return (
    <div
      className={`h-2 rounded-full bg-black/10 overflow-hidden ${className}`}
    >
      <motion.div
        className={`h-full rounded-full ${
          variant === 'gradient'
            ? 'bg-gradient-to-r from-[#667EEA] to-[#764BA2]'
            : 'bg-[#3B82F6]'
        }`}
        initial={{ width: 0 }}
        animate={{ width: `${progress * 100}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      />
    </div>
  );
}

// Full page loading overlay
export function LoadingOverlay({
  message = 'Loading...',
}: {
  message?: string;
}) {
  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" variant="dual-operator" />
        <p className="text-[#6E6E73] font-medium">{message}</p>
      </div>
    </motion.div>
  );
}
