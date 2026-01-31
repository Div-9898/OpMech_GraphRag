'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  Menu,
  X,
  Zap,
  GitBranch,
  Gauge,
  Target,
  Shield,
  Network,
  Play,
  Layers,
  BarChart3,
  Users,
  BookOpen,
  AlertTriangle,
} from 'lucide-react';

const navigation = [
  { name: 'Home', href: '/' },
  { name: 'How It Works', href: '/how-it-works', icon: BookOpen },
  {
    name: 'Features',
    href: '/features',
    children: [
      { name: 'Dual Operators', href: '/features/dual-operators', icon: GitBranch, description: 'Two perspectives, one truth' },
      { name: 'The Commutator', href: '/features/commutator', icon: Gauge, description: 'Measuring divergence' },
      { name: 'Mode Selection', href: '/features/mode-selection', icon: Target, description: 'EXPLOIT, ADAPTIVE, EXPLORE' },
      { name: 'Trust Decision', href: '/features/trust-decision', icon: Shield, description: 'Evidence authority' },
      { name: 'Graph Construction', href: '/features/graph-construction', icon: Network, description: '7 specialized experts' },
    ],
  },
  { name: 'Demo', href: '/demo', icon: Play },
  { name: 'Architecture', href: '/architecture', icon: Layers },
  { name: 'Metrics', href: '/metrics', icon: BarChart3 },
  { name: 'Team', href: '/team', icon: Users },
  { name: 'Limitations', href: '/limitations', icon: AlertTriangle },
];

export default function Navigation() {
  const pathname = usePathname();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <>
      <motion.nav
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? 'bg-white/80 backdrop-blur-xl border-b border-black/5 shadow-sm'
            : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group">
              <motion.div
                className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center"
                whileHover={{ scale: 1.05, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
              >
                <Zap className="w-5 h-5 text-white" />
                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-[#667EEA] to-[#764BA2] blur-lg opacity-50 group-hover:opacity-75 transition-opacity" />
              </motion.div>
              <div className="hidden sm:block">
                <span className="font-bold text-lg tracking-tight">OpMech</span>
                <span className="text-[#6E6E73] text-sm ml-1">GraphRAG</span>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden lg:flex items-center gap-1">
              {navigation.map((item) => (
                <div
                  key={item.name}
                  className="relative"
                  onMouseEnter={() => item.children && setOpenDropdown(item.name)}
                  onMouseLeave={() => setOpenDropdown(null)}
                >
                  <Link
                    href={item.href}
                    className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-[15px] font-medium transition-all ${
                      isActive(item.href)
                        ? 'text-[#667EEA] bg-[#667EEA]/5'
                        : 'text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-black/5'
                    }`}
                  >
                    {item.name}
                    {item.children && (
                      <ChevronDown
                        className={`w-4 h-4 transition-transform ${
                          openDropdown === item.name ? 'rotate-180' : ''
                        }`}
                      />
                    )}
                  </Link>

                  {/* Dropdown Menu */}
                  <AnimatePresence>
                    {item.children && openDropdown === item.name && (
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute top-full left-0 pt-2 w-72"
                      >
                        <div className="bg-white rounded-2xl shadow-xl border border-black/5 p-2 overflow-hidden">
                          {item.children.map((child, idx) => {
                            const Icon = child.icon;
                            return (
                              <Link
                                key={child.href}
                                href={child.href}
                                className={`flex items-start gap-3 p-3 rounded-xl transition-all ${
                                  isActive(child.href)
                                    ? 'bg-[#667EEA]/10'
                                    : 'hover:bg-black/5'
                                }`}
                              >
                                <div
                                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                                    isActive(child.href)
                                      ? 'bg-[#667EEA] text-white'
                                      : 'bg-[#F5F5F7] text-[#6E6E73]'
                                  }`}
                                >
                                  <Icon className="w-5 h-5" />
                                </div>
                                <div>
                                  <div className="font-semibold text-[#1D1D1F] text-sm">
                                    {child.name}
                                  </div>
                                  <div className="text-xs text-[#6E6E73] mt-0.5">
                                    {child.description}
                                  </div>
                                </div>
                              </Link>
                            );
                          })}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>

            {/* CTA Button */}
            <div className="hidden lg:flex items-center gap-4">
              <Link
                href="/demo"
                className="relative group px-5 py-2.5 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white text-sm font-semibold rounded-full overflow-hidden"
              >
                <span className="relative z-10">Try Demo</span>
                <div className="absolute inset-0 bg-gradient-to-r from-[#764BA2] to-[#667EEA] opacity-0 group-hover:opacity-100 transition-opacity" />
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-black/5 transition-colors"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 lg:hidden"
          >
            <div
              className="absolute inset-0 bg-black/20 backdrop-blur-sm"
              onClick={() => setIsMobileMenuOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute right-0 top-0 bottom-0 w-80 bg-white shadow-2xl"
            >
              <div className="p-6 pt-20">
                <div className="space-y-1">
                  {navigation.map((item) => (
                    <div key={item.name}>
                      <Link
                        href={item.href}
                        onClick={() => !item.children && setIsMobileMenuOpen(false)}
                        className={`flex items-center justify-between p-3 rounded-xl text-[15px] font-medium transition-all ${
                          isActive(item.href)
                            ? 'text-[#667EEA] bg-[#667EEA]/5'
                            : 'text-[#1D1D1F] hover:bg-black/5'
                        }`}
                      >
                        {item.name}
                        {item.children && <ChevronDown className="w-4 h-4" />}
                      </Link>
                      {item.children && (
                        <div className="ml-4 mt-1 space-y-1">
                          {item.children.map((child) => {
                            const Icon = child.icon;
                            return (
                              <Link
                                key={child.href}
                                href={child.href}
                                onClick={() => setIsMobileMenuOpen(false)}
                                className={`flex items-center gap-3 p-2.5 rounded-lg text-sm transition-all ${
                                  isActive(child.href)
                                    ? 'text-[#667EEA] bg-[#667EEA]/5'
                                    : 'text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-black/5'
                                }`}
                              >
                                <Icon className="w-4 h-4" />
                                {child.name}
                              </Link>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="mt-8 pt-8 border-t border-black/5">
                  <Link
                    href="/demo"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="block w-full py-3 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white text-center font-semibold rounded-xl"
                  >
                    Try Live Demo
                  </Link>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
