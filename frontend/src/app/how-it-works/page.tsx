'use client';

import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Search,
  MessageCircle,
  Check,
  HelpCircle,
  X,
  Sparkles,
  Scale,
  Eye,
  Map,
  Target,
  Calculator,
  BookOpen,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// STORYBOOK DETECTIVE EXPLAINER - "Explaining OpMech Like You're 5"
// Warm, illustrated, playful design with paper textures and hand-drawn vibes
// ═══════════════════════════════════════════════════════════════════════════

// Detective Character Component
function DetectiveCharacter({
  type,
  isActive,
}: {
  type: 'A' | 'B';
  isActive?: boolean;
}) {
  const isA = type === 'A';
  const bgColor = isA ? '#3B82F6' : '#10B981';
  const hatColor = isA ? '#1E40AF' : '#047857';

  return (
    <motion.div
      className="relative"
      animate={isActive ? { y: [0, -8, 0] } : {}}
      transition={{ duration: 0.6, repeat: isActive ? Infinity : 0, repeatDelay: 1 }}
    >
      <svg width="120" height="140" viewBox="0 0 120 140">
        {/* Body */}
        <ellipse cx="60" cy="115" rx="35" ry="20" fill={bgColor} opacity="0.9" />

        {/* Face */}
        <circle cx="60" cy="65" r="35" fill="#FCD9B6" />

        {/* Detective Hat */}
        <path
          d="M25 55 Q60 20 95 55 L90 60 Q60 35 30 60 Z"
          fill={hatColor}
        />
        <ellipse cx="60" cy="55" rx="40" ry="8" fill={hatColor} />

        {/* Eyes */}
        <circle cx="48" cy="60" r="5" fill="#1D1D1F" />
        <circle cx="72" cy="60" r="5" fill="#1D1D1F" />
        <circle cx="49" cy="59" r="2" fill="white" />
        <circle cx="73" cy="59" r="2" fill="white" />

        {/* Eyebrows */}
        <path
          d={isA ? "M42 52 Q48 48 54 52" : "M42 50 Q48 54 54 50"}
          stroke="#5D4037"
          strokeWidth="2"
          fill="none"
        />
        <path
          d={isA ? "M66 52 Q72 48 78 52" : "M66 50 Q72 54 78 50"}
          stroke="#5D4037"
          strokeWidth="2"
          fill="none"
        />

        {/* Smile */}
        <path
          d="M45 78 Q60 88 75 78"
          stroke="#1D1D1F"
          strokeWidth="2"
          fill="none"
        />

        {/* Magnifying Glass */}
        <g transform="translate(85, 70) rotate(30)">
          <circle cx="0" cy="0" r="12" fill="none" stroke={bgColor} strokeWidth="4" />
          <rect x="-3" y="10" width="6" height="20" rx="2" fill="#8B4513" />
          <circle cx="0" cy="0" r="8" fill="rgba(255,255,255,0.3)" />
        </g>

        {/* Label Badge */}
        <rect x="45" y="125" width="30" height="14" rx="7" fill="white" />
        <text
          x="60"
          y="135"
          textAnchor="middle"
          fontSize="10"
          fontWeight="bold"
          fill={bgColor}
        >
          {type}
        </text>
      </svg>
    </motion.div>
  );
}

