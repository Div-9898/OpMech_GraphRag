'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Sparkles, ExternalLink } from 'lucide-react';

const teamMembers = [
  { name: 'Divyansh Maiwar Singh', initials: 'DM' },
  { name: 'Dhruvish Shah', initials: 'DS' },
  { name: 'Dharmik Kothari', initials: 'DK' },
  { name: 'Agastya Shetty', initials: 'AS' },
];

const highlights = [
  'First commutator-based divergence measurement for GraphRAG',
  'Novel dual-operator architecture for multi-perspective retrieval',
  'Intelligent mode selection (EXPLOIT/ADAPTIVE/EXPLORE)',
  'Query-aware trust decisions for numerical accuracy',
  '93% traversal reduction through smart edge scoring',
];

export default function TeamSection() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section ref={ref} className="py-24 bg-[#F5F5F7]">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-[#1D1D1F] mb-4">Team</h2>
          <p className="text-xl text-[#6E6E73]">
            OpMech-GraphRAG: Multi-Perspective Knowledge Retrieval
            <br />
            Through Quantum-Inspired Operator Mechanics
          </p>
        </motion.div>

        {/* Team members */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {teamMembers.map((member, index) => (
            <motion.div
              key={member.name}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: 0.2 + index * 0.1 }}
              className="team-card"
            >
              <div className="team-avatar">{member.initials}</div>
              <h3 className="text-lg font-semibold text-[#1D1D1F]">{member.name}</h3>
            </motion.div>
          ))}
        </div>

        {/* Institution */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-lg font-medium text-[#1D1D1F]">SP Jain School of Global Management</p>
          <p className="text-[#6E6E73]">Master&apos;s in AI in Business</p>
        </motion.div>

        {/* Divider */}
        <div className="border-t border-black/10 mb-16" />

        {/* Research highlights */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.7 }}
        >
          <h3 className="text-2xl font-bold text-[#1D1D1F] text-center mb-8">
            Research Highlights
          </h3>

          <div className="max-w-3xl mx-auto space-y-4">
            {highlights.map((highlight, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: 0.8 + index * 0.1 }}
                className="flex items-start gap-4 p-4 rounded-xl bg-white/60 border border-black/5"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <p className="text-[#1D1D1F]">{highlight}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 1.3 }}
          className="text-center mt-12"
        >
          <a
            href="#"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white font-semibold hover:shadow-lg transition-all hover:scale-105"
          >
            <span>View Paper</span>
            <ExternalLink className="w-4 h-4" />
          </a>
        </motion.div>
      </div>
    </section>
  );
}
