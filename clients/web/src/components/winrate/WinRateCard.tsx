'use client'

import { clsx } from 'clsx'
import type { WinRateStats, DifficultyWinRate } from '@/lib/api'

interface WinRateCardProps {
  stats: WinRateStats
  period?: '30d' | 'alltime'
  onTogglePeriod?: () => void
}

const difficultyConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  easy: { label: 'Easy', color: 'bg-green-500', bgColor: 'bg-green-100' },
  medium: { label: 'Medium', color: 'bg-yellow-500', bgColor: 'bg-yellow-100' },
  hard: { label: 'Hard', color: 'bg-red-500', bgColor: 'bg-red-100' },
}

function RateBar({ difficulty, data }: { difficulty: string; data: DifficultyWinRate }) {
  const config = difficultyConfig[difficulty] || difficultyConfig.easy
  const ratePercent = Math.round(data.rate * 100)
  const targetPercent = Math.round(data.target * 100)
  const isAboveTarget = data.rate >= data.target

  return (
    <div className="mb-3 last:mb-0">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-bold uppercase tracking-wider">{config.label}</span>
        <span className={clsx(
          'text-xs font-mono font-bold',
          isAboveTarget ? 'text-green-600' : 'text-red-600'
        )}>
          {ratePercent}% ({data.optimal}/{data.attempts})
        </span>
      </div>
      <div className="relative h-4 border-2 border-black bg-gray-100">
        {/* Filled bar */}
        <div
          className={clsx(
            'h-full transition-all duration-500',
            isAboveTarget ? 'bg-green-500' : 'bg-red-400'
          )}
          style={{ width: `${Math.min(ratePercent, 100)}%` }}
        />
        {/* Target marker */}
        <div
          className="absolute top-0 h-full w-0.5 bg-black"
          style={{ left: `${Math.min(targetPercent, 100)}%` }}
          title={`Target: ${targetPercent}%`}
        >
          <div className="absolute -top-4 -translate-x-1/2 text-[9px] font-mono text-gray-500 whitespace-nowrap">
            {targetPercent}%
          </div>
        </div>
      </div>
    </div>
  )
}

export function WinRateCard({ stats, period = '30d', onTogglePeriod }: WinRateCardProps) {
  const rateData = period === '30d' ? stats.current_30d : stats.current_alltime

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title !mb-0 !pb-0 !border-0">Win Rate</h3>
        {onTogglePeriod && (
          <button
            onClick={onTogglePeriod}
            className="text-xs font-mono px-2 py-1 border-2 border-black hover:bg-gray-100 transition-colors"
          >
            {period === '30d' ? '30-day' : 'All-time'}
          </button>
        )}
      </div>

      {(!rateData || Object.keys(rateData).length === 0) ? (
        <p className="text-sm text-gray-500">No metric data yet. Complete metric problems to track your win rate.</p>
      ) : (
        <div>
          {['easy', 'medium', 'hard'].map(diff => {
            const data = rateData[diff]
            if (!data) return null
            return <RateBar key={diff} difficulty={diff} data={data} />
          })}
        </div>
      )}
    </div>
  )
}
