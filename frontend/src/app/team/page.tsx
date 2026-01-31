'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Users,
  Github,
  Linkedin,
  Mail,
  GraduationCap,
  Building2,
  BookOpen,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// Team Members
const teamMembers = [
  {
    name: 'Divyansh Maiwar Singh',
    role: 'Lead Developer',
    avatar: 'DM',
    color: '#667EEA',
    bio: 'Full-stack developer specializing in AI/ML systems and graph databases.',
    focus: ['System Architecture', 'GraphRAG', 'LLM Integration'],
    links: {
      github: 'https://github.com',
      linkedin: 'https://linkedin.com',
    },
  },
  {
    name: 'Dharmik Kothari',
    role: 'ML Engineer',
    avatar: 'DK',
    color: '#10B981',
    bio: 'Machine learning specialist focused on NLP and knowledge graph construction.',
    focus: ['MoE Experts', 'Graph Construction', 'NLP'],
    links: {
      github: 'https://github.com',
      linkedin: 'https://linkedin.com',
    },
  },
  {
    name: 'Agastya Shetty',
    role: 'Research Engineer',
    avatar: 'AS',
    color: '#8B5CF6',
    bio: 'Research engineer working on dual-operator mechanics and divergence analysis.',
    focus: ['Operator Design', 'Commutator', 'Research'],
    links: {
      github: 'https://github.com',
      linkedin: 'https://linkedin.com',
    },
  },
  {
    name: 'Dhruvish Shah',
    role: 'Data Engineer',
    avatar: 'DS',
    color: '#F59E0B',
    bio: 'Data engineer specializing in SEC filings processing and XBRL extraction.',
    focus: ['Data Pipeline', 'XBRL Parsing', 'Neo4j'],
    links: {
      github: 'https://github.com',
      linkedin: 'https://linkedin.com',
    },
  },
];

// Advisors/Mentors
const advisors = [
  {
    name: 'Research Advisor',
    role: 'Faculty Advisor',
    institution: 'University',
    avatar: 'RA',
    color: '#10B981',
  },
];

// Tech Stack Contributors
const technologies = [
  { name: 'Neo4j', role: 'Graph Database', logo: '🔗' },
  { name: 'vLLM', role: 'LLM Inference', logo: '🚀' },
  { name: 'Next.js', role: 'Frontend Framework', logo: '▲' },
  { name: 'FastAPI', role: 'Backend API', logo: '⚡' },
  { name: 'Qwen', role: 'Language Model', logo: '🤖' },
  { name: 'Three.js', role: '3D Visualization', logo: '🎨' },
];

// Team Member Card
function TeamMemberCard({
  member,
  index,
}: {
  member: (typeof teamMembers)[0];
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1 }}
      className="bg-white rounded-2xl p-6 shadow-sm border border-[#E5E7EB] text-center"
    >
      {/* Avatar */}
      <div
        className="w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl font-bold text-white"
        style={{ background: `linear-gradient(135deg, ${member.color}, ${member.color}CC)` }}
      >
        {member.avatar}
      </div>

      {/* Name & Role */}
      <h3 className="font-bold text-xl mb-1">{member.name}</h3>
      <div className="text-[#667EEA] font-medium mb-3">{member.role}</div>

      {/* Bio */}
      <p className="text-[#6E6E73] text-sm mb-4">{member.bio}</p>

      {/* Focus Areas */}
      <div className="flex flex-wrap gap-2 justify-center mb-4">
        {member.focus.map((area) => (
          <span
            key={area}
            className="px-3 py-1 text-xs rounded-full bg-[#F5F5F7] text-[#6E6E73]"
          >
            {area}
          </span>
        ))}
      </div>

      {/* Links */}
      <div className="flex justify-center gap-3">
        {member.links.github && (
          <a
            href={member.links.github}
            target="_blank"
            rel="noopener noreferrer"
            className="w-10 h-10 rounded-full bg-[#F5F5F7] flex items-center justify-center hover:bg-[#667EEA] hover:text-white transition-colors"
          >
            <Github className="w-5 h-5" />
          </a>
        )}
        {member.links.linkedin && (
          <a
            href={member.links.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            className="w-10 h-10 rounded-full bg-[#F5F5F7] flex items-center justify-center hover:bg-[#0077B5] hover:text-white transition-colors"
          >
            <Linkedin className="w-5 h-5" />
          </a>
        )}
      </div>
    </motion.div>
  );
}

