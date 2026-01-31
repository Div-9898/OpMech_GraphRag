'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Cpu, GitBranch, Gauge, Lightbulb } from 'lucide-react';
import { ModeCard } from '@/components/chat/ModeIndicator';
import CommutatorGauge from '@/components/visualization/CommutatorGauge';

const features = [
  {
    id: 'dual-operator',
    title: 'Dual Operator Architecture',
    subtitle: 'Two perspectives, one truth',
    description:
      'Our quantum-inspired approach uses two distinct operators to explore the knowledge graph from complementary perspectives.',
    icon: GitBranch,
    operators: [
      {
        name: 'Operator A',
        type: 'Structure-First',
        color: '#3B82F6',
        items: ['XBRL Financial Data', 'Hierarchical Links', 'Quantitative Focus'],
      },
      {
        name: 'Operator B',
        type: 'Narrative-First',
        color: '#10B981',
        items: ['MD&A Narratives', 'Semantic Connections', 'Qualitative Context'],
      },
    ],
  },
  {
    id: 'commutator',
    title: 'The Commutator',
    subtitle: '[A, B] = AB - BA ≠ 0',
    description:
      'The mathematical heart of OpMech - measuring divergence between operator perspectives to determine the optimal response strategy.',
    icon: Gauge,
  },
  {
    id: 'mode-selection',
    title: 'Intelligent Mode Selection',
    subtitle: 'Adaptive response strategies',
    description:
      'Based on divergence analysis, the system automatically selects the optimal mode for answering your query.',
    icon: Lightbulb,
  },
];

export default function FeatureShowcase() {
  return (
    <section className="py-24 bg-[#F5F5F7]">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-[#1D1D1F] mb-4">
            How It Works
          </h2>
          <p className="text-xl text-[#6E6E73] max-w-2xl mx-auto">
            A novel approach to knowledge retrieval that combines quantum-inspired
            mechanics with graph-based reasoning.
          </p>
        </motion.div>

        {/* Feature 1: Dual Operator */}
        <FeatureSection feature={features[0]}>
          <div className="grid md:grid-cols-2 gap-6">
            {features[0].operators?.map((op, index) => (
              <motion.div
                key={op.name}
                initial={{ opacity: 0, x: index === 0 ? -30 : 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 + index * 0.1 }}
                className="relative p-6 rounded-2xl bg-white border border-black/5"
                style={{ borderTopColor: op.color, borderTopWidth: '4px' }}
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{ backgroundColor: `${op.color}15` }}
                >
                  <Cpu className="w-6 h-6" style={{ color: op.color }} />
                </div>
                <h4 className="text-xl font-bold text-[#1D1D1F] mb-1">{op.name}</h4>
                <p className="text-sm font-medium mb-4" style={{ color: op.color }}>
                  {op.type}
                </p>
                <ul className="space-y-2">
                  {op.items.map((item) => (
                    <li key={item} className="flex items-center gap-2 text-[#6E6E73]">
                      <div
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: op.color }}
                      />
                      {item}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </FeatureSection>

        {/* Feature 2: Commutator */}
        <FeatureSection feature={features[1]}>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="flex justify-center"
          >
            <CommutatorGauge
              delta={0.335}
              deltaComponents={{
                delta_E: 0.63,
                delta_V: 0.57,
                delta_A: 0.03,
                delta_C: 0.11,
              }}
              isAnimating={false}
              size={240}
              showComponents={true}
            />
          </motion.div>
        </FeatureSection>

        {/* Feature 3: Mode Selection */}
        <FeatureSection feature={features[2]}>
          <div className="grid md:grid-cols-3 gap-4">
            <ModeCard mode="EXPLOIT" isActive={false} />
            <ModeCard mode="ADAPTIVE" isActive={true} />
            <ModeCard mode="EXPLORE" isActive={false} />
          </div>
        </FeatureSection>
      </div>
    </section>
  );
}

function FeatureSection({
  feature,
  children,
}: {
  feature: (typeof features)[0];
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const Icon = feature.icon;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6 }}
      className="mb-24 last:mb-0"
    >
      <div className="grid lg:grid-cols-2 gap-12 items-center">
        {/* Text content */}
        <div className={feature.id === 'commutator' ? 'lg:order-2' : ''}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-3 mb-6"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center">
              <Icon className="w-6 h-6 text-white" />
            </div>
            <span className="text-sm font-medium text-[#6E6E73] uppercase tracking-wider">
              Feature
            </span>
          </motion.div>

          <h3 className="text-3xl lg:text-4xl font-bold text-[#1D1D1F] mb-2">
            {feature.title}
          </h3>

          {feature.subtitle && (
            <p className="text-lg font-mono text-[#667EEA] mb-4">{feature.subtitle}</p>
          )}

          <p className="text-lg text-[#6E6E73] leading-relaxed">{feature.description}</p>
        </div>

        {/* Visual content */}
        <div className={feature.id === 'commutator' ? 'lg:order-1' : ''}>
          {children}
        </div>
      </div>
    </motion.div>
  );
}
