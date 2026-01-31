'use client';

import { motion } from 'framer-motion';
import Navigation from './Navigation';
import Footer from './Footer';

interface PageWrapperProps {
  children: React.ReactNode;
  showFooter?: boolean;
  className?: string;
}

export default function PageWrapper({
  children,
  showFooter = true,
  className = '',
}: PageWrapperProps) {
  return (
    <>
      <Navigation />
      <motion.main
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className={`min-h-screen pt-16 ${className}`}
      >
        {children}
      </motion.main>
      {showFooter && <Footer />}
    </>
  );
}

// Section component for consistent spacing and animations
interface SectionProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
  dark?: boolean;
}

export function Section({ children, className = '', id, dark = false }: SectionProps) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className={`py-20 md:py-32 ${dark ? 'bg-[#1D1D1F] text-white' : ''} ${className}`}
    >
      <div className="max-w-7xl mx-auto px-6">
        {children}
      </div>
    </motion.section>
  );
}

// Page header component
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: string;
  centered?: boolean;
}

export function PageHeader({ title, subtitle, badge, centered = true }: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className={`${centered ? 'text-center' : ''} mb-16`}
    >
      {badge && (
        <motion.span
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="inline-block px-4 py-1.5 bg-gradient-to-r from-[#667EEA]/10 to-[#764BA2]/10 text-[#667EEA] text-sm font-semibold rounded-full mb-4"
        >
          {badge}
        </motion.span>
      )}
      <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">
        <span className="gradient-text">{title}</span>
      </h1>
      {subtitle && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-6 text-lg md:text-xl text-[#6E6E73] max-w-3xl mx-auto"
        >
          {subtitle}
        </motion.p>
      )}
    </motion.div>
  );
}

// Feature card component
interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  href?: string;
  delay?: number;
}

export function FeatureCard({ icon, title, description, href, delay = 0 }: FeatureCardProps) {
  const content = (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -4 }}
      className="group relative bg-white rounded-2xl p-8 shadow-sm border border-black/5 hover:shadow-xl hover:border-[#667EEA]/20 transition-all duration-300 cursor-pointer"
    >
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#667EEA] to-[#764BA2] rounded-t-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#667EEA]/10 to-[#764BA2]/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
        {icon}
      </div>
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <p className="text-[#6E6E73] leading-relaxed">{description}</p>
    </motion.div>
  );

  if (href) {
    return (
      <a href={href} className="block">
        {content}
      </a>
    );
  }

  return content;
}

// Stats card component
interface StatCardProps {
  value: string;
  label: string;
  delay?: number;
}

export function StatCard({ value, label, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="text-center"
    >
      <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">{value}</div>
      <div className="text-sm text-[#6E6E73] uppercase tracking-wider">{label}</div>
    </motion.div>
  );
}
