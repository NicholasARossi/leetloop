'use client'

interface StreakBadgeProps {
  streak: number
}

export function StreakBadge({ streak }: StreakBadgeProps) {
  const isActive = streak > 0

  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
      isActive
        ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
        : 'bg-slate-100 dark:bg-slate-700 text-slate-500'
    }`}>
      <span className="text-xl">{isActive ? '🔥' : '💤'}</span>
      <div className="flex flex-col">
        <span className="font-bold text-lg leading-tight">{streak}</span>
        <span className="text-xs leading-tight">
          {streak === 1 ? 'day' : 'days'}
        </span>
      </div>
    </div>
  )
}
