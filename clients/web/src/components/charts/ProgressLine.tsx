'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { ProgressTrend } from '@/lib/api'
import { useAccentColors } from '@/hooks/useAccentColors'

interface ProgressLineProps {
  trends: ProgressTrend[]
  className?: string
}

export function ProgressLine({ trends, className }: ProgressLineProps) {
  const { accent, accentDark } = useAccentColors()

  if (trends.length === 0) {
    return (
      <div className={className}>
        <div className="flex items-center justify-center h-64 text-gray-500">
          No submission data yet. Start solving problems!
        </div>
      </div>
    )
  }

  const chartData = trends.map((t) => ({
    date: t.date.slice(5), // MM-DD format
    Submissions: t.submissions,
    Accepted: t.accepted,
    'Success Rate': Math.round(t.success_rate * 100),
  }))

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#737373', fontSize: 11 }}
            tickLine={{ stroke: '#e5e5e5' }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#737373', fontSize: 11 }}
            tickLine={{ stroke: '#e5e5e5' }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[0, 100]}
            tick={{ fill: '#737373', fontSize: 11 }}
            tickLine={{ stroke: '#e5e5e5' }}
            unit="%"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#262626',
              border: 'none',
              borderRadius: '8px',
              color: '#fafafa',
            }}
          />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="Submissions"
            stroke="#a3a3a3"
            strokeWidth={2}
            dot={{ fill: '#a3a3a3', strokeWidth: 0, r: 3 }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="Accepted"
            stroke={accent}
            strokeWidth={2}
            dot={{ fill: accent, strokeWidth: 0, r: 3 }}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="Success Rate"
            stroke={accentDark}
            strokeWidth={2}
            dot={{ fill: accentDark, strokeWidth: 0, r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
