'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';

interface DivergenceChartProps {
  data?: { hop: number; delta: number }[];
  className?: string;
}

const defaultData = [
  { hop: 1, delta: 0.65, label: 'Hop 1' },
  { hop: 2, delta: 0.45, label: 'Hop 2' },
  { hop: 3, delta: 0.38, label: 'Hop 3' },
  { hop: 4, delta: 0.335, label: 'Hop 4' },
];

export default function DivergenceChart({
  data = defaultData,
  className = '',
}: DivergenceChartProps) {
  const chartData = useMemo(() => data, [data]);

  return (
    <div className={`w-full h-64 ${className}`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 20, right: 20, left: 0, bottom: 10 }}
        >
          {/* Gradient fill */}
          <defs>
            <linearGradient id="deltaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#667EEA" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#667EEA" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(0,0,0,0.06)"
            vertical={false}
          />

          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#86868B', fontSize: 12 }}
            dy={10}
          />

          <YAxis
            domain={[0, 0.8]}
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#86868B', fontSize: 12 }}
            tickFormatter={(value) => value.toFixed(1)}
            dx={-10}
          />

          {/* Convergence threshold line */}
          <ReferenceLine
            y={0.4}
            stroke="#F59E0B"
            strokeDasharray="5 5"
            label={{
              value: 'Convergence',
              position: 'right',
              fill: '#F59E0B',
              fontSize: 11,
            }}
          />

          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white/95 backdrop-blur-sm border border-black/10 rounded-lg px-4 py-3 shadow-lg">
                    <p className="font-medium text-[#1D1D1F]">{data.label}</p>
                    <p className="text-sm text-[#6E6E73]">
                      Divergence:{' '}
                      <span
                        className="font-mono font-bold"
                        style={{
                          color:
                            data.delta < 0.3
                              ? '#10B981'
                              : data.delta < 0.6
                              ? '#F59E0B'
                              : '#EF4444',
                        }}
                      >
                        {data.delta.toFixed(3)}
                      </span>
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />

          <Area
            type="monotone"
            dataKey="delta"
            stroke="#667EEA"
            strokeWidth={3}
            fill="url(#deltaGradient)"
            dot={{
              fill: '#667EEA',
              stroke: '#fff',
              strokeWidth: 2,
              r: 6,
            }}
            activeDot={{
              fill: '#764BA2',
              stroke: '#fff',
              strokeWidth: 2,
              r: 8,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Mini version for inline display
export function DivergenceSparkline({
  data = defaultData,
  className = '',
}: DivergenceChartProps) {
  return (
    <div className={`w-32 h-8 ${className}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            type="monotone"
            dataKey="delta"
            stroke="#667EEA"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