// Main Page
export default function TeamPage() {
  return (
    <PageWrapper>
      {/* Header */}
      <Section className="pt-24 pb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-2xl bg-[#667EEA]/10 flex items-center justify-center">
              <Users className="w-8 h-8 text-[#667EEA]" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-bold">The Team</h1>
              <p className="text-xl text-[#6E6E73] mt-1">
                Building the future of financial AI
              </p>
            </div>
          </div>
        </motion.div>
      </Section>

      {/* Mission Statement */}
      <Section className="!pt-0">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-[#667EEA]/5 to-[#764BA2]/5 rounded-2xl p-8 mb-12 text-center"
        >
          <GraduationCap className="w-12 h-12 mx-auto mb-4 text-[#667EEA]" />
          <h2 className="text-2xl font-bold mb-4">Our Mission</h2>
          <p className="text-lg text-[#6E6E73] max-w-2xl mx-auto">
            To create transparent, trustworthy AI systems for financial analysis
            that combine the power of large language models with the precision
            of graph-based reasoning.
          </p>
        </motion.div>
      </Section>

      {/* Core Team */}
      <Section className="bg-[#F5F5F7]">
        <h2 className="text-3xl font-bold text-center mb-12">Core Team</h2>

        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {teamMembers.map((member, idx) => (
            <TeamMemberCard key={member.name} member={member} index={idx} />
          ))}
        </div>
      </Section>

      {/* Acknowledgments */}
      <Section>
        <h2 className="text-3xl font-bold text-center mb-4">Acknowledgments</h2>
        <p className="text-center text-[#6E6E73] mb-12 max-w-2xl mx-auto">
          Special thanks to the open-source community and the following
          technologies that make OpMech-GraphRAG possible.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-4xl mx-auto">
          {technologies.map((tech, idx) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.05 }}
              className="bg-white rounded-xl p-4 text-center shadow-sm border border-[#E5E7EB] hover:shadow-md transition-shadow"
            >
              <div className="text-3xl mb-2">{tech.logo}</div>
              <div className="font-medium text-sm">{tech.name}</div>
              <div className="text-xs text-[#6E6E73]">{tech.role}</div>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* Project Info */}
      <Section className="bg-[#F5F5F7]">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            About the Project
          </h2>

          <div className="grid md:grid-cols-2 gap-8">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-white rounded-2xl p-6 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#667EEA]/10 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-[#667EEA]" />
                </div>
                <h3 className="font-bold">Research Background</h3>
              </div>
              <p className="text-[#6E6E73] text-sm">
                OpMech-GraphRAG is developed as part of an academic research
                project exploring the intersection of graph neural networks,
                large language models, and financial document understanding.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-white rounded-2xl p-6 shadow-sm"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#10B981]/10 flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-[#10B981]" />
                </div>
                <h3 className="font-bold">Open Source</h3>
              </div>
              <p className="text-[#6E6E73] text-sm">
                The project is open-source and welcomes contributions from the
                community. Our goal is to advance the state-of-the-art in
                transparent, trustworthy AI for financial applications.
              </p>
            </motion.div>
          </div>
        </div>
      </Section>

      {/* Contact CTA */}
      <Section className="bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Get in Touch</h2>
          <p className="text-xl opacity-90 mb-8">
            Interested in collaborating or learning more about OpMech-GraphRAG?
            We&apos;d love to hear from you.
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[#1D1D1F] rounded-full font-semibold hover:shadow-lg transition-all"
            >
              <Github className="w-5 h-5" />
              View on GitHub
            </a>
            <a
              href="mailto:contact@example.com"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white/20 text-white rounded-full font-semibold hover:bg-white/30 transition-all"
            >
              <Mail className="w-5 h-5" />
              Contact Us
            </a>
          </div>
        </div>
      </Section>

      {/* Navigation */}
      <Section className="!py-12">
        <div className="flex justify-between items-center">
          <Link
            href="/metrics"
            className="flex items-center gap-2 text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Metrics
          </Link>
          <Link
            href="/demo"
            className="flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all"
          >
            Try the Demo
            <span className="text-xl">→</span>
          </Link>
        </div>
      </Section>
    </PageWrapper>
  );
}
