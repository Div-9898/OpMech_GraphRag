import type { ModeType, NodeType, TrustDecision } from '@/types';

// Format number with commas
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

// Format currency
export function formatCurrency(num: number): string {
  if (num >= 1e12) {
    return `$${(num / 1e12).toFixed(2)}T`;
  }
  if (num >= 1e9) {
    return `$${(num / 1e9).toFixed(2)}B`;
  }
  if (num >= 1e6) {
    return `$${(num / 1e6).toFixed(2)}M`;
  }
  if (num >= 1e3) {
    return `$${(num / 1e3).toFixed(2)}K`;
  }
  return `$${num.toFixed(2)}`;
}

// Format percentage
export function formatPercentage(num: number, decimals: number = 0): string {
  return `${(num * 100).toFixed(decimals)}%`;
}

// Format delta value
export function formatDelta(delta: number): string {
  return delta.toFixed(3);
}

// Get mode label
export function getModeLabel(mode: ModeType): string {
  const labels: Record<ModeType, string> = {
    EXPLOIT: 'High Confidence',
    ADAPTIVE: 'Balanced View',
    EXPLORE: 'Multiple Perspectives',
  };
  return labels[mode];
}

// Get mode description
export function getModeDescription(mode: ModeType): string {
  const descriptions: Record<ModeType, string> = {
    EXPLOIT: 'Direct answer from authoritative source',
    ADAPTIVE: 'Nuanced analysis with context',
    EXPLORE: 'Exploring different viewpoints',
  };
  return descriptions[mode];
}

// Get mode icon
export function getModeIcon(mode: ModeType): string {
  const icons: Record<ModeType, string> = {
    EXPLOIT: '⚡',
    ADAPTIVE: '⚖️',
    EXPLORE: '🔍',
  };
  return icons[mode];
}

// Get node type label
export function getNodeTypeLabel(type: NodeType): string {
  const labels: Record<NodeType, string> = {
    FINANCIAL_LINE: 'Financial Data',
    TEXT_SECTION: 'Text Section',
    NOTE: 'Note',
    ENTITY: 'Entity',
  };
  return labels[type];
}

// Get node type icon
export function getNodeTypeIcon(type: NodeType): string {
  const icons: Record<NodeType, string> = {
    FINANCIAL_LINE: '📊',
    TEXT_SECTION: '📝',
    NOTE: '📄',
    ENTITY: '🏢',
  };
  return icons[type];
}

// Get trust decision label
export function getTrustDecisionLabel(decision: TrustDecision): string {
  const labels: Record<TrustDecision, string> = {
    TRUST_A: 'Operator A (Structure)',
    TRUST_B: 'Operator B (Narrative)',
    MERGE_EQUAL: 'Equal Merge',
    MERGE_WEIGHTED: 'Weighted Merge',
  };
  return labels[decision];
}

// Format time ago
export function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${diffDay}d ago`;
}

// Format file size
export function formatFileSize(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(2)} KB`;
  return `${bytes} B`;
}

// Truncate text with ellipsis
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

// Generate unique ID
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Clamp value between min and max
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

// Linear interpolation
export function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t;
}

// Ease out cubic
export function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

// Ease in out cubic
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Get divergence color based on value
export function getDivergenceColor(delta: number): string {
  if (delta < 0.3) return '#10B981'; // Green - low divergence
  if (delta < 0.6) return '#F59E0B'; // Orange - medium divergence
  return '#EF4444'; // Red - high divergence
}

// Get confidence color
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return '#10B981'; // Green - high confidence
  if (confidence >= 0.5) return '#F59E0B'; // Orange - medium confidence
  return '#EF4444'; // Red - low confidence
}
