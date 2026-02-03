'use client'

import { clsx } from 'clsx'
import type { SystemDesignTrackSummary, UserTrackProgressData } from '@/lib/api'

interface TrackCardProps {
  track: SystemDesignTrackSummary
  progress?: UserTrackProgressData
  onClick?: () => void
}

export function TrackCard({ track, progress, onClick }: TrackCardProps) {
  const completedTopics = progress?.completed_topics?.length || 0
  const completionPercentage = track.total_topics > 0
    ? (completedTopics / track.total_topics) * 100
    : 0

  const getTrackTypeLabel = (type: string) => {
    switch (type) {
      case 'mle':
        return 'ML Engineering'
      case 'traditional':
        return 'Traditional'
      case 'infra':
        return 'Infrastructure'
      case 'data':
        return 'Data Engineering'
      default:
        return type.toUpperCase()
    }
  }

  const isStarted = progress && progress.sessions_completed > 0

  return (
    <button
      onClick={onClick}
      className="list-item w-full text-left reg-corners"
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
        </div>
        <span className="tag">
          {getTrackTypeLabel(track.track_type)}
        </span>
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
