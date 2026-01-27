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
    <div className="card">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1">
          <p className="text-xs uppercase tracking-wider text-gray-500 mb-2">Today's Focus</p>
          <h2 className="text-base font-semibold text-black mb-2">
            {objective.title}
          </h2>
          <p className="text-gray-600 text-sm leading-relaxed">
            {objective.description}
          </p>

          {/* Skill tags */}
          {objective.skill_tags.length > 0 && (
            <div className="flex gap-2 mt-3 flex-wrap">
              {objective.skill_tags.map((tag, i) => (
                <span
                  key={tag}
                  className={i === 0 ? 'tag tag-accent' : 'tag'}
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
            className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            title={canRegenerate ? 'Regenerate mission' : 'Regeneration limit reached'}
          >
            <svg
              className={`w-4 h-4 inline mr-1 ${isRegenerating ? 'animate-spin' : ''}`}
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
            Regenerate
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="pt-4 border-t-2 border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-500 uppercase tracking-wide">Today's Progress</span>
          <span className="text-sm font-medium text-black">
            {objective.completed_count} of {objective.target_count}
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  )
}
