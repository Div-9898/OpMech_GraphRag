'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  formatFn?: (value: number) => string;
}

export default function AnimatedNumber({
  value,
  duration = 1000,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
  formatFn,
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const prevValue = useRef(0);

  const spring = useSpring(0, {
    duration: duration,
    bounce: 0,
  });

  const display = useTransform(spring, (latest) => {
    if (formatFn) {
      return formatFn(latest);
    }
    return latest.toFixed(decimals);
  });

  useEffect(() => {
    spring.set(value);
    prevValue.current = value;
  }, [value, spring]);

  // Subscribe to spring changes
  useEffect(() => {
    const unsubscribe = display.on('change', (latest) => {
      setDisplayValue(parseFloat(latest));
    });
    return () => unsubscribe();
  }, [display]);

  return (
    <motion.span
      className={`tabular-nums ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {prefix}
      <motion.span>{display}</motion.span>
      {suffix}
    </motion.span>
  );
}

// Specialized animated counter for large numbers with commas
export function AnimatedCounter({
  value,
  duration = 1500,
  className = '',
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  return (
    <AnimatedNumber
      value={value}
      duration={duration}
      className={className}
      formatFn={(v) => Math.round(v).toLocaleString()}
    />
  );
}

// Percentage counter
export function AnimatedPercentage({
  value,
  duration = 1000,
  className = '',
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  return (
    <AnimatedNumber
      value={value * 100}
      duration={duration}
      decimals={0}
      suffix="%"
      className={className}
    />
  );
}

// Delta counter with color coding
export function AnimatedDelta({
  value,
  duration = 800,
  className = '',
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  const getColor = (v: number) => {
    if (v < 0.3) return 'text-green-500';
    if (v < 0.6) return 'text-amber-500';
    return 'text-red-500';
  };

  return (
    <AnimatedNumber
      value={value}
      duration={duration}
      decimals={3}
      className={`${getColor(value)} ${className}`}
    />
  );
}
