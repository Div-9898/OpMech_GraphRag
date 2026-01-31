'use client';

import { useRef, useEffect, useState, Suspense, useMemo } from 'react';
import Link from 'next/link';
import { motion, useScroll, useTransform, useInView } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Float, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';
import {
  GitBranch,
  Gauge,
  Target,
  Shield,
  ChevronRight,
  Play,
  ArrowRight,
  Sparkles,
  TrendingDown,
  FileText,
  Scale,
  Search,
  BarChart,
  MousePointer,
  Zap,
} from 'lucide-react';
import { PageWrapper, Section } from '@/components/layout';

// ═══════════════════════════════════════════════════════════════════════════
// Hero 3D Scene - Animated Knowledge Graph
// ═══════════════════════════════════════════════════════════════════════════

// Deterministic pseudo-random function to avoid hydration mismatch
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9999) * 10000;
  return x - Math.floor(x);
}

function HeroGraph() {
  const groupRef = useRef<THREE.Group>(null);
  const nodesA = useRef<THREE.InstancedMesh>(null);
  const nodesB = useRef<THREE.InstancedMesh>(null);

  // Use useMemo with deterministic seeded random to avoid hydration mismatch
  const positions = useMemo(() => {
    const posA: [number, number, number][] = [];
    const posB: [number, number, number][] = [];
    for (let i = 0; i < 20; i++) {
      posA.push([
        (seededRandom(i * 3) - 0.5) * 4,
        (seededRandom(i * 3 + 1) - 0.5) * 4,
        (seededRandom(i * 3 + 2) - 0.5) * 4,
      ]);
      posB.push([
        (seededRandom(i * 3 + 60) - 0.5) * 4,
        (seededRandom(i * 3 + 61) - 0.5) * 4,
        (seededRandom(i * 3 + 62) - 0.5) * 4,
      ]);
    }
    return { posA, posB };
  }, []);

  useFrame(({ clock }) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(clock.elapsedTime * 0.1) * 0.3;
      groupRef.current.rotation.x = Math.cos(clock.elapsedTime * 0.1) * 0.1;
    }

    const dummy = new THREE.Object3D();
    if (nodesA.current) {
      positions.posA.forEach((pos, i) => {
        dummy.position.set(
          pos[0] + Math.sin(clock.elapsedTime + i) * 0.1,
          pos[1] + Math.cos(clock.elapsedTime + i) * 0.1,
          pos[2]
        );
        dummy.scale.setScalar(0.08 + Math.sin(clock.elapsedTime * 2 + i) * 0.02);
        dummy.updateMatrix();
        nodesA.current!.setMatrixAt(i, dummy.matrix);
      });
      nodesA.current.instanceMatrix.needsUpdate = true;
    }

    if (nodesB.current) {
      positions.posB.forEach((pos, i) => {
        dummy.position.set(
          pos[0] + Math.sin(clock.elapsedTime + i + Math.PI) * 0.1,
          pos[1] + Math.cos(clock.elapsedTime + i + Math.PI) * 0.1,
          pos[2]
        );
        dummy.scale.setScalar(0.08 + Math.sin(clock.elapsedTime * 2 + i + Math.PI) * 0.02);
        dummy.updateMatrix();
        nodesB.current!.setMatrixAt(i, dummy.matrix);
      });
      nodesB.current.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <group ref={groupRef}>
      <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
        <Sphere args={[0.5, 64, 64]}>
          <MeshDistortMaterial
            color="#667EEA"
            attach="material"
            distort={0.4}
            speed={2}
            roughness={0.1}
            metalness={0.8}
          />
        </Sphere>
      </Float>

      <instancedMesh ref={nodesA} args={[undefined, undefined, 20]}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial color="#3B82F6" emissive="#3B82F6" emissiveIntensity={0.5} />
      </instancedMesh>

      <instancedMesh ref={nodesB} args={[undefined, undefined, 20]}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial color="#10B981" emissive="#10B981" emissiveIntensity={0.5} />
      </instancedMesh>

      {positions.posA.slice(0, 10).map((posA, i) => {
        const posB = positions.posB[i];
        return (
          <line key={i}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[new Float32Array([...posA, ...posB]), 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#FFD700" opacity={0.3} transparent />
          </line>
        );
      })}

      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array(Array.from({ length: 600 }, (_, i) => (seededRandom(i * 7 + 200) - 0.5) * 10)), 3]}
          />
        </bufferGeometry>
        <pointsMaterial size={0.02} color="#FFFFFF" transparent opacity={0.4} sizeAttenuation />
      </points>
    </group>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Animated Counter Component
// ═══════════════════════════════════════════════════════════════════════════

function AnimatedCounter({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (isInView) {
      const duration = 2000;
      const start = Date.now();
      const animate = () => {
        const elapsed = Date.now() - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setCount(Math.floor(eased * value));
        if (progress < 1) requestAnimationFrame(animate);
      };
      animate();
    }
  }, [isInView, value]);

  return (
    <span ref={ref}>
      {count.toLocaleString()}
      {suffix}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Data
// ═══════════════════════════════════════════════════════════════════════════

const features = [
  {
    icon: GitBranch,
    title: 'Dual Operators',
    description: 'Two complementary operators explore knowledge from different angles - structure-first and narrative-first.',
    href: '/features/dual-operators',
    color: '#3B82F6',
  },
  {
    icon: Gauge,
    title: 'The Commutator',
    description: 'Quantum-inspired divergence measurement reveals when perspectives agree or conflict.',
    href: '/features/commutator',
    color: '#8B5CF6',
  },
  {
    icon: Target,
    title: 'Mode Selection',
    description: 'Intelligent switching between EXPLOIT, ADAPTIVE, and EXPLORE based on real-time divergence.',
    href: '/features/mode-selection',
    color: '#F59E0B',
  },
  {
    icon: Shield,
    title: 'Trust Decision',
    description: 'Evidence authority hierarchy ensures numerical accuracy while preserving contextual insights.',
    href: '/features/trust-decision',
    color: '#10B981',
  },
];

const useCases = [
  { icon: BarChart, title: 'Financial Analysis', description: 'Extract precise figures with full context' },
  { icon: Search, title: 'Due Diligence', description: 'Multi-perspective risk assessment' },
  { icon: Scale, title: 'Regulatory Compliance', description: 'Accurate regulatory data retrieval' },
  { icon: TrendingDown, title: 'Risk Assessment', description: 'Comprehensive risk factor analysis' },
  { icon: FileText, title: 'Research Q&A', description: 'Deep document understanding' },
  { icon: Sparkles, title: 'Document Intelligence', description: 'Smart document exploration' },
];

// ═══════════════════════════════════════════════════════════════════════════
// Main Page Component
// ═══════════════════════════════════════════════════════════════════════════

export default function HomePage() {
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });

  const heroOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.5], [1, 0.95]);
  const heroY = useTransform(scrollYProgress, [0, 0.5], [0, 100]);

  return (
    <PageWrapper>
      {/* Hero Section */}
      <section ref={heroRef} className="relative min-h-screen flex items-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#F5F5F7] via-white to-[#F5F5F7]" />
        <div className="absolute inset-0 opacity-50">
          <div className="absolute top-20 left-10 w-[500px] h-[500px] bg-[#667EEA]/10 rounded-full blur-[100px]" />
          <div className="absolute bottom-20 right-10 w-[600px] h-[600px] bg-[#764BA2]/10 rounded-full blur-[100px]" />
        </div>

        <motion.div
          style={{ opacity: heroOpacity, scale: heroScale, y: heroY }}
          className="relative z-10 max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center"
        >
          <div className="text-center lg:text-left">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#667EEA]/10 to-[#764BA2]/10 rounded-full mb-6"
            >
              <Sparkles className="w-4 h-4 text-[#667EEA]" />
              <span className="text-sm font-semibold text-[#667EEA]">Quantum-Inspired GraphRAG</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1]"
            >
              <span className="gradient-text">OpMech</span>
              <br />
              <span className="text-[#1D1D1F]">GraphRAG</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="mt-6 text-xl text-[#6E6E73] max-w-xl mx-auto lg:mx-0"
            >
              Multi-Perspective Knowledge Retrieval Through Quantum-Inspired Operator Mechanics
            </motion.p>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="mt-4 text-lg text-[#86868B] italic"
            >
              &ldquo;When two perspectives converge, truth emerges&rdquo;
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="mt-10 flex flex-wrap gap-4 justify-center lg:justify-start"
            >
              <Link
                href="/demo"
                className="group inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-[#667EEA] to-[#764BA2] text-white font-semibold rounded-full shadow-lg shadow-[#667EEA]/30 hover:shadow-xl hover:shadow-[#667EEA]/40 transition-all hover:-translate-y-0.5"
              >
                <Play className="w-5 h-5" />
                Try Live Demo
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/features"
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-[#1D1D1F] font-semibold rounded-full border border-black/10 hover:bg-[#F5F5F7] transition-all"
              >
                Explore Features
                <ChevronRight className="w-4 h-4" />
              </Link>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.6 }}
              className="mt-6 flex justify-center lg:justify-start"
            >
              <Link
                href="/how-it-works"
                className="inline-flex items-center gap-2 text-[#6E6E73] hover:text-[#667EEA] transition-colors group"
              >
                <span className="text-lg">🔍</span>
                <span className="text-sm font-medium underline underline-offset-2 decoration-dotted">
                  Explain it like I&apos;m 5
                </span>
                <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
              </Link>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="relative h-[500px] lg:h-[600px]"
          >
            <div className="absolute inset-0 rounded-3xl overflow-hidden bg-gradient-to-br from-[#1a1a2e] to-[#0a0a14]">
              <Suspense fallback={<div className="w-full h-full animate-pulse bg-[#1a1a2e]" />}>
                <Canvas camera={{ position: [0, 0, 6], fov: 50 }}>
                  <ambientLight intensity={0.5} />
                  <pointLight position={[10, 10, 10]} intensity={1} color="#667EEA" />
                  <pointLight position={[-10, -10, -10]} intensity={0.5} color="#10B981" />
                  <HeroGraph />
                  <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
                </Canvas>
              </Suspense>

              <div className="absolute bottom-6 left-6 right-6 flex flex-wrap gap-3">
                <span className="stat-pill flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#3B82F6]" />
                  Operator A
                </span>
                <span className="stat-pill flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#10B981]" />
                  Operator B
                </span>
                <span className="stat-pill flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#FFD700]" />
                  Bridge
                </span>
              </div>
            </div>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <div className="scroll-indicator flex flex-col items-center gap-2 text-[#86868B]">
            <span className="text-xs uppercase tracking-widest">Scroll to explore</span>
            <MousePointer className="w-4 h-4" />
          </div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <Section className="bg-[#1D1D1F] text-white !py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold mb-2">
              <AnimatedCounter value={1737} />
            </div>
            <div className="text-sm text-white/60 uppercase tracking-wider">Nodes</div>
          </div>
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold mb-2">
              <AnimatedCounter value={26842} />
            </div>
            <div className="text-sm text-white/60 uppercase tracking-wider">Edges</div>
          </div>
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold mb-2">
              <AnimatedCounter value={100} suffix="%" />
            </div>
            <div className="text-sm text-white/60 uppercase tracking-wider">Accuracy</div>
          </div>
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold mb-2">
              <AnimatedCounter value={93} suffix="%" />
            </div>
            <div className="text-sm text-white/60 uppercase tracking-wider">Reduction</div>
          </div>
        </div>
      </Section>

      {/* Features Section */}
      <Section>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="inline-block px-4 py-1.5 bg-gradient-to-r from-[#667EEA]/10 to-[#764BA2]/10 text-[#667EEA] text-sm font-semibold rounded-full mb-4">
            Key Features
          </span>
          <h2 className="text-4xl md:text-5xl font-bold">
            <span className="gradient-text">How OpMech Works</span>
          </h2>
          <p className="mt-4 text-lg text-[#6E6E73] max-w-2xl mx-auto">
            A novel approach to knowledge retrieval that combines dual operators with commutator-guided explore/exploit strategies
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, idx) => (
            <motion.a
              key={feature.title}
              href={feature.href}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ y: -4 }}
              className="group relative bg-white rounded-2xl p-8 shadow-sm border border-black/5 hover:shadow-xl hover:border-[#667EEA]/20 transition-all duration-300"
            >
              <div
                className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: `linear-gradient(to right, ${feature.color}, ${feature.color}88)` }}
              />
              <div
                className="w-14 h-14 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform"
                style={{ background: `${feature.color}15` }}
              >
                <feature.icon className="w-7 h-7" style={{ color: feature.color }} />
              </div>
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="text-[#6E6E73] leading-relaxed">{feature.description}</p>
              <div className="mt-4 inline-flex items-center gap-1 text-[#667EEA] font-medium text-sm opacity-0 group-hover:opacity-100 transition-opacity">
                Learn more <ChevronRight className="w-4 h-4" />
              </div>
            </motion.a>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mt-12 text-center"
        >
          <Link href="/features" className="inline-flex items-center gap-2 text-[#667EEA] font-semibold hover:gap-3 transition-all">
            View all features
            <ArrowRight className="w-4 h-4" />
          </Link>
        </motion.div>
      </Section>

      {/* Use Cases Section */}
      <Section className="bg-[#F5F5F7]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="inline-block px-4 py-1.5 bg-white text-[#667EEA] text-sm font-semibold rounded-full mb-4 shadow-sm">
            Use Cases
          </span>
          <h2 className="text-4xl md:text-5xl font-bold">
            What Problems Does <span className="gradient-text">OpMech</span> Solve?
          </h2>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {useCases.map((useCase, idx) => (
            <motion.div
              key={useCase.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#667EEA]/10 to-[#764BA2]/10 flex items-center justify-center mb-4">
                <useCase.icon className="w-6 h-6 text-[#667EEA]" />
              </div>
              <h3 className="font-bold text-lg mb-2">{useCase.title}</h3>
              <p className="text-[#6E6E73] text-sm">{useCase.description}</p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* CTA Section */}
      <Section>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative rounded-3xl bg-gradient-to-br from-[#667EEA] to-[#764BA2] p-12 md:p-16 text-center text-white overflow-hidden"
        >
          <div className="absolute inset-0 opacity-20">
            <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full blur-[100px]" />
            <div className="absolute bottom-0 left-0 w-96 h-96 bg-white rounded-full blur-[100px]" />
          </div>

          <div className="relative z-10">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Ready to Experience the Future of Knowledge Retrieval?
            </h2>
            <p className="text-xl text-white/80 max-w-2xl mx-auto mb-10">
              Watch dual operators explore the knowledge graph in real-time and see how commutator-guided strategies deliver precise answers.
            </p>
            <Link
              href="/demo"
              className="inline-flex items-center gap-3 px-10 py-5 bg-white text-[#667EEA] font-bold text-lg rounded-full shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all"
            >
              <Zap className="w-6 h-6" />
              Launch Live Demo
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </motion.div>
      </Section>
    </PageWrapper>
  );
}
