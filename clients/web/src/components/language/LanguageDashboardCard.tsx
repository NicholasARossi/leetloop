'use client'

import { clsx } from 'clsx'
import Link from 'next/link'
import type { LanguageDashboardSummary, LanguageReviewItem } from '@/lib/api'

interface LanguageDashboardCardProps {
  data: LanguageDashboardSummary
  onStartExercise?: (trackId: string, topic: string) => void
  onStartReview?: (review: LanguageReviewItem) => void
}

const languageLabels: Record<string, string> = {
  french: 'French',
  chinese: 'Chinese',
  spanish: 'Spanish',
  german: 'German',
  japanese: 'Japanese',
  italian: 'Italian',
  portuguese: 'Portuguese',
  korean: 'Korean',
}

export function LanguageDashboardCard({
  data,
  onStartExercise,
  onStartReview,
}: LanguageDashboardCardProps) {
  const getLanguageLabel = (lang: string) => languageLabels[lang] || lang

  if (!data.has_active_track) {
    return (
      <div className="card border-coral bg-gradient-to-br from-white to-gray-50">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 bg-coral rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">L</span>
          </div>
          <span className="font-semibold text-sm text-gray-700">Language Practice</span>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Study languages with AI-generated exercises, immersive grading, and spaced repetition.
        </p>

        <Link
          href="/language"
          className="btn-primary inline-block text-sm"
        >
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
            <span className="text-white text-xs font-bold">L</span>
          </div>
          <span className="font-semibold text-sm text-gray-700">Language Practice</span>
        </div>

        {data.reviews_due_count > 0 && (
          <span className="inline-flex items-center gap-1 bg-gray-100 border border-gray-400 px-2 py-1 text-[11px] text-gray-700">
            {data.reviews_due_count} review{data.reviews_due_count !== 1 ? 's' : ''} due
          </span>
        )}
      </div>

      {/* Next Topic */}
      {data.next_topic && data.active_track && (
        <>
          <div className="mb-3">
            <p className="text-[13px] text-gray-600">
              Next up: <strong>{data.next_topic.topic_name}</strong>
            </p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              {getLanguageLabel(data.next_topic.language)} {data.next_topic.level.toUpperCase()} &bull; Topic {data.next_topic.topic_order + 1} of {data.next_topic.total_topics}
            </p>
          </div>

          <button
            onClick={() => onStartExercise?.(data.next_topic!.track_id, data.next_topic!.topic_name)}
            className="w-full text-left p-4 bg-white border-2 border-gray-200 hover:border-gray-400 transition-all hover:translate-x-1 mb-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-gray-400" />
                <div>
                  <div className="font-semibold text-sm">{data.next_topic.topic_name}</div>
                  {data.next_topic.key_concepts.length > 0 && (
                    <div className="text-[11px] text-gray-400 mt-1">
                      {data.next_topic.key_concepts.slice(0, 3).join(', ')}
                    </div>
                  )}
                </div>
              </div>
              <span className="bg-coral hover:bg-coral-dark text-white px-3 py-1.5 text-xs font-semibold">
                Practice
              </span>
            </div>
          </button>
        </>
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
                    <div className="text-xs text-gray-500">
                      {review.reason || 'Spaced repetition review'}
                    </div>
                  </div>
                </div>
                <span className="bg-gray-700 hover:bg-black text-white px-3 py-1.5 text-xs font-semibold">
                  Review
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Stats row */}
      {(data.recent_score !== undefined || data.exercises_this_week > 0) && (
        <div className="flex items-center gap-4 pt-3 mt-3 border-t border-gray-200 text-xs text-gray-500">
          {data.recent_score != null && (
            <span>Last score: <strong className="text-black">{data.recent_score.toFixed(1)}/10</strong></span>
          )}
          {data.exercises_this_week > 0 && (
            <span>{data.exercises_this_week} exercise{data.exercises_this_week !== 1 ? 's' : ''} this week</span>
          )}
        </div>
      )}

      {/* Link to full page */}
      <div className="mt-3 text-right">
        <Link
          href="/language"
          className="text-xs text-coral hover:text-coral-dark hover:underline"
        >
          View all tracks &rarr;
        </Link>
      </div>
    </div>
  )
}
