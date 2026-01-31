'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface EvidenceBreakdownProps {
  data?: { type: string; count: number; color: string; label: string }[];
  className?: string;
}

const defaultData = [
  { type: 'FINANCIAL_LINE', count: 62, color: '#3B82F6', label: 'Financial Data' },
  { type: 'TEXT_SECTION', count: 23, color: '#10B981', label: 'Text Sections' },
  { type: 'NOTE', count: 15, color: '#F59E0B', label: 'Notes' },
];

export default function EvidenceBreakdown({
  data = defaultData,
  className = '',
}: EvidenceBreakdownProps) {
  const chartData = useMemo(() => data, [data]);
  const total = useMemo(
    () => chartData.reduce((sum, item) => sum + item.count, 0),
    [chartData]
  );

  return (
    <div className={`flex flex-col lg:flex-row items-center gap-6 ${className}`}>
      {/* Pie chart */}
      <div className="w-40 h-40">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={60}
              paddingAngle={4}
              dataKey="count"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white/95 backdrop-blur-sm border border-black/10 rounded-lg px-3 py-2 shadow-lg">
                      <p className="font-medium text-[#1D1D1F]">{data.label}</p>
                      <p className="text-sm text-[#6E6E73]">
                        {data.count}% of evidence
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex-1 space-y-3">
        {chartData.map((item, index) => (
          <motion.div
            key={item.type}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-[#1D1D1F]">{item.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-24 h-2 bg-black/5 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: item.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${item.count}%` }}
                  transition={{ delay: index * 0.1 + 0.3, duration: 0.5 }}
                />
              </div>
              <span className="font-mono text-sm font-medium text-[#1D1D1F] w-10 text-right">
                {item.count}%
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// Compact version
export function EvidenceBreakdownCompact({
  data = defaultData,
  className = '',
}: EvidenceBreakdownProps) {
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {data.map((item) => (
        <span
          key={item.type}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium"
          style={{
            backgroundColor: `${item.color}15`,
            color: item.color,
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          {item.label} ({item.count}%)
        </span>
      ))}
    </div>
  );
}
