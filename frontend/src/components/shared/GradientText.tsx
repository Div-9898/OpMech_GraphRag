'use client';

import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface GradientTextProps {
  children: ReactNode;
  variant?: 'hero' | 'convergence' | 'operator-a' | 'operator-b';
  animate?: boolean;
  className?: string;
  as?: 'span' | 'h1' | 'h2' | 'h3' | 'h4' | 'p';
}

export default function GradientText({
  children,
  variant = 'hero',
  animate = true,
  className = '',
  as: Component = 'span',
}: GradientTextProps) {
  const gradients = {
    hero: 'from-[#667EEA] via-[#764BA2] to-[#667EEA]',
    convergence: 'from-[#667EEA] via-[#764BA2] to-[#F093FB]',
    'operator-a': 'from-[#3B82F6] via-[#60A5FA] to-[#3B82F6]',
    'operator-b': 'from-[#10B981] via-[#34D399] to-[#10B981]',
  };

  const MotionComponent = motion[Component] as typeof motion.span;

  return (
    <MotionComponent
      className={`
        bg-gradient-to-r ${gradients[variant]}
        bg-[length:200%_200%]
        bg-clip-text text-transparent
        ${className}
      `}
      animate={
        animate
          ? {
              backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
            }
          : undefined
      }
      transition={
        animate
          ? {
              duration: 4,
              ease: 'linear',
              repeat: Infinity,
            }
          : undefined
      }
    >
      {children}
    </MotionComponent>
  );
}

// Static gradient text without animation
export function StaticGradientText({
  children,
  from = '#667EEA',
  to = '#764BA2',
  className = '',
}: {
  children: ReactNode;
  from?: string;
  to?: string;
  className?: string;
}) {
  return (
    <span
      className={`bg-clip-text text-transparent ${className}`}
      style={{
        backgroundImage: `linear-gradient(135deg, ${from} 0%, ${to} 100%)`,
      }}
    >
      {children}
    </span>
  );
}
