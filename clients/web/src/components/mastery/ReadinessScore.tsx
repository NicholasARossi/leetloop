'use client'

interface ReadinessScoreProps {
  score: number
  summary: string
}

export function ReadinessScore({ score, summary }: ReadinessScoreProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-blue-600 dark:text-blue-400'
    if (score >= 40) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-500'
    if (score >= 60) return 'bg-blue-500'
    if (score >= 40) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="card p-6 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-700">
      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* Score display */}
        <div className="flex-shrink-0 text-center">
          <div className={`text-5xl font-bold ${getScoreColor(score)}`}>
            {score.toFixed(0)}%
          </div>
          <div className="text-sm text-slate-500 mt-1">Google Readiness</div>
        </div>

        {/* Progress bar and summary */}
        <div className="flex-1 w-full">
          <div className="h-4 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden mb-3">
            <div
              className={`h-full transition-all duration-1000 ${getProgressColor(score)}`}
              style={{ width: `${Math.min(score, 100)}%` }}
            />
          </div>
          <p className="text-slate-700 dark:text-slate-300">{summary}</p>
        </div>

        {/* Target badge */}
        <div className="flex-shrink-0">
          <div className="px-4 py-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm">
            <div className="text-xs text-slate-500 uppercase tracking-wide">Target</div>
            <div className="text-lg font-semibold text-slate-900 dark:text-white">80%+</div>
          </div>
        </div>
      </div>
    </div>
  )
}