// Paper Card Component
function PaperCard({
  children,
  className = '',
  color = '#FEF3E2',
}: {
  children: React.ReactNode;
  className?: string;
  color?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, rotate: -1 }}
      whileInView={{ opacity: 1, y: 0, rotate: 0 }}
      viewport={{ once: true }}
      whileHover={{ scale: 1.02, rotate: 0.5 }}
      className={`relative rounded-2xl p-6 shadow-lg ${className}`}
      style={{
        background: color,
        boxShadow: `
          0 4px 6px rgba(0, 0, 0, 0.05),
          0 10px 30px rgba(0, 0, 0, 0.08),
          inset 0 1px 0 rgba(255, 255, 255, 0.5)
        `,
      }}
    >
      {/* Paper texture overlay */}
      <div
        className="absolute inset-0 rounded-2xl opacity-30 pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%' height='100%' filter='url(%23noise)' opacity='0.4'/%3E%3C/svg%3E")`,
        }}
      />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}

// Speech Bubble Component
function SpeechBubble({
  children,
  direction = 'left',
}: {
  children: React.ReactNode;
  direction?: 'left' | 'right';
}) {
  return (
    <div className="relative">
      <div className="bg-white rounded-2xl px-4 py-3 shadow-md border-2 border-[#E5E7EB]">
        <p className="text-sm md:text-base text-[#1D1D1F] font-medium italic">
          &ldquo;{children}&rdquo;
        </p>
      </div>
      <div
        className={`absolute -bottom-2 ${direction === 'left' ? 'left-6' : 'right-6'}`}
        style={{
          width: 0,
          height: 0,
          borderLeft: '10px solid transparent',
          borderRight: '10px solid transparent',
          borderTop: '10px solid white',
        }}
      />
    </div>
  );
}

// Animated Meter Component
function DisagreementMeter({ value = 0.33 }: { value?: number }) {
  const [isAnimating, setIsAnimating] = useState(false);

  return (
    <div className="w-full">
      <div className="relative h-12 bg-gradient-to-r from-[#34C759] via-[#F59E0B] to-[#FF3B30] rounded-full overflow-hidden shadow-inner">
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 w-6 h-6 bg-white rounded-full shadow-lg border-2 border-[#1D1D1F] z-10 cursor-pointer"
          style={{ left: `calc(${value * 100}% - 12px)` }}
          animate={isAnimating ? { scale: [1, 1.2, 1] } : {}}
          onClick={() => setIsAnimating(!isAnimating)}
        />
        {/* Tick marks */}
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
          <div
            key={tick}
            className="absolute top-0 bottom-0 w-0.5 bg-white/40"
            style={{ left: `${tick * 100}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between mt-2 text-sm font-bold">
        <span className="text-[#34C759]">0</span>
        <span className="text-[#F59E0B]">0.5</span>
        <span className="text-[#FF3B30]">1</span>
      </div>
      <div className="flex justify-between text-xs text-[#6E6E73]">
        <span>Same answer!</span>
        <span>Kinda same</span>
        <span>Totally different!</span>
      </div>
    </div>
  );
}

// Outcome Card for the table
function OutcomeCard({
  emoji,
  title,
  mode,
  modeColor,
  description,
  isActive,
  onClick,
}: {
  emoji: string;
  title: string;
  mode: string;
  modeColor: string;
  description: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.98 }}
      className={`w-full p-4 rounded-xl text-left transition-all ${
        isActive
          ? 'bg-white shadow-xl ring-2'
          : 'bg-[#FEF3E2]/50 hover:bg-white hover:shadow-md'
      }`}
      style={{ '--tw-ring-color': isActive ? modeColor : 'transparent' } as React.CSSProperties}
    >
      <div className="text-3xl mb-2">{emoji}</div>
      <div className="text-sm text-[#6E6E73] mb-1">{title}</div>
      <div
        className="inline-block px-2 py-1 rounded-full text-xs font-bold text-white mb-2"
        style={{ background: modeColor }}
      >
        {mode}
      </div>
      <p className="text-sm text-[#1D1D1F]">{description}</p>
    </motion.button>
  );
}

// Check Item Component
function CheckItem({
  symbol,
  name,
  kidVersion,
  color,
  delay = 0,
}: {
  symbol: string;
  name: string;
  kidVersion: string;
  color: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ delay }}
      className="flex items-start gap-4 p-4 bg-white rounded-xl shadow-sm"
    >
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 text-xl font-bold text-white"
        style={{ background: color }}
      >
        {symbol}
      </div>
      <div>
        <div className="font-bold text-[#1D1D1F]">{name}</div>
        <div className="text-sm text-[#6E6E73]">{kidVersion}</div>
      </div>
    </motion.div>
  );
}

