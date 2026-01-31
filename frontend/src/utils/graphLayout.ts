import type { GraphNode, GraphEdge, NodeType } from '@/types';
import * as THREE from 'three';

// Force-directed layout simulation
export class ForceDirectedLayout {
  private nodes: GraphNode[];
  private edges: GraphEdge[];
  private nodeMap: Map<string, GraphNode>;
  private velocities: Map<string, THREE.Vector3>;

  // Physics parameters
  private repulsion = 500;
  private attraction = 0.01;
  private damping = 0.9;
  private maxVelocity = 10;

  constructor(nodes: GraphNode[], edges: GraphEdge[]) {
    this.nodes = nodes;
    this.edges = edges;
    this.nodeMap = new Map(nodes.map((n) => [n.id, n]));
    this.velocities = new Map(
      nodes.map((n) => [n.id, new THREE.Vector3(0, 0, 0)])
    );
  }

  // Run one iteration of the simulation
  tick(): void {
    // Reset forces
    const forces = new Map<string, THREE.Vector3>();
    this.nodes.forEach((n) => forces.set(n.id, new THREE.Vector3(0, 0, 0)));

    // Calculate repulsion forces (all nodes repel each other)
    for (let i = 0; i < this.nodes.length; i++) {
      for (let j = i + 1; j < this.nodes.length; j++) {
        const nodeA = this.nodes[i];
        const nodeB = this.nodes[j];

        const dx = nodeB.position.x - nodeA.position.x;
        const dy = nodeB.position.y - nodeA.position.y;
        const dz = nodeB.position.z - nodeA.position.z;

        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.1;
        const force = this.repulsion / (distance * distance);

        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;
        const fz = (dz / distance) * force;

        forces.get(nodeA.id)!.sub(new THREE.Vector3(fx, fy, fz));
        forces.get(nodeB.id)!.add(new THREE.Vector3(fx, fy, fz));
      }
    }

    // Calculate attraction forces (connected nodes attract)
    this.edges.forEach((edge) => {
      const nodeA = this.nodeMap.get(edge.source);
      const nodeB = this.nodeMap.get(edge.target);

      if (!nodeA || !nodeB) return;

      const dx = nodeB.position.x - nodeA.position.x;
      const dy = nodeB.position.y - nodeA.position.y;
      const dz = nodeB.position.z - nodeA.position.z;

      const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
      const force = distance * this.attraction * (edge.weight || 1);

      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      const fz = (dz / distance) * force;

      forces.get(nodeA.id)!.add(new THREE.Vector3(fx, fy, fz));
      forces.get(nodeB.id)!.sub(new THREE.Vector3(fx, fy, fz));
    });

    // Apply forces to velocities and positions
    this.nodes.forEach((node) => {
      const velocity = this.velocities.get(node.id)!;
      const force = forces.get(node.id)!;

      velocity.add(force);
      velocity.multiplyScalar(this.damping);

      // Clamp velocity
      if (velocity.length() > this.maxVelocity) {
        velocity.normalize().multiplyScalar(this.maxVelocity);
      }

      node.position.x += velocity.x;
      node.position.y += velocity.y;
      node.position.z += velocity.z;
    });
  }

  // Run simulation for specified iterations
  simulate(iterations: number = 100): GraphNode[] {
    for (let i = 0; i < iterations; i++) {
      this.tick();
    }
    return this.nodes;
  }

  getNodes(): GraphNode[] {
    return this.nodes;
  }
}

// Generate initial random positions in a sphere
export function generateInitialPositions(
  nodes: GraphNode[],
  radius: number = 100
): GraphNode[] {
  return nodes.map((node) => ({
    ...node,
    position: {
      x: (Math.random() - 0.5) * radius * 2,
      y: (Math.random() - 0.5) * radius * 2,
      z: (Math.random() - 0.5) * radius * 2,
    },
  }));
}

// Group nodes by type for layered layout
export function groupNodesByType(nodes: GraphNode[]): Map<NodeType, GraphNode[]> {
  const groups = new Map<NodeType, GraphNode[]>();
  nodes.forEach((node) => {
    const group = groups.get(node.type) || [];
    group.push(node);
    groups.set(node.type, group);
  });
  return groups;
}

// Create a hierarchical layout based on node types
export function createHierarchicalLayout(
  nodes: GraphNode[],
  edges: GraphEdge[]
): GraphNode[] {
  const groups = groupNodesByType(nodes);
  const layerSpacing = 50;
  const nodeSpacing = 20;

  let currentY = 0;

  // Define layer order
  const layerOrder: NodeType[] = ['FINANCIAL_LINE', 'TEXT_SECTION', 'NOTE', 'ENTITY'];

  layerOrder.forEach((type, layerIndex) => {
    const layerNodes = groups.get(type) || [];
    const columns = Math.ceil(Math.sqrt(layerNodes.length));
    const rows = Math.ceil(layerNodes.length / columns);

    layerNodes.forEach((node, index) => {
      const col = index % columns;
      const row = Math.floor(index / columns);

      node.position = {
        x: (col - columns / 2) * nodeSpacing,
        y: currentY - row * nodeSpacing,
        z: (Math.random() - 0.5) * 20,
      };
    });

    currentY -= rows * nodeSpacing + layerSpacing;
  });

  return nodes;
}

// Calculate bounding box of all nodes
export function calculateBoundingBox(nodes: GraphNode[]): {
  min: THREE.Vector3;
  max: THREE.Vector3;
  center: THREE.Vector3;
  size: THREE.Vector3;
} {
  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);

  nodes.forEach((node) => {
    min.x = Math.min(min.x, node.position.x);
    min.y = Math.min(min.y, node.position.y);
    min.z = Math.min(min.z, node.position.z);
    max.x = Math.max(max.x, node.position.x);
    max.y = Math.max(max.y, node.position.y);
    max.z = Math.max(max.z, node.position.z);
  });

  const center = new THREE.Vector3()
    .addVectors(min, max)
    .multiplyScalar(0.5);

  const size = new THREE.Vector3().subVectors(max, min);

  return { min, max, center, size };
}

// Find shortest path between two nodes using BFS
export function findShortestPath(
  edges: GraphEdge[],
  startId: string,
  endId: string
): string[] | null {
  const adjacency = new Map<string, string[]>();

  edges.forEach((edge) => {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
    adjacency.get(edge.source)!.push(edge.target);
    adjacency.get(edge.target)!.push(edge.source);
  });

  const queue: string[][] = [[startId]];
  const visited = new Set<string>([startId]);

  while (queue.length > 0) {
    const path = queue.shift()!;
    const current = path[path.length - 1];

    if (current === endId) return path;

    const neighbors = adjacency.get(current) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([...path, neighbor]);
      }
    }
  }

  return null;
}
