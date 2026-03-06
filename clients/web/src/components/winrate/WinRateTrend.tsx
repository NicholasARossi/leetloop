'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { WinRateStats } from '@/lib/api'

interface WinRateTrendProps {
  stats: WinRateStats
}

export function WinRateTrend({ stats }: WinRateTrendProps) {
  if (!stats.trend || stats.trend.length === 0) {
    return (
      <div className="card">
        <h3 className="section-title mb-4">Win Rate Trend</h3>
        <p className="text-sm text-gray-500 text-center py-8">
          Not enough data for trends yet. Complete metric problems to see your progress.
        </p>
      </div>
    )
  }

  const data = stats.trend.map(t => ({
    date: t.date,
    easy: Math.round(t.easy_rate * 100),
    medium: Math.round(t.medium_rate * 100),
    hard: Math.round(t.hard_rate * 100),
  }))

  const easyTarget = stats.targets ? Math.round(stats.targets.easy_target * 100) : 90
  const mediumTarget = stats.targets ? Math.round(stats.targets.medium_target * 100) : 70
  const hardTarget = stats.targets ? Math.round(stats.targets.hard_target * 100) : 50

  return (
    <div className="card">
      <h3 className="section-title mb-4">Win Rate Trend (30 Days)</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              tickFormatter={(v) => v.slice(5)}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 10 }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(value: number) => [`${value}%`]}
              labelFormatter={(label) => `Date: ${label}`}
            />
            {/* Target reference lines */}
            <ReferenceLine y={easyTarget} stroke="#22c55e" strokeDasharray="5 5" strokeWidth={1} />
            <ReferenceLine y={mediumTarget} stroke="#eab308" strokeDasharray="5 5" strokeWidth={1} />
            <ReferenceLine y={hardTarget} stroke="#ef4444" strokeDasharray="5 5" strokeWidth={1} />
            {/* Data lines */}
            <Line type="monotone" dataKey="easy" stroke="#22c55e" strokeWidth={2} dot={false} name="Easy" />
            <Line type="monotone" dataKey="medium" stroke="#eab308" strokeWidth={2} dot={false} name="Medium" />
            <Line type="monotone" dataKey="hard" stroke="#ef4444" strokeWidth={2} dot={false} name="Hard" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-4 mt-2 text-xs">
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-green-500 inline-block" /> Easy</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-yellow-500 inline-block" /> Medium</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-red-500 inline-block" /> Hard</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 border-t-2 border-dashed border-gray-400 inline-block" /> Target</span>
      </div>
    </div>
  )
}
