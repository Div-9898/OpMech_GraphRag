'use client';

import { useRef, Suspense } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ChevronDown, Play, Github } from 'lucide-react';
import dynamic from 'next/dynamic';
import GradientText from '@/components/shared/GradientText';
import LoadingSpinner from '@/components/shared/LoadingSpinner';

// Dynamically import 3D component to avoid SSR issues
const KnowledgeGraph3D = dynamic(
  () => import('@/components/visualization/KnowledgeGraph3D'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14] rounded-3xl">
        <LoadingSpinner size="lg" variant="dual-operator" />
      </div>
    ),
  }
);

interface HeroSectionProps {
  onScrollToDemo: () => void;
}

export default function HeroSection({ onScrollToDemo }: HeroSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  });

  const y = useTransform(scrollYProgress, [0, 1], ['0%', '50%']);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  return (
    <section
      ref={containerRef}
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
    >
      {/* Background gradient mesh */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#FAFAFA] via-[#F5F5F7] to-[#FAFAFA]" />
      <div
        className="absolute inset-0 opacity-60"
        style={{
          background: `
            radial-gradient(at 20% 30%, rgba(102, 126, 234, 0.15) 0px, transparent 50%),
            radial-gradient(at 80% 20%, rgba(118, 75, 162, 0.12) 0px, transparent 50%),
            radial-gradient(at 40% 80%, rgba(59, 130, 246, 0.1) 0px, transparent 50%)
          `,
        }}
      />

      <motion.div
        className="relative z-10 w-full max-w-7xl mx-auto px-6 py-20"
        style={{ y, opacity }}
      >
        {/* Main content */}
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left side - Text content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 backdrop-blur-sm border border-black/5 mb-6"
            >
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm font-medium text-[#1D1D1F]">
                Research Project - SP Jain
              </span>
            </motion.div>

            {/* Main heading */}
            <h1 className="text-5xl lg:text-7xl font-bold leading-tight mb-6">
              <GradientText as="span" variant="hero" className="block">
                OpMech
              </GradientText>
              <span className="text-[#1D1D1F]">GraphRAG</span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl lg:text-2xl text-[#6E6E73] leading-relaxed mb-4">
              Multi-Perspective Knowledge Retrieval Through{' '}
              <span className="text-[#1D1D1F] font-medium">
                Quantum-Inspired Operator Mechanics
              </span>
            </p>

            {/* Tagline */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="text-lg text-[#86868B] italic mb-8"
            >
              &ldquo;When two perspectives converge, truth emerges&rdquo;
            </motion.p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap gap-4">
              <motion.button
                onClick={onScrollToDemo}
                className="btn-primary group"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Play className="w-5 h-5" />
                Try Live Demo
                <ChevronDown className="w-4 h-4 group-hover:translate-y-1 transition-transform" />
              </motion.button>

              <motion.a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Github className="w-5 h-5" />
                View Source
              </motion.a>
            </div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="flex gap-8 mt-12 pt-8 border-t border-black/5"
            >
              <div>
                <div className="text-3xl font-bold text-[#1D1D1F]">1,737</div>
                <div className="text-sm text-[#6E6E73]">Knowledge Nodes</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-[#1D1D1F]">26,842</div>
                <div className="text-sm text-[#6E6E73]">Graph Edges</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-[#3B82F6]">100%</div>
                <div className="text-sm text-[#6E6E73]">Mode Accuracy</div>
              </div>
            </motion.div>
          </motion.div>

          {/* Right side - 3D Graph */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="relative h-[500px] lg:h-[600px]"
          >
            {/* Glow effect behind canvas */}
            <div className="absolute inset-0 bg-gradient-to-r from-[#667EEA]/20 to-[#764BA2]/20 blur-3xl rounded-full scale-75" />

            {/* 3D Canvas */}
            <div className="relative h-full rounded-3xl overflow-hidden shadow-2xl">
              <Suspense
                fallback={
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
                    <LoadingSpinner size="lg" variant="dual-operator" />
                  </div>
                }
              >
                <KnowledgeGraph3D showStats={true} />
              </Suspense>
            </div>

            {/* Floating operator indicators */}
            <motion.div
              className="absolute -left-4 top-1/4 px-4 py-2 rounded-full bg-[#3B82F6]/10 border border-[#3B82F6]/20 backdrop-blur-sm"
              animate={{ x: [0, 10, 0], y: [0, -5, 0] }}
              transition={{ duration: 4, repeat: Infinity }}
            >
              <span className="text-sm font-medium text-[#3B82F6]">
                Operator A: Structure
              </span>
            </motion.div>

            <motion.div
              className="absolute -right-4 top-2/3 px-4 py-2 rounded-full bg-[#10B981]/10 border border-[#10B981]/20 backdrop-blur-sm"
              animate={{ x: [0, -10, 0], y: [0, 5, 0] }}
              transition={{ duration: 4, repeat: Infinity, delay: 1 }}
            >
              <span className="text-sm font-medium text-[#10B981]">
                Operator B: Narrative
              </span>
            </motion.div>
          </motion.div>
        </div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
      >
        <span className="text-sm text-[#86868B]">Scroll to explore</span>
        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <ChevronDown className="w-6 h-6 text-[#86868B]" />
        </motion.div>
      </motion.div>
    </section>
  );
}
