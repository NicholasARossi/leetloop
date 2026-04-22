'use client'

import { useMemo } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { ProgressTrend } from '@/lib/api'

interface VelocityChartProps {
  trends: ProgressTrend[]
  windowDays?: number
}

export function VelocityChart({ trends, windowDays = 7 }: VelocityChartProps) {
  const chartData = useMemo(() => {
    if (trends.length === 0) return []

    // Build a complete date range with 0-filled gaps
    const dateMap = new Map<string, number>()
    for (const t of trends) {
      dateMap.set(t.date, t.submissions)
    }

    const sortedDates = Array.from(dateMap.keys()).sort()
    if (sortedDates.length === 0) return []

    const start = new Date(sortedDates[0])
    const end = new Date(sortedDates[sortedDates.length - 1])
    const allDays: { date: string; count: number }[] = []

    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      const key = d.toISOString().slice(0, 10)
      allDays.push({ date: key, count: dateMap.get(key) || 0 })
    }

    // Compute rolling average
    const result: { date: string; velocity: number }[] = []
    for (let i = 0; i < allDays.length; i++) {
      const windowStart = Math.max(0, i - windowDays + 1)
      const window = allDays.slice(windowStart, i + 1)
      const avg = window.reduce((sum, d) => sum + d.count, 0) / windowDays
      result.push({
        date: allDays[i].date.slice(5), // MM-DD
        velocity: Math.round(avg * 100) / 100,
      })
    }

    return result
  }, [trends, windowDays])

  if (chartData.length === 0) {
    return null
  }

  return (
    <div>
      <div className="dimension-line mb-3">
        <span className="text-[9px] uppercase tracking-widest text-gray-400 px-2 whitespace-nowrap">
          Velocity (7-day avg)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="velocityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#000" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#000" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fill: '#a3a3a3', fontSize: 9 }}
            tickLine={false}
            axisLine={{ stroke: '#e5e5e5' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#a3a3a3', fontSize: 9 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#262626',
              border: 'none',
              borderRadius: '6px',
              color: '#fafafa',
              fontSize: 11,
            }}
            formatter={(value: number) => [`${value} problems/day`]}
            labelStyle={{ color: '#fafafa' }}
            itemStyle={{ color: '#fafafa' }}
          />
          <Area
            type="monotone"
            dataKey="velocity"
            stroke="#000"
            strokeWidth={1.5}
            fill="url(#velocityGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
