'use client'

import { clsx } from 'clsx'
import type { PaceStatus } from '@/lib/api'

interface PaceIndicatorProps {
  pace: PaceStatus
  compact?: boolean
}

const statusConfig = {
  ahead: {
    label: 'AHEAD',
    color: 'bg-green-500',
    textColor: 'text-green-600',
    bgLight: 'bg-green-50',
    message: 'Great work! You\'re ahead of schedule.',
  },
  on_track: {
    label: 'ON TRACK',
    color: 'bg-blue-500',
    textColor: 'text-blue-600',
    bgLight: 'bg-blue-50',
    message: 'Keep going! You\'re on track to meet your goal.',
  },
  behind: {
    label: 'BEHIND',
    color: 'bg-yellow-500',
    textColor: 'text-yellow-600',
    bgLight: 'bg-yellow-50',
    message: 'You\'re falling behind. Time to push harder.',
  },
  critical: {
    label: 'CRITICAL',
    color: 'bg-coral',
    textColor: 'text-coral',
    bgLight: 'bg-red-50',
    message: 'Urgent: You need to significantly increase your pace.',
  },
}

export function PaceIndicator({ pace, compact = false }: PaceIndicatorProps) {
  const config = statusConfig[pace.status]

  if (compact) {
    return (
      <div className={clsx(
        'inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-bold',
        config.bgLight,
        config.textColor
      )}>
        <span className={clsx('w-2 h-2 rounded-full', config.color)} />
        {config.label}
      </div>
    )
  }

  return (
    <div className={clsx('card', config.bgLight, 'border-l-4', `border-l-${pace.status === 'critical' ? 'coral' : config.color.replace('bg-', '')}`)}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className={clsx('text-lg font-bold', config.textColor)}>
            {config.label}
          </div>
          <div className="text-sm text-gray-600">
            {config.message}
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-mono font-bold text-black">
            {pace.pace_percentage.toFixed(0)}%
          </div>
          <div className="text-xs text-gray-500">of expected pace</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-gray-500">This Week</div>
          <div className="font-mono font-bold text-black">
            {pace.problems_this_week} / {pace.weekly_target}
          </div>
        </div>
        <div>
          <div className="text-gray-500">Behind By</div>
          <div className={clsx('font-mono font-bold', pace.problems_behind > 0 ? 'text-coral' : 'text-green-600')}>
            {pace.problems_behind > 0 ? `${pace.problems_behind} problems` : 'None'}
          </div>
        </div>
        <div>
          <div className="text-gray-500">Need Daily</div>
          <div className="font-mono font-bold text-black">
            {pace.daily_rate_needed.toFixed(1)} problems
          </div>
        </div>
      </div>
    </div>
  )
}