// Flow Diagram Component
function FlowDiagram() {
  const [activeOutcome, setActiveOutcome] = useState<'yes' | 'kinda' | 'no'>('yes');

  return (
    <div className="relative py-8">
      {/* Detectives Row */}
      <div className="flex justify-between items-start mb-8 px-8">
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="text-center"
        >
          <DetectiveCharacter type="A" isActive={activeOutcome === 'yes'} />
          <div className="mt-2 text-sm font-medium text-[#3B82F6]">Detective A</div>
          <div className="text-xs text-[#6E6E73]">(Counts first)</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 30 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="text-center"
        >
          <DetectiveCharacter type="B" isActive={activeOutcome === 'no'} />
          <div className="mt-2 text-sm font-medium text-[#10B981]">Detective B</div>
          <div className="text-xs text-[#6E6E73]">(Asks first)</div>
        </motion.div>
      </div>

      {/* Arrows converging */}
      <svg className="w-full h-16" viewBox="0 0 400 60" preserveAspectRatio="xMidYMid meet">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#6E6E73" />
          </marker>
        </defs>
        <motion.path
          d="M60,10 Q200,10 200,50"
          stroke="#3B82F6"
          strokeWidth="3"
          fill="none"
          strokeDasharray="8,4"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        />
        <motion.path
          d="M340,10 Q200,10 200,50"
          stroke="#10B981"
          strokeWidth="3"
          fill="none"
          strokeDasharray="8,4"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
        />
      </svg>

      {/* AGREE? Box */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        className="w-32 h-16 mx-auto bg-gradient-to-br from-[#667EEA] to-[#764BA2] rounded-xl flex items-center justify-center text-white font-bold shadow-lg"
      >
        AGREE?
      </motion.div>

      {/* Arrows diverging */}
      <svg className="w-full h-16" viewBox="0 0 400 60" preserveAspectRatio="xMidYMid meet">
        <motion.path
          d="M200,10 Q100,50 60,50"
          stroke="#34C759"
          strokeWidth="3"
          fill="none"
          markerEnd="url(#arrowhead)"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
        />
        <motion.path
          d="M200,10 L200,50"
          stroke="#F59E0B"
          strokeWidth="3"
          fill="none"
          markerEnd="url(#arrowhead)"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
        />
        <motion.path
          d="M200,10 Q300,50 340,50"
          stroke="#FF3B30"
          strokeWidth="3"
          fill="none"
          markerEnd="url(#arrowhead)"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.6 }}
        />
      </svg>

      {/* Outcomes Row */}
      <div className="grid grid-cols-3 gap-4 mt-4">
        <motion.button
          onClick={() => setActiveOutcome('yes')}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`p-4 rounded-xl text-center transition-all ${
            activeOutcome === 'yes'
              ? 'bg-[#34C759]/20 ring-2 ring-[#34C759]'
              : 'bg-[#34C759]/5 hover:bg-[#34C759]/10'
          }`}
        >
          <div className="text-2xl mb-1">😊</div>
          <div className="font-bold text-[#34C759]">YES</div>
          <div className="text-xs text-[#6E6E73] mt-1">&ldquo;Here&apos;s the answer!&rdquo;</div>
        </motion.button>

        <motion.button
          onClick={() => setActiveOutcome('kinda')}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`p-4 rounded-xl text-center transition-all ${
            activeOutcome === 'kinda'
              ? 'bg-[#F59E0B]/20 ring-2 ring-[#F59E0B]'
              : 'bg-[#F59E0B]/5 hover:bg-[#F59E0B]/10'
          }`}
        >
          <div className="text-2xl mb-1">🤔</div>
          <div className="font-bold text-[#F59E0B]">KINDA</div>
          <div className="text-xs text-[#6E6E73] mt-1">&ldquo;Probably this, but...&rdquo;</div>
        </motion.button>

        <motion.button
          onClick={() => setActiveOutcome('no')}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`p-4 rounded-xl text-center transition-all ${
            activeOutcome === 'no'
              ? 'bg-[#FF3B30]/20 ring-2 ring-[#FF3B30]'
              : 'bg-[#FF3B30]/5 hover:bg-[#FF3B30]/10'
          }`}
        >
          <div className="text-2xl mb-1">😟</div>
          <div className="font-bold text-[#FF3B30]">NO</div>
          <div className="text-xs text-[#6E6E73] mt-1">&ldquo;Could be this OR that&rdquo;</div>
        </motion.button>
      </div>
    </div>
  );
}

