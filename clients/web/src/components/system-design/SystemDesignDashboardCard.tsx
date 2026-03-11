'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import Link from 'next/link'
import type { SystemDesignDashboardSummary, SystemDesignReviewItem } from '@/lib/api'

interface SystemDesignDashboardCardProps {
  data: SystemDesignDashboardSummary
  onStartReview?: (review: SystemDesignReviewItem) => void
}

export function SystemDesignDashboardCard({
  data,
  onStartReview,
}: SystemDesignDashboardCardProps) {
  const [showScenario, setShowScenario] = useState(false)

  const getTrackTypeLabel = (type: string) => {
    switch (type) {
      case 'mle': return 'ML Engineering'
      case 'traditional': return 'Traditional'
      case 'infra': return 'Infrastructure'
      case 'data': return 'Data Engineering'
      default: return type.toUpperCase()
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case 'pass': return 'bg-coral-light text-black border-coral'
      case 'borderline': return 'bg-gray-100 text-gray-700 border-gray-400'
      case 'fail': return 'bg-gray-200 text-black border-black'
      default: return 'bg-gray-100 text-gray-700 border-gray-300'
    }
  }

  const oral = data.oral_session
  const gradedCount = oral?.questions.filter(q => q.status === 'graded').length ?? 0
  const isSessionCompleted = oral?.status === 'completed'

  // If no active track, show setup prompt
  if (!data.has_active_track) {
    return (
      <div className="card border-coral bg-gradient-to-br from-white to-gray-50">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 bg-coral rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">SD</span>
          </div>
          <span className="font-semibold text-sm text-gray-700">System Design Practice</span>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Practice system design orally. Record or upload your answer, get AI grading with cited evidence.
        </p>
        <Link href="/system-design" className="btn-primary inline-block text-sm">
          Choose a Track
        </Link>
      </div>
    )
  }

  return (
    <div className="card border-coral bg-gradient-to-br from-white to-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-coral rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">SD</span>
          </div>
          <span className="font-semibold text-sm text-gray-700">System Design Practice</span>
        </div>

        {data.reviews_due_count > 0 && (
          <span className="inline-flex items-center gap-1 bg-gray-100 border border-gray-400 px-2 py-1 text-[11px] text-gray-700">
            {data.reviews_due_count} review{data.reviews_due_count !== 1 ? 's' : ''} due
          </span>
        )}
      </div>

      {/* Track info */}
      {data.next_topic && (
        <div className="mb-3">
          <p className="text-[13px] text-gray-600 mb-0.5">
            {oral ? oral.topic : <>Next up: <strong>{data.next_topic.topic_name}</strong></>}
          </p>
          <p className="text-[11px] text-gray-400">
            {getTrackTypeLabel(data.next_topic.track_type)} Track &bull; Topic {data.next_topic.topic_order + 1} of {data.next_topic.total_topics}
          </p>
        </div>
      )}

      {/* Oral session questions inline */}
      {oral ? (
        <div className="mb-3">
          {/* Scenario (collapsed by default) */}
          <button
            onClick={() => setShowScenario(!showScenario)}
            className="text-[11px] text-gray-400 hover:text-gray-600 mb-2 flex items-center gap-1"
          >
            <span>{showScenario ? 'Hide' : 'Show'} scenario</span>
            <svg className={clsx('w-3 h-3 transition-transform', showScenario && 'rotate-180')} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showScenario && (
            <div className="p-3 bg-coral-light border-l-4 border-l-coral mb-3 text-xs text-gray-800">
              {oral.scenario}
            </div>
          )}

          {/* Progress bar */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">
              {gradedCount} of {oral.questions.length} answered
            </span>
            <div className="flex-1 h-1 bg-gray-200 rounded">
              <div
                className="h-1 bg-coral rounded transition-all"
                style={{ width: `${(gradedCount / Math.max(oral.questions.length, 1)) * 100}%` }}
              />
            </div>
          </div>

          {/* Overall score if session completed */}
          {isSessionCompleted && data.recent_score != null && (
            <div className="flex items-center justify-between py-2 px-3 bg-gray-50 border border-gray-200 mb-2">
              <span className="text-[11px] text-gray-500">Session score</span>
              <div className="flex items-center gap-2">
                <span className={clsx('font-mono font-bold text-sm', getScoreColor(data.recent_score))}>
                  {data.recent_score.toFixed(1)}/10
                </span>
              </div>
            </div>
          )}

          {/* Sub-questions list */}
          <div className="space-y-1.5">
            {oral.questions.map((q, i) => (
              <div key={q.id} className="flex items-center gap-2">
                {/* Status dot */}
                <div className={clsx(
                  'w-5 h-5 flex items-center justify-center text-[10px] font-bold flex-shrink-0 border',
                  q.status === 'graded'
                    ? 'bg-coral border-coral text-white'
                    : 'bg-white border-gray-300 text-gray-400'
                )}>
                  {q.status === 'graded' ? (q.overall_score ? Math.round(q.overall_score) : '\u2713') : (i + 1)}
                </div>

                {/* Focus area + action */}
                <div className="flex-1 min-w-0 flex items-center justify-between">
                  <span className={clsx(
                    'text-xs font-mono uppercase truncate',
                    q.status === 'graded' ? 'text-gray-600' : 'text-gray-800'
                  )}>
                    {q.focus_area}
                  </span>

                  {q.status === 'graded' ? (
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {q.verdict && (
                        <span className={clsx('text-[9px] px-1.5 py-0.5 border', getVerdictStyle(q.verdict))}>
                          {q.verdict}
                        </span>
                      )}
                      <Link
                        href={`/system-design/session/${oral.id}#q${i}`}
                        className="text-[10px] text-coral hover:underline"
                      >
                        View
                      </Link>
                    </div>
                  ) : (
                    <Link
                      href={`/system-design?session=${oral.id}&q=${i}`}
                      className="text-[10px] font-semibold text-coral hover:underline flex-shrink-0"
                    >
                      Record
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* View Full Session link */}
          {gradedCount > 0 && (
            <div className="mt-2">
              <Link
                href={`/system-design/session/${oral.id}`}
                className="text-xs text-coral hover:underline"
              >
                View Full Session &rarr;
              </Link>
            </div>
          )}
        </div>
      ) : (
        /* Fallback: link to /system-design when no oral session */
        data.next_topic && (
          <div className="mb-3">
            <Link
              href="/system-design"
              className="w-full flex items-center justify-between p-4 bg-white border-2 border-gray-200 hover:border-coral transition-all hover:translate-x-1"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-coral/10 border-2 border-coral flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-coral" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
                <div>
                  <div className="font-semibold text-sm">Start Oral Practice</div>
                  <div className="text-[11px] text-gray-400">Record or upload audio</div>
                </div>
              </div>
              <span className="bg-coral text-white px-3 py-1.5 text-xs font-semibold flex-shrink-0">Go</span>
            </Link>
          </div>
        )
      )}

      {/* Reviews Due */}
      {data.reviews_due && data.reviews_due.length > 0 && (
        <div className="pt-3 border-t border-gray-200">
          <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-2">Reviews Due</p>
          {data.reviews_due.slice(0, 2).map((review) => (
            <button
              key={review.id}
              onClick={() => onStartReview?.(review)}
              className="w-full text-left p-3 bg-gray-50 border-2 border-gray-200 hover:border-gray-400 transition-all hover:translate-x-1 mb-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-gray-400" />
                  <div>
                    <div className="font-semibold text-sm">{review.topic}</div>
                    <div className="text-xs text-gray-500">{review.reason || 'Spaced repetition review'}</div>
                  </div>
                </div>
                <span className="bg-gray-700 hover:bg-black text-white px-3 py-1.5 text-xs font-semibold">Review</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Stats row */}
      {data.sessions_this_week > 0 && (
        <div className="flex items-center gap-4 pt-3 mt-3 border-t border-gray-200 text-xs text-gray-500">
          <span>{data.sessions_this_week} session{data.sessions_this_week !== 1 ? 's' : ''} this week</span>
        </div>
      )}

      {/* Link to full system design page */}
      <div className="mt-3 text-right">
        <Link href="/system-design" className="text-xs text-coral hover:text-coral-dark hover:underline">
          View all tracks &rarr;
        </Link>
      </div>
    </div>
  )
}
