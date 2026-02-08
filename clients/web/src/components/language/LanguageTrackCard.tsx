'use client'

import { clsx } from 'clsx'
import type { LanguageTrackSummary, LanguageTrackProgressData } from '@/lib/api'

interface LanguageTrackCardProps {
  track: LanguageTrackSummary
  progress?: LanguageTrackProgressData
  isActive?: boolean
  onClick?: () => void
}

export function LanguageTrackCard({ track, progress, isActive, onClick }: LanguageTrackCardProps) {
  const completedTopics = progress?.completed_topics?.length || 0
  const completionPercentage = track.total_topics > 0
    ? (completedTopics / track.total_topics) * 100
    : 0

  const getLevelLabel = (level: string) => level.toUpperCase()

  const getLanguageLabel = (language: string) => {
    const labels: Record<string, string> = {
      french: 'French',
      chinese: 'Chinese',
      spanish: 'Spanish',
      german: 'German',
      japanese: 'Japanese',
      italian: 'Italian',
      portuguese: 'Portuguese',
      korean: 'Korean',
    }
    return labels[language] || language.charAt(0).toUpperCase() + language.slice(1)
  }

  const isStarted = progress && progress.sessions_completed > 0

  return (
    <button
      onClick={onClick}
      className={clsx(
        'list-item w-full text-left reg-corners',
        isActive && 'border-coral bg-coral-light'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={clsx(
            'status-light',
            isStarted ? 'status-light-active' : 'status-light-inactive'
          )} />
          <h3 className="font-medium text-black text-sm">
            {track.name}
          </h3>
          {isActive && (
            <span className="bg-coral-light text-black text-[10px] font-semibold px-1.5 py-0.5 border border-coral">
              ACTIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <span className="tag">{getLanguageLabel(track.language)}</span>
          <span className="tag tag-accent">{getLevelLabel(track.level)}</span>
        </div>
      </div>

      {track.description && (
        <p className="text-xs text-gray-600 mb-3 line-clamp-2">
          {track.description}
        </p>
      )}

      {/* Progress bar */}
      <div className="progress-bar mb-2">
        <div
          className="progress-fill transition-all duration-500"
          style={{ width: `${completionPercentage}%` }}
        />
      </div>

      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          {completedTopics}/{track.total_topics} topics
        </div>
        {progress && (
          <div className="coord-display">
            {progress.average_score?.toFixed(1) || '0.0'}/10
          </div>
        )}
      </div>
    </button>
  )
}