// Real Example Component
function RealExample() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="bg-gradient-to-br from-[#1D1D1F] to-[#2D2D32] rounded-3xl p-8 text-white overflow-hidden relative"
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute top-10 left-10 text-6xl">💰</div>
        <div className="absolute bottom-10 right-10 text-6xl">🍎</div>
        <div className="absolute top-1/2 right-1/4 text-4xl">📊</div>
      </div>

      <div className="relative z-10">
        <div className="flex items-center gap-2 mb-6">
          <BookOpen className="w-5 h-5 text-[#F59E0B]" />
          <span className="text-sm font-medium text-[#F59E0B]">Real Example in Kid Terms</span>
        </div>

        <h3 className="text-2xl font-bold mb-6">
          Question: &ldquo;How much money does Apple have?&rdquo;
        </h3>

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Detective A */}
          <div className="bg-[#3B82F6]/20 rounded-2xl p-5 border border-[#3B82F6]/30">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-[#3B82F6] rounded-full flex items-center justify-center font-bold">
                A
              </div>
              <span className="font-medium">Detective A</span>
            </div>
            <div className="flex items-start gap-2 mb-3">
              <Calculator className="w-5 h-5 text-[#3B82F6] flex-shrink-0 mt-0.5" />
              <p className="text-sm text-white/80">
                Opens the cash register, counts:
              </p>
            </div>
            <div className="text-2xl font-bold text-[#3B82F6]">
              &ldquo;$383 billion&rdquo;
            </div>
          </div>

          {/* Detective B */}
          <div className="bg-[#10B981]/20 rounded-2xl p-5 border border-[#10B981]/30">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-[#10B981] rounded-full flex items-center justify-center font-bold">
                B
              </div>
              <span className="font-medium">Detective B</span>
            </div>
            <div className="flex items-start gap-2 mb-3">
              <MessageCircle className="w-5 h-5 text-[#10B981] flex-shrink-0 mt-0.5" />
              <p className="text-sm text-white/80">
                Asks the manager:
              </p>
            </div>
            <div className="text-2xl font-bold text-[#10B981]">
              &ldquo;Oh, around $380-ish billion&rdquo;
            </div>
          </div>
        </div>

        {/* Result */}
        <div className="bg-white/10 rounded-2xl p-6 backdrop-blur-sm">
          <div className="grid sm:grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-sm text-white/60 mb-1">Commutator says</div>
              <div className="text-lg font-bold">
                They mostly agree! <span className="text-[#F59E0B]">(Δ = 0.33)</span>
              </div>
            </div>
            <div>
              <div className="text-sm text-white/60 mb-1">Mode</div>
              <span className="inline-block px-3 py-1 bg-[#3B82F6] rounded-full font-bold">
                EXPLOIT ✅
              </span>
            </div>
            <div>
              <div className="text-sm text-white/60 mb-1">Answer</div>
              <div className="text-lg font-bold text-[#34C759]">
                &ldquo;$383 billion&rdquo;
              </div>
            </div>
          </div>
          <p className="text-center text-sm text-white/70 mt-4">
            (Trust Detective A - he actually counted!)
          </p>
        </div>
      </div>
    </motion.div>
  );
}

