'use client'

interface ProgressHeaderProps {
  completedCount: number
  totalCount: number
  currentStreak: number
}

export function ProgressHeader({ completedCount, totalCount, currentStreak }: ProgressHeaderProps) {
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0
  const allDone = totalCount > 0 && completedCount === totalCount

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-lg font-bold">
            {allDone ? 'All done!' : "Today's Checklist"}
          </h2>
          <p className="text-sm text-gray-500">
            {completedCount}/{totalCount} completed
          </p>
        </div>
        {currentStreak > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-md">
            <span className="text-amber-600 font-bold text-sm">{currentStreak}</span>
            <span className="text-amber-600 text-xs">day streak</span>
          </div>
        )}
      </div>

      <div className="w-full bg-gray-100 border border-gray-200 rounded-full h-3">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${progressPercent}%`,
            backgroundColor: allDone ? 'var(--success-color, #22c55e)' : 'var(--accent-color)',
          }}
        />
      </div>
    </div>
  )
}
