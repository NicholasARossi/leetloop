'use client'

import { clsx } from 'clsx'
import Link from 'next/link'
import type { SystemDesignDashboardSummary, SystemDesignReviewItem } from '@/lib/api'

interface SystemDesignDashboardCardProps {
  data: SystemDesignDashboardSummary
  onStartSession?: (trackId: string, topic: string) => void
  onStartReview?: (review: SystemDesignReviewItem) => void
}

export function SystemDesignDashboardCard({
  data,
  onStartSession,
  onStartReview,
}: SystemDesignDashboardCardProps) {
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

  // If no active track, show setup prompt
  if (!data.has_active_track) {
    return (
      <div className="card border-sky-500 bg-gradient-to-br from-white to-sky-50">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 bg-sky-500 rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">SD</span>
          </div>
          <span className="font-semibold text-sm text-sky-700">System Design Practice</span>
          <span className="bg-green-100 text-green-800 text-[10px] font-semibold px-1.5 py-0.5 ml-1">NEW</span>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Prepare for system design interviews with guided practice sessions and AI grading.
        </p>

        <Link
          href="/system-design"
          className="btn-primary inline-block bg-sky-500 hover:bg-sky-600 text-sm"
        >
          Choose a Track
        </Link>
      </div>
    )
  }

  return (
    <div className="card border-sky-500 bg-gradient-to-br from-white to-sky-50">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-sky-500 rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">SD</span>
          </div>
          <span className="font-semibold text-sm text-sky-700">System Design Practice</span>
        </div>

        {data.reviews_due_count > 0 && (
          <span className="inline-flex items-center gap-1 bg-amber-100 border border-amber-400 px-2 py-1 text-[11px] text-amber-800">
            {data.reviews_due_count} review{data.reviews_due_count !== 1 ? 's' : ''} due
          </span>
        )}
      </div>

      {/* Next Topic */}
      {data.next_topic && data.active_track && (
        <>
          <p className="text-[13px] text-gray-600 mb-3">
            Today&apos;s topic from your <strong>{data.active_track.name}</strong> track:
          </p>

          <button
            onClick={() => onStartSession?.(data.next_topic!.track_id, data.next_topic!.topic_name)}
            className="w-full text-left p-4 bg-white border-2 border-sky-200 hover:border-sky-400 transition-all hover:translate-x-1 mb-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  'bg-amber-400'
                )} />
                <div>
                  <div className="font-semibold text-sm">{data.next_topic.topic_name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {getTrackTypeLabel(data.next_topic.track_type)} Track &bull; Topic {data.next_topic.topic_order + 1} of {data.next_topic.total_topics}
                  </div>
                  {data.next_topic.example_systems.length > 0 && (
                    <div className="text-[11px] text-gray-400 mt-1">
                      Examples: {data.next_topic.example_systems.slice(0, 3).join(', ')}
                    </div>
                  )}
                </div>
              </div>
              <span className="bg-sky-500 hover:bg-sky-600 text-white px-3 py-1.5 text-xs font-semibold">
                Start Session
              </span>
            </div>
          </button>
        </>
      )}

      {/* Reviews Due */}
      {data.reviews_due && data.reviews_due.length > 0 && (
        <div className="pt-3 border-t border-sky-200">
          <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-2">Reviews Due</p>
          {data.reviews_due.slice(0, 2).map((review) => (
            <button
              key={review.id}
              onClick={() => onStartReview?.(review)}
              className="w-full text-left p-3 bg-amber-50 border-2 border-amber-200 hover:border-amber-400 transition-all hover:translate-x-1 mb-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-amber-400" />
                  <div>
                    <div className="font-semibold text-sm">{review.topic}</div>
                    <div className="text-xs text-gray-500">
                      {review.reason || 'Spaced repetition review'}
                    </div>
                  </div>
                </div>
                <span className="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 text-xs font-semibold">
                  Review
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Stats row */}
      {(data.recent_score !== undefined || data.sessions_this_week > 0) && (
        <div className="flex items-center gap-4 pt-3 mt-3 border-t border-sky-200 text-xs text-gray-500">
          {data.recent_score !== undefined && (
            <span>Last score: <strong className="text-black">{data.recent_score.toFixed(1)}/10</strong></span>
          )}
          {data.sessions_this_week > 0 && (
            <span>{data.sessions_this_week} session{data.sessions_this_week !== 1 ? 's' : ''} this week</span>
          )}
        </div>
      )}

      {/* Link to full system design page */}
      <div className="mt-3 text-right">
        <Link
          href="/system-design"
          className="text-xs text-sky-600 hover:text-sky-800 hover:underline"
        >
          View all tracks &rarr;
        </Link>
      </div>
    </div>
  )
}