// Main Page Component
export default function HowItWorksPage() {
  const [activeMode, setActiveMode] = useState<'exploit' | 'adaptive' | 'explore'>('exploit');

  return (
    <PageWrapper>
      {/* Warm Paper Background */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: `
            radial-gradient(ellipse at 30% 20%, rgba(254, 243, 226, 0.8) 0%, transparent 50%),
            radial-gradient(ellipse at 70% 80%, rgba(254, 226, 226, 0.5) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, rgba(237, 233, 254, 0.3) 0%, transparent 70%),
            linear-gradient(180deg, #FAFAFA 0%, #F5F5F7 100%)
          `,
        }}
      />

      {/* Hero Section */}
      <Section className="pt-24 pb-12 relative z-10">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back Home
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-3xl mx-auto"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#FEF3E2] rounded-full mb-6"
          >
            <span className="text-2xl">🔍</span>
            <span className="font-medium text-[#B45309]">Explained Simply</span>
          </motion.div>

          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            <span className="text-[#1D1D1F]">The </span>
            <span className="text-[#3B82F6]">Two </span>
            <span className="text-[#10B981]">Detectives</span>
          </h1>

          <p className="text-xl md:text-2xl text-[#6E6E73] leading-relaxed">
            Understanding OpMech&apos;s dual operators like you&apos;re 5
          </p>
        </motion.div>
      </Section>

      {/* The Setup - Lost Toy Story */}
      <Section className="!pt-0 relative z-10">
        <PaperCard className="max-w-3xl mx-auto mb-12">
          <div className="flex items-start gap-4">
            <span className="text-4xl">🧸</span>
            <div>
              <h2 className="text-2xl font-bold text-[#1D1D1F] mb-3">
                The Story Begins...
              </h2>
              <p className="text-lg text-[#6E6E73] leading-relaxed">
                Imagine you lost your toy in your house and you ask{' '}
                <span className="font-bold text-[#3B82F6]">two detectives</span> to find it.
                They each have their own way of searching!
              </p>
            </div>
          </div>
        </PaperCard>

        {/* The Two Detectives */}
        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {/* Detective A */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <PaperCard color="#EFF6FF">
              <div className="flex flex-col items-center text-center mb-6">
                <DetectiveCharacter type="A" />
                <h3 className="text-xl font-bold text-[#3B82F6] mt-4">
                  Detective A
                </h3>
                <span className="text-sm text-[#6E6E73]">
                  (Operator A - Structure-First)
                </span>
              </div>

              <SpeechBubble direction="left">
                Detective A always starts in the toy box.
              </SpeechBubble>

              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-3 p-3 bg-white/70 rounded-lg">
                  <Search className="w-5 h-5 text-[#3B82F6]" />
                  <span className="text-sm">Looks in the toy box first</span>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white/70 rounded-lg">
                  <Map className="w-5 h-5 text-[#3B82F6]" />
                  <span className="text-sm">Then checks nearby shelves</span>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white/70 rounded-lg">
                  <MessageCircle className="w-5 h-5 text-[#3B82F6]" />
                  <span className="text-sm">Maybe asks mom where she saw it</span>
                </div>
              </div>

              <div className="mt-6 p-4 bg-[#3B82F6]/10 rounded-xl">
                <div className="flex items-center justify-center gap-2 text-[#3B82F6] font-bold">
                  <Calculator className="w-5 h-5" />
                  Numbers → Story
                </div>
                <p className="text-xs text-center text-[#6E6E73] mt-2">
                  He trusts the toy box label that says &ldquo;Cars go here&rdquo;
                </p>
              </div>
            </PaperCard>
          </motion.div>

          {/* Detective B */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <PaperCard color="#ECFDF5">
              <div className="flex flex-col items-center text-center mb-6">
                <DetectiveCharacter type="B" />
                <h3 className="text-xl font-bold text-[#10B981] mt-4">
                  Detective B
                </h3>
                <span className="text-sm text-[#6E6E73]">
                  (Operator B - Narrative-First)
                </span>
              </div>

              <SpeechBubble direction="right">
                Detective B always asks your mom first.
              </SpeechBubble>

              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-3 p-3 bg-white/70 rounded-lg">
                  <MessageCircle className="w-5 h-5 text-[#10B981]" />
                  <span className="text-sm">Asks &ldquo;Where did you last play?&rdquo;</span>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white/70 rounded-lg">
                  <Eye className="w-5 h-5 text-[#10B981]" />
                  <span className="text-sm">Listens to the story carefully</span>
                </div>
                <div className="flex items-center gap-3 p-3 bg-white/70 rounded-lg">
                  <Search className="w-5 h-5 text-[#10B981]" />
                  <span className="text-sm">Then goes to check that room</span>
                </div>
              </div>

              <div className="mt-6 p-4 bg-[#10B981]/10 rounded-xl">
                <div className="flex items-center justify-center gap-2 text-[#10B981] font-bold">
                  <BookOpen className="w-5 h-5" />
                  Story → Numbers
                </div>
                <p className="text-xs text-center text-[#6E6E73] mt-2">
                  She trusts what people remember
                </p>
              </div>
            </PaperCard>
          </motion.div>
        </div>
      </Section>

      {/* The Commutator Section */}
      <Section className="bg-gradient-to-b from-[#F5F5F7] to-[#FAFAFA] relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#667EEA]/10 rounded-full mb-4">
            <Scale className="w-5 h-5 text-[#667EEA]" />
            <span className="font-medium text-[#667EEA]">The Commutator</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-[#1D1D1F] mb-4">
            🤝 Do They Agree?
          </h2>
          <p className="text-lg text-[#6E6E73] max-w-2xl mx-auto">
            Now both detectives come back. Did they find the same toy in the same place?
          </p>
        </motion.div>

        {/* Outcomes Grid */}
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12">
          <OutcomeCard
            emoji="✅"
            title="Both found the red car under the sofa"
            mode="EXPLOIT"
            modeColor="#3B82F6"
            description="&ldquo;Your toy is under the sofa!&rdquo;"
            isActive={activeMode === 'exploit'}
            onClick={() => setActiveMode('exploit')}
          />
          <OutcomeCard
            emoji="🤔"
            title="A found red car, B found blue car"
            mode="ADAPTIVE"
            modeColor="#F59E0B"
            description="&ldquo;Probably the red car, but check for blue too&rdquo;"
            isActive={activeMode === 'adaptive'}
            onClick={() => setActiveMode('adaptive')}
          />
          <OutcomeCard
            emoji="❌"
            title="A says sofa, B says bedroom"
            mode="EXPLORE"
            modeColor="#8B5CF6"
            description="&ldquo;It might be in the sofa OR bedroom - let's check both&rdquo;"
            isActive={activeMode === 'explore'}
            onClick={() => setActiveMode('explore')}
          />
        </div>

        {/* The Meter */}
        <PaperCard className="max-w-2xl mx-auto" color="#FFFFFF">
          <h3 className="text-xl font-bold text-center mb-6 flex items-center justify-center gap-2">
            <span className="text-2xl">📏</span>
            The Disagreement Meter
          </h3>
          <p className="text-center text-[#6E6E73] mb-6">
            Think of it like a &ldquo;disagreement meter&rdquo; from 0 to 1:
          </p>
          <DisagreementMeter value={activeMode === 'exploit' ? 0.15 : activeMode === 'adaptive' ? 0.5 : 0.85} />
          <div className="flex justify-center gap-4 mt-6">
            <span className="px-3 py-1 bg-[#34C759]/10 text-[#34C759] rounded-full text-sm font-medium">
              EXPLOIT
            </span>
            <span className="px-3 py-1 bg-[#F59E0B]/10 text-[#F59E0B] rounded-full text-sm font-medium">
              ADAPTIVE
            </span>
            <span className="px-3 py-1 bg-[#8B5CF6]/10 text-[#8B5CF6] rounded-full text-sm font-medium">
              EXPLORE
            </span>
          </div>
        </PaperCard>
      </Section>

      {/* The 4 Checks */}
      <Section className="relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#1D1D1F] mb-4">
            We Check 4 Things
          </h2>
          <p className="text-lg text-[#6E6E73]">
            Here&apos;s what the commutator measures
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-4 max-w-3xl mx-auto">
          <CheckItem
            symbol="Δₑ"
            name="Evidence"
            kidVersion="Did they look in the same rooms?"
            color="#3B82F6"
            delay={0}
          />
          <CheckItem
            symbol="Δᵥ"
            name="Structure"
            kidVersion="Did they check the same type of places (drawers vs shelves)?"
            color="#10B981"
            delay={0.1}
          />
          <CheckItem
            symbol="Δₐ"
            name="Answer"
            kidVersion="Did they find the same toy?"
            color="#F59E0B"
            delay={0.2}
          />
          <CheckItem
            symbol="Δc"
            name="Confidence"
            kidVersion="Are they both sure, or is one guessing?"
            color="#8B5CF6"
            delay={0.3}
          />
        </div>
      </Section>

      {/* Who Do We Trust */}
      <Section className="bg-[#FEF3E2]/50 relative z-10">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-8"
          >
            <div className="text-4xl mb-4">🏆</div>
            <h2 className="text-3xl md:text-4xl font-bold text-[#1D1D1F] mb-4">
              Who Do We Trust?
            </h2>
          </motion.div>

          <PaperCard color="#FFFFFF">
            <p className="text-lg text-center text-[#6E6E73] mb-6">
              If they disagree about a <span className="font-bold text-[#1D1D1F]">NUMBER</span> (like how many toys),
              trust the detective who actually <span className="font-bold text-[#3B82F6]">COUNTED</span> the toys,
              not the one who guessed.
            </p>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 bg-[#34C759]/10 rounded-xl border-2 border-[#34C759]">
                <div className="flex items-center gap-2 mb-2">
                  <Check className="w-5 h-5 text-[#34C759]" />
                  <span className="font-bold text-[#34C759]">Detective A</span>
                </div>
                <p className="text-sm text-[#1D1D1F]">
                  Counted 5 cars in the toy box
                </p>
                <p className="text-xs text-[#6E6E73] mt-1">
                  (Trust him - he counted!)
                </p>
              </div>

              <div className="p-4 bg-[#FF3B30]/10 rounded-xl border-2 border-[#FF3B30]">
                <div className="flex items-center gap-2 mb-2">
                  <X className="w-5 h-5 text-[#FF3B30]" />
                  <span className="font-bold text-[#FF3B30]">Detective B</span>
                </div>
                <p className="text-sm text-[#1D1D1F]">
                  Heard &ldquo;around 5 or 6&rdquo; from mom
                </p>
                <p className="text-xs text-[#6E6E73] mt-1">
                  (Just a guess)
                </p>
              </div>
            </div>
          </PaperCard>
        </div>
      </Section>

      {/* Flow Diagram */}
      <Section className="relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-8"
        >
          <div className="text-4xl mb-4">🖼️</div>
          <h2 className="text-3xl md:text-4xl font-bold text-[#1D1D1F] mb-4">
            The Big Picture
          </h2>
        </motion.div>

        <PaperCard className="max-w-3xl mx-auto" color="#FFFFFF">
          <FlowDiagram />
        </PaperCard>
      </Section>

      {/* Real Example */}
      <Section className="relative z-10">
        <div className="max-w-3xl mx-auto">
          <RealExample />
        </div>
      </Section>

      {/* Summary */}
      <Section className="bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto text-center"
        >
          <div className="text-4xl mb-4">🎯</div>
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            The Simple Summary
          </h2>
          <p className="text-xl md:text-2xl opacity-90 leading-relaxed">
            Two detectives search differently. We check if they agree.
            If yes, we&apos;re confident. If no, we show both answers.
            For counting questions, trust the one who actually counted.
          </p>

          <div className="flex flex-wrap justify-center gap-4 mt-8">
            <Sparkles className="w-6 h-6 opacity-70" />
            <span className="text-lg font-medium opacity-90">
              That&apos;s OpMech in a nutshell!
            </span>
            <Sparkles className="w-6 h-6 opacity-70" />
          </div>
        </motion.div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12 relative z-10">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back Home
          </Link>
          <Link
            href="/features/dual-operators"
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white rounded-full font-semibold hover:shadow-lg transition-all"
          >
            Dive Deeper: Technical Details
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
