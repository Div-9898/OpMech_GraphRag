'use client';

import { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Float, Text, Sphere, Line } from '@react-three/drei';
import * as THREE from 'three';
import { motion } from 'framer-motion';
import type { GraphNode, GraphEdge, NodeType, AnimationState } from '@/types';
import { NODE_COLORS } from '@/types';

// Deterministic pseudo-random function to avoid hydration mismatch
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9999) * 10000;
  return x - Math.floor(x);
}

// Generate demo graph data using deterministic random for SSR compatibility
function generateDemoGraph(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodeCount = 200;
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  const nodeTypes: NodeType[] = ['FINANCIAL_LINE', 'TEXT_SECTION', 'NOTE', 'ENTITY'];

  // Generate nodes in clusters
  for (let i = 0; i < nodeCount; i++) {
    const type = nodeTypes[Math.floor(seededRandom(i * 7) * nodeTypes.length)];
    const cluster = Math.floor(i / 50);
    const angle = (i % 50) * (Math.PI * 2) / 50;
    const radius = 30 + seededRandom(i * 11) * 20;

    nodes.push({
      id: `node-${i}`,
      type,
      label: `Node ${i}`,
      position: {
        x: Math.cos(angle) * radius + (cluster % 2) * 60 - 30,
        y: Math.sin(angle) * radius + Math.floor(cluster / 2) * 60 - 30,
        z: (seededRandom(i * 13) - 0.5) * 40,
      },
      score: seededRandom(i * 17),
      isEvidence: seededRandom(i * 19) > 0.9,
    });
  }

  // Generate edges
  for (let i = 0; i < nodeCount * 2; i++) {
    const source = Math.floor(seededRandom(i * 23 + 1000) * nodeCount);
    let target = Math.floor(seededRandom(i * 29 + 2000) * nodeCount);
    if (target === source) target = (target + 1) % nodeCount;

    edges.push({
      id: `edge-${i}`,
      source: `node-${source}`,
      target: `node-${target}`,
      type: 'RELATES_TO',
      weight: seededRandom(i * 31 + 3000),
      isBridge: seededRandom(i * 37 + 4000) > 0.95,
    });
  }

  return { nodes, edges };
}

// Individual node component
function GraphNodeMesh({
  node,
  isHighlighted,
  operatorVisit,
  onClick,
}: {
  node: GraphNode;
  isHighlighted: boolean;
  operatorVisit?: 'A' | 'B' | 'both';
  onClick?: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const color = useMemo(() => {
    if (operatorVisit === 'A') return '#3B82F6';
    if (operatorVisit === 'B') return '#10B981';
    if (operatorVisit === 'both') return '#FFD700';
    return NODE_COLORS[node.type];
  }, [node.type, operatorVisit]);

  const scale = useMemo(() => {
    if (node.isEvidence) return 1.5;
    if (isHighlighted) return 1.3;
    return 0.8 + (node.score || 0.5) * 0.4;
  }, [node.isEvidence, isHighlighted, node.score]);

  useFrame((state) => {
    if (meshRef.current) {
      if (hovered || isHighlighted || node.isEvidence) {
        meshRef.current.scale.lerp(
          new THREE.Vector3(scale * 1.2, scale * 1.2, scale * 1.2),
          0.1
        );
      } else {
        meshRef.current.scale.lerp(
          new THREE.Vector3(scale, scale, scale),
          0.1
        );
      }
    }
  });

  return (
    <group position={[node.position.x, node.position.y, node.position.z]}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered || isHighlighted ? 0.5 : 0.2}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Glow effect for evidence nodes */}
      {node.isEvidence && (
        <mesh scale={1.5}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.2}
          />
        </mesh>
      )}
    </group>
  );
}

// Edge component with bundling
function GraphEdgeLine({
  edge,
  nodes,
  isBridge,
  isActive,
}: {
  edge: GraphEdge;
  nodes: Map<string, GraphNode>;
  isBridge: boolean;
  isActive: boolean;
}) {
  const sourceNode = nodes.get(edge.source);
  const targetNode = nodes.get(edge.target);

  if (!sourceNode || !targetNode) return null;

  const points = useMemo(() => {
    const start = new THREE.Vector3(
      sourceNode.position.x,
      sourceNode.position.y,
      sourceNode.position.z
    );
    const end = new THREE.Vector3(
      targetNode.position.x,
      targetNode.position.y,
      targetNode.position.z
    );

    // Add slight curve for visual interest (use deterministic offset based on edge id)
    const mid = new THREE.Vector3()
      .addVectors(start, end)
      .multiplyScalar(0.5);
    // Use edge id hash for deterministic curve offset
    const edgeHash = edge.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    mid.z += (seededRandom(edgeHash) - 0.5) * 5;

    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
    return curve.getPoints(20);
  }, [sourceNode, targetNode, edge.id]);

  const color = isBridge ? '#FFD700' : isActive ? '#3B82F6' : '#ffffff';
  const opacity = isBridge ? 0.6 : isActive ? 0.5 : 0.1;

  return (
    <Line
      points={points}
      color={color}
      lineWidth={isBridge ? 2 : 1}
      transparent
      opacity={opacity}
    />
  );
}

