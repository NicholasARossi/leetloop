'use client'

import type { LifeOpsStreak } from '@/lib/api'

interface StreakDisplayProps {
  streak: LifeOpsStreak
}

export function StreakDisplay({ streak }: StreakDisplayProps) {
  return (
    <div className="card mb-6">
      <h3 className="section-title">Streak</h3>
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center p-4 bg-gray-50 rounded-md">
          <div className="text-3xl font-bold">{streak.current_streak}</div>
          <div className="text-xs text-gray-500 mt-1">Current Streak</div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-md">
          <div className="text-3xl font-bold">{streak.longest_streak}</div>
          <div className="text-xs text-gray-500 mt-1">Longest Streak</div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-md">
          <div className="text-3xl font-bold">{streak.total_perfect_days}</div>
          <div className="text-xs text-gray-500 mt-1">Perfect Days</div>
        </div>
        <div className="text-center p-4 bg-gray-50 rounded-md">
          <div className="text-sm font-medium">
            {streak.last_completed_date || '--'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Last Perfect Day</div>
        </div>
      </div>
    </div>
  )
}
