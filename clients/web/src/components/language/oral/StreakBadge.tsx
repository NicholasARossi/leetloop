'use client'

interface StreakBadgeProps {
  currentStreak: number
  longestStreak: number
}

export function StreakBadge({ currentStreak, longestStreak }: StreakBadgeProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5">
        <span className="text-xl" role="img" aria-label="flame">
          {currentStreak > 0 ? '🔥' : '💤'}
        </span>
        <span className="stat-value text-lg">
          Jour {currentStreak}
        </span>
      </div>
      {longestStreak > currentStreak && (
        <span className="text-xs text-gray-400 font-mono">
          record: {longestStreak}
        </span>
      )}
    </div>
  )
}
