'use client'

interface DailyGoalRingProps {
  completed: number
  goal: number
  size?: number
}

export function DailyGoalRing({ completed, goal, size = 120 }: DailyGoalRingProps) {
  const progress = Math.min(completed / goal, 1)
  const strokeWidth = 8
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference * (1 - progress)

  const isComplete = completed >= goal

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background circle */}
        <svg
          className="absolute inset-0 -rotate-90"
          width={size}
          height={size}
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-200 dark:text-slate-700"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`transition-all duration-500 ${
              isComplete
                ? 'text-green-500'
                : progress > 0.5
                ? 'text-brand-500'
                : 'text-yellow-500'
            }`}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-bold ${
            isComplete ? 'text-green-600 dark:text-green-400' : 'text-slate-900 dark:text-white'
          }`}>
            {completed}/{goal}
          </span>
          <span className="text-xs text-slate-500">
            {isComplete ? 'Complete!' : 'daily goal'}
          </span>
        </div>
      </div>
    </div>
  )
}
