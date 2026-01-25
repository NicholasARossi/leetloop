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

interface ProgressLineProps {
  trends: ProgressTrend[]
  className?: string
}

export function ProgressLine({ trends, className }: ProgressLineProps) {
  if (trends.length === 0) {
    return (
      <div className={className}>
        <div className="flex items-center justify-center h-64 text-slate-500">
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
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={{ stroke: '#e2e8f0' }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={{ stroke: '#e2e8f0' }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[0, 100]}
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={{ stroke: '#e2e8f0' }}
            unit="%"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: 'none',
              borderRadius: '8px',
              color: '#f8fafc',
            }}
          />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="Submissions"
            stroke="#94a3b8"
            strokeWidth={2}
            dot={{ fill: '#94a3b8', strokeWidth: 0, r: 3 }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="Accepted"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ fill: '#22c55e', strokeWidth: 0, r: 3 }}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="Success Rate"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={{ fill: '#0ea5e9', strokeWidth: 0, r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