// Operator traversal stream
function OperatorStream({
  path,
  nodes,
  operator,
  progress,
}: {
  path: string[];
  nodes: Map<string, GraphNode>;
  operator: 'A' | 'B';
  progress: number;
}) {
  const pointsRef = useRef<THREE.Vector3[]>([]);
  const lineRef = useRef<any>(null);

  const color = operator === 'A' ? '#3B82F6' : '#10B981';

  // Calculate visible portion of path based on progress
  const visiblePath = useMemo(() => {
    const pathNodes = path
      .map((id) => nodes.get(id))
      .filter(Boolean) as GraphNode[];

    if (pathNodes.length < 2) return [];

    const points: THREE.Vector3[] = pathNodes.map(
      (node) =>
        new THREE.Vector3(node.position.x, node.position.y, node.position.z)
    );

    const visibleCount = Math.ceil(points.length * progress);
    return points.slice(0, visibleCount);
  }, [path, nodes, progress]);

  if (visiblePath.length < 2) return null;

  return (
    <>
      <Line
        points={visiblePath}
        color={color}
        lineWidth={3}
        transparent
        opacity={0.8}
      />
      {/* Current position indicator */}
      {visiblePath.length > 0 && (
        <Float speed={4} floatIntensity={0.5}>
          <mesh position={visiblePath[visiblePath.length - 1]}>
            <sphereGeometry args={[1.5, 16, 16]} />
            <meshBasicMaterial color={color} transparent opacity={0.8} />
          </mesh>
        </Float>
      )}
    </>
  );
}

// Main scene component
function GraphScene({
  nodes,
  edges,
  animationState,
  operatorPaths,
  selectedNodeId,
  onNodeClick,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  animationState: AnimationState;
  operatorPaths: { A: string[]; B: string[] };
  selectedNodeId: string | null;
  onNodeClick?: (node: GraphNode) => void;
}) {
  const nodeMap = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
    [nodes]
  );

  const [operatorProgress, setOperatorProgress] = useState({ A: 0, B: 0 });

  // Animate operator progress
  useEffect(() => {
    if (animationState === 'operator_a_traversing' || animationState === 'operator_b_traversing') {
      const interval = setInterval(() => {
        setOperatorProgress((prev) => ({
          A: Math.min(prev.A + 0.02, 1),
          B: Math.min(prev.B + 0.015, 1),
        }));
      }, 50);
      return () => clearInterval(interval);
    }
  }, [animationState]);

  return (
    <>
      {/* Ambient lighting */}
      <ambientLight intensity={0.4} />
      <pointLight position={[100, 100, 100]} intensity={0.8} />
      <pointLight position={[-100, -100, -100]} intensity={0.4} color="#764BA2" />

      {/* Render edges first (behind nodes) */}
      {edges.slice(0, 500).map((edge) => (
        <GraphEdgeLine
          key={edge.id}
          edge={edge}
          nodes={nodeMap}
          isBridge={edge.isBridge || false}
          isActive={false}
        />
      ))}

      {/* Render nodes */}
      {nodes.map((node) => (
        <GraphNodeMesh
          key={node.id}
          node={node}
          isHighlighted={node.id === selectedNodeId}
          onClick={() => onNodeClick?.(node)}
        />
      ))}

      {/* Operator traversal streams */}
      {operatorPaths.A.length > 0 && (
        <OperatorStream
          path={operatorPaths.A}
          nodes={nodeMap}
          operator="A"
          progress={operatorProgress.A}
        />
      )}
      {operatorPaths.B.length > 0 && (
        <OperatorStream
          path={operatorPaths.B}
          nodes={nodeMap}
          operator="B"
          progress={operatorProgress.B}
        />
      )}

      {/* Camera controls */}
      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        autoRotate={animationState === 'idle'}
        autoRotateSpeed={0.5}
        minDistance={50}
        maxDistance={300}
      />
    </>
  );
}

// Main component
interface KnowledgeGraph3DProps {
  data?: { nodes: GraphNode[]; edges: GraphEdge[] };
  animationState?: AnimationState;
  operatorPaths?: { A: string[]; B: string[] };
  onNodeClick?: (node: GraphNode) => void;
  className?: string;
  showStats?: boolean;
}

export default function KnowledgeGraph3D({
  data,
  animationState = 'idle',
  operatorPaths = { A: [], B: [] },
  onNodeClick,
  className = '',
  showStats = true,
}: KnowledgeGraph3DProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Use provided data or generate demo data
  const graphData = useMemo(() => data || generateDemoGraph(), [data]);

  const handleNodeClick = (node: GraphNode) => {
    setSelectedNodeId(node.id);
    onNodeClick?.(node);
  };

  return (
    <div className={`relative w-full h-full min-h-[400px] ${className}`} style={{ position: 'relative' }}>
      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 150], fov: 60 }}
        gl={{ antialias: true, alpha: true }}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a14 100%)',
        }}
      >
        <GraphScene
          nodes={graphData.nodes}
          edges={graphData.edges}
          animationState={animationState}
          operatorPaths={operatorPaths}
          selectedNodeId={selectedNodeId}
          onNodeClick={handleNodeClick}
        />
      </Canvas>

      {/* Stats overlay */}
      {showStats && (
        <motion.div
          className="absolute bottom-0 left-0 right-0 p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          style={{
            background: 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%)',
          }}
        >
          <div className="flex flex-wrap gap-3">
            <span className="stat-pill">
              {graphData.nodes.length.toLocaleString()} nodes
            </span>
            <span className="stat-pill">
              {graphData.edges.length.toLocaleString()} edges
            </span>
            {animationState !== 'idle' && (
              <span className="stat-pill bg-[#3B82F6]/20 border-[#3B82F6]/30">
                {animationState.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </motion.div>
      )}

      {/* Legend */}
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2 text-xs text-white/70">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span>{type.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
