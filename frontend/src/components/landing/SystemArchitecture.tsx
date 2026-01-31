'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const architectureNodes = [
  { id: 'query', label: 'Query', x: 50, y: 5, type: 'input' },
  { id: 'classifier', label: 'Query Classifier', x: 50, y: 18, type: 'process' },
  { id: 'operator-a', label: 'Operator A\nStructure First', x: 25, y: 35, type: 'operator-a' },
  { id: 'operator-b', label: 'Operator B\nNarrative First', x: 75, y: 35, type: 'operator-b' },
  { id: 'commutator', label: 'Commutator\n[A,B] = Δ', x: 50, y: 52, type: 'core' },
  { id: 'mode-selector', label: 'Mode Selector\n+ Trust Decision', x: 50, y: 68, type: 'process' },
  { id: 'exploit', label: 'EXPLOIT\nDirect', x: 20, y: 85, type: 'mode-exploit' },
  { id: 'adaptive', label: 'ADAPTIVE\nBalanced', x: 50, y: 85, type: 'mode-adaptive' },
  { id: 'explore', label: 'EXPLORE\nMultiple', x: 80, y: 85, type: 'mode-explore' },
];

const connections = [
  { from: 'query', to: 'classifier' },
  { from: 'classifier', to: 'operator-a' },
  { from: 'classifier', to: 'operator-b' },
  { from: 'operator-a', to: 'commutator' },
  { from: 'operator-b', to: 'commutator' },
  { from: 'commutator', to: 'mode-selector' },
  { from: 'mode-selector', to: 'exploit' },
  { from: 'mode-selector', to: 'adaptive' },
  { from: 'mode-selector', to: 'explore' },
];

export default function SystemArchitecture() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section ref={ref} className="py-24 bg-white">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-[#1D1D1F] mb-4">
            System Architecture
          </h2>
          <p className="text-xl text-[#6E6E73] max-w-2xl mx-auto">
            A quantum-inspired pipeline for multi-perspective knowledge retrieval
          </p>
        </motion.div>

        {/* Architecture diagram */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ delay: 0.3 }}
          className="relative aspect-[4/3] max-w-4xl mx-auto"
        >
          <svg
            viewBox="0 0 100 100"
            className="w-full h-full"
            preserveAspectRatio="xMidYMid meet"
          >
            {/* Definitions */}
            <defs>
              {/* Gradients */}
              <linearGradient id="operatorAGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.1" />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.2" />
              </linearGradient>
              <linearGradient id="operatorBGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#10B981" stopOpacity="0.1" />
                <stop offset="100%" stopColor="#10B981" stopOpacity="0.2" />
              </linearGradient>
              <linearGradient id="coreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#667EEA" stopOpacity="0.1" />
                <stop offset="100%" stopColor="#764BA2" stopOpacity="0.2" />
              </linearGradient>

              {/* Arrow marker */}
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#86868B" />
              </marker>
            </defs>

            {/* Connection lines */}
            {connections.map((conn, index) => {
              const from = architectureNodes.find((n) => n.id === conn.from)!;
              const to = architectureNodes.find((n) => n.id === conn.to)!;

              return (
                <motion.line
                  key={`${conn.from}-${conn.to}`}
                  x1={from.x}
                  y1={from.y + 5}
                  x2={to.x}
                  y2={to.y - 3}
                  stroke="#E5E5E7"
                  strokeWidth="0.5"
                  markerEnd="url(#arrowhead)"
                  initial={{ pathLength: 0 }}
                  animate={isInView ? { pathLength: 1 } : {}}
                  transition={{ delay: 0.5 + index * 0.1, duration: 0.5 }}
                />
              );
            })}

            {/* Bridge connection between operators */}
            <motion.path
              d="M 35 38 Q 50 42 65 38"
              fill="none"
              stroke="#FFD700"
              strokeWidth="0.5"
              strokeDasharray="2 2"
              initial={{ pathLength: 0 }}
              animate={isInView ? { pathLength: 1 } : {}}
              transition={{ delay: 1.2, duration: 0.5 }}
            />
            <motion.text
              x="50"
              y="44"
              textAnchor="middle"
              className="text-[2.5px] fill-[#D97706]"
              initial={{ opacity: 0 }}
              animate={isInView ? { opacity: 1 } : {}}
              transition={{ delay: 1.5 }}
            >
              Bridge Seeds
            </motion.text>

            {/* Nodes */}
            {architectureNodes.map((node, index) => (
              <ArchitectureNode
                key={node.id}
                node={node}
                isInView={isInView}
                delay={0.3 + index * 0.1}
              />
            ))}
          </svg>
        </motion.div>

        {/* Legend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 1.5 }}
          className="flex flex-wrap justify-center gap-6 mt-12"
        >
          <LegendItem color="#3B82F6" label="Structure-First (Operator A)" />
          <LegendItem color="#10B981" label="Narrative-First (Operator B)" />
          <LegendItem color="#FFD700" label="Bridge Connections" />
        </motion.div>
      </div>
    </section>
  );
}

function ArchitectureNode({
  node,
  isInView,
  delay,
}: {
  node: (typeof architectureNodes)[0];
  isInView: boolean;
  delay: number;
}) {
  const getStyles = () => {
    switch (node.type) {
      case 'operator-a':
        return {
          fill: 'url(#operatorAGrad)',
          stroke: '#3B82F6',
          textColor: '#3B82F6',
        };
      case 'operator-b':
        return {
          fill: 'url(#operatorBGrad)',
          stroke: '#10B981',
          textColor: '#10B981',
        };
      case 'core':
        return {
          fill: 'url(#coreGrad)',
          stroke: '#667EEA',
          textColor: '#667EEA',
        };
      case 'mode-exploit':
        return {
          fill: '#3B82F610',
          stroke: '#3B82F6',
          textColor: '#3B82F6',
        };
      case 'mode-adaptive':
        return {
          fill: '#F59E0B10',
          stroke: '#F59E0B',
          textColor: '#F59E0B',
        };
      case 'mode-explore':
        return {
          fill: '#8B5CF610',
          stroke: '#8B5CF6',
          textColor: '#8B5CF6',
        };
      default:
        return {
          fill: '#F5F5F7',
          stroke: '#E5E5E7',
          textColor: '#1D1D1F',
        };
    }
  };

  const styles = getStyles();
  const lines = node.label.split('\n');

  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.8 }}
      animate={isInView ? { opacity: 1, scale: 1 } : {}}
      transition={{ delay, duration: 0.4 }}
    >
      <rect
        x={node.x - 12}
        y={node.y - 4}
        width={24}
        height={lines.length > 1 ? 10 : 8}
        rx={2}
        fill={styles.fill}
        stroke={styles.stroke}
        strokeWidth="0.3"
      />
      {lines.map((line, i) => (
        <text
          key={i}
          x={node.x}
          y={node.y + (lines.length > 1 ? i * 3.5 : 1)}
          textAnchor="middle"
          dominantBaseline="middle"
          className="text-[2.5px] font-medium"
          fill={styles.textColor}
        >
          {line}
        </text>
      ))}
    </motion.g>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-4 h-4 rounded"
        style={{ backgroundColor: `${color}20`, border: `2px solid ${color}` }}
      />
      <span className="text-sm text-[#6E6E73]">{label}</span>
    </div>
  );
}
