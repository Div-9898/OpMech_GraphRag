'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

interface GlassCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: ReactNode;
  variant?: 'default' | 'heavy' | 'dark';
  hover?: boolean;
  glow?: 'none' | 'a' | 'b' | 'convergence';
  className?: string;
}

export default function GlassCard({
  children,
  variant = 'default',
  hover = true,
  glow = 'none',
  className = '',
  ...props
}: GlassCardProps) {
  const baseStyles = 'relative overflow-hidden rounded-2xl';

  const variantStyles = {
    default: 'bg-white/72 backdrop-blur-xl border border-white/25 shadow-lg',
    heavy: 'bg-white/88 backdrop-blur-2xl border border-white/30 shadow-xl',
    dark: 'bg-black/50 backdrop-blur-xl border border-white/10 shadow-2xl',
  };

  const glowStyles = {
    none: '',
    a: 'shadow-[0_0_30px_rgba(59,130,246,0.35)]',
    b: 'shadow-[0_0_30px_rgba(16,185,129,0.35)]',
    convergence:
      'shadow-[0_0_40px_rgba(102,126,234,0.3),0_0_60px_rgba(118,75,162,0.2)]',
  };

  return (
    <motion.div
      className={`${baseStyles} ${variantStyles[variant]} ${glowStyles[glow]} ${className}`}
      whileHover={
        hover
          ? {
              y: -4,
              boxShadow:
                '0 16px 48px rgba(0, 0, 0, 0.12), 0 8px 24px rgba(0, 0, 0, 0.08)',
            }
          : undefined
      }
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      {...props}
    >
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 h-full">{children}</div>
    </motion.div>
  );
}
