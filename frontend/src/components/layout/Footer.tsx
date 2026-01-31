'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Zap, Github, Linkedin, FileText, ArrowUpRight } from 'lucide-react';

const footerLinks = {
  features: [
    { name: 'Dual Operators', href: '/features/dual-operators' },
    { name: 'The Commutator', href: '/features/commutator' },
    { name: 'Mode Selection', href: '/features/mode-selection' },
    { name: 'Trust Decision', href: '/features/trust-decision' },
    { name: 'Graph Construction', href: '/features/graph-construction' },
  ],
  resources: [
    { name: 'Live Demo', href: '/demo' },
    { name: 'Architecture', href: '/architecture' },
    { name: 'Metrics', href: '/metrics' },
    { name: 'Research Paper', href: '/paper' },
  ],
  team: [
    { name: 'About Us', href: '/team' },
    { name: 'SP Jain Global', href: 'https://www.spjain.org', external: true },
  ],
};

export default function Footer() {
  return (
    <footer className="relative bg-[#1D1D1F] text-white overflow-hidden">
      {/* Gradient overlay */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#667EEA] rounded-full blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-[#764BA2] rounded-full blur-[128px]" />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 py-16">
        {/* Top Section */}
        <div className="grid lg:grid-cols-5 gap-12 lg:gap-8">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="inline-flex items-center gap-3 group">
              <motion.div
                className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center"
                whileHover={{ scale: 1.05, rotate: 5 }}
              >
                <Zap className="w-6 h-6 text-white" />
              </motion.div>
              <div>
                <span className="font-bold text-xl">OpMech-GraphRAG</span>
              </div>
            </Link>
            <p className="mt-4 text-white/60 text-sm leading-relaxed max-w-sm">
              Multi-Perspective Knowledge Retrieval Through Quantum-Inspired Operator Mechanics.
              A novel approach combining dual operators with commutator-guided explore/exploit strategies.
            </p>
            <div className="flex items-center gap-4 mt-6">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="https://linkedin.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <Linkedin className="w-5 h-5" />
              </a>
              <a
                href="/paper"
                className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <FileText className="w-5 h-5" />
              </a>
            </div>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-white/40 mb-4">
              Features
            </h4>
            <ul className="space-y-3">
              {footerLinks.features.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-white/70 hover:text-white text-sm transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-white/40 mb-4">
              Resources
            </h4>
            <ul className="space-y-3">
              {footerLinks.resources.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-white/70 hover:text-white text-sm transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-white/40 mb-4">
              Team
            </h4>
            <ul className="space-y-3">
              {footerLinks.team.map((link) => (
                <li key={link.href}>
                  {'external' in link && link.external ? (
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-white/70 hover:text-white text-sm transition-colors"
                    >
                      {link.name}
                      <ArrowUpRight className="w-3 h-3" />
                    </a>
                  ) : (
                    <Link
                      href={link.href}
                      className="text-white/70 hover:text-white text-sm transition-colors"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="mt-16 pt-8 border-t border-white/10 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-white/40 text-sm">
            © {new Date().getFullYear()} OpMech-GraphRAG. SP Jain School of Global Management.
          </p>
          <p className="text-white/40 text-sm">
            Master&apos;s in AI in Business • Dubai Campus
          </p>
        </div>
      </div>
    </footer>
  );
}
