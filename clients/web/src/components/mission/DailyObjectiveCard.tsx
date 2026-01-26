'use client'

import { DailyObjective } from '@/lib/api'

interface DailyObjectiveCardProps {
  objective: DailyObjective
  onRegenerate?: () => void
  canRegenerate: boolean
  isRegenerating?: boolean
}

export function DailyObjectiveCard({
  objective,
  onRegenerate,
  canRegenerate,
  isRegenerating = false,
}: DailyObjectiveCardProps) {
  const progressPercent = objective.target_count > 0
    ? Math.round((objective.completed_count / objective.target_count) * 100)
    : 0

  return (
    <div className="bg-gradient-to-r from-sky-600/20 to-indigo-600/20 dark:from-sky-600/10 dark:to-indigo-600/10 border border-sky-500/30 rounded-2xl p-6">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-12 h-12 bg-sky-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>

        {/* Content */}
        <div className="flex-1">
          <p className="text-sky-600 dark:text-sky-400 text-sm font-medium mb-1">Today's Focus</p>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
            {objective.title}
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
            {objective.description}
          </p>

          {/* Skill tags */}
          {objective.skill_tags.length > 0 && (
            <div className="flex gap-2 mt-3 flex-wrap">
              {objective.skill_tags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs bg-sky-500/20 text-sky-600 dark:text-sky-400 px-2 py-0.5 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Regenerate button */}
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            disabled={!canRegenerate || isRegenerating}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={canRegenerate ? 'Regenerate mission' : 'Regeneration limit reached'}
          >
            <svg
              className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span className="hidden sm:inline">Regenerate</span>
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="mt-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-500 dark:text-slate-400">Today's Progress</span>
          <span className="text-sm font-medium text-slate-900 dark:text-white">
            {objective.completed_count} of {objective.target_count} completed
          </span>
        </div>
        <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-sky-500 to-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  )
}
