'use client'

import type { LifeOpsCompletionRate } from '@/lib/api'

interface CompletionChartProps {
  title: string
  rates: LifeOpsCompletionRate[]
}

export function CompletionChart({ title, rates }: CompletionChartProps) {
  if (rates.length === 0) return null

  const maxRate = 100

  return (
    <div className="card mb-6">
      <h3 className="section-title">{title}</h3>
      <div className="space-y-3">
        {rates.map((rate) => (
          <div key={rate.period}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500">{rate.period}</span>
              <span className="text-xs font-semibold">
                {rate.rate}% ({rate.completed}/{rate.total})
              </span>
            </div>
            <div className="w-full bg-gray-100 border border-gray-200 rounded-full h-2.5">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${(rate.rate / maxRate) * 100}%`,
                  backgroundColor: rate.rate >= 80 ? '#22c55e' : rate.rate >= 50 ? '#eab308' : '#ef4444',
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
