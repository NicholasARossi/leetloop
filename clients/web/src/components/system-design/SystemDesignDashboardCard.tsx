'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import Link from 'next/link'
import type { SystemDesignDashboardSummary, SystemDesignReviewItem, AttemptGrade } from '@/lib/api'
import { DashboardQuestionCard } from './DashboardQuestionCard'

interface SystemDesignDashboardCardProps {
  data: SystemDesignDashboardSummary
  onStartSession?: (trackId: string, topic: string) => void
  onStartReview?: (review: SystemDesignReviewItem) => void
  onQuestionGraded?: (questionId: string, grade: AttemptGrade) => void
}

export function SystemDesignDashboardCard({
  data,
  onStartSession,
  onStartReview,
  onQuestionGraded,
}: SystemDesignDashboardCardProps) {
  const [gradedQuestions, setGradedQuestions] = useState<Set<string>>(new Set())

  const handleQuestionGraded = (questionId: string, grade: AttemptGrade) => {
    setGradedQuestions(prev => new Set(prev).add(questionId))
    onQuestionGraded?.(questionId, grade)
  }

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
      <div className="card border-coral bg-gradient-to-br from-white to-gray-50">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 bg-coral rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">SD</span>
          </div>
          <span className="font-semibold text-sm text-gray-700">System Design Practice</span>
          <span className="bg-coral-light text-black text-[10px] font-semibold px-1.5 py-0.5 ml-1">NEW</span>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Prepare for system design interviews with guided practice sessions and AI grading.
        </p>

        <Link
          href="/system-design"
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

      {/* Daily Questions */}
      {data.next_topic && data.active_track && (
        <>
          <div className="mb-3">
            <p className="text-[13px] text-gray-600">
              Today&apos;s practice on <strong>{data.next_topic.topic_name}</strong>:
            </p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              {getTrackTypeLabel(data.next_topic.track_type)} Track &bull; Topic {data.next_topic.topic_order + 1} of {data.next_topic.total_topics}
            </p>
          </div>

          {/* Show daily questions if available */}
          {data.daily_questions && data.daily_questions.length > 0 ? (
            <div className="mb-3">
              {/* Scenario (shared context) - show once */}
              {data.daily_questions[0]?.scenario && (
                <div className="p-3 bg-coral-light border-l-4 border-l-coral mb-3 text-xs text-gray-800">
                  <span className="font-semibold text-black">Scenario: </span>
                  {data.daily_questions[0].scenario}
                </div>
              )}

              {/* Progress indicator */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">
                  {data.daily_questions.filter(q => q.completed).length + gradedQuestions.size} of {data.daily_questions.length} answered
                </span>
                <div className="flex-1 h-1 bg-gray-200 rounded">
                  <div
                    className="h-1 bg-coral rounded"
                    style={{
                      width: `${((data.daily_questions.filter(q => q.completed).length + gradedQuestions.size) / data.daily_questions.length) * 100}%`
                    }}
                  />
                </div>
              </div>

              {/* Sub-questions */}
              <div className="space-y-2">
                {data.daily_questions.map((question, index) => (
                  <DashboardQuestionCard
                    key={question.id}
                    question={question}
                    index={index}
                    showScenario={false}
                    onGraded={handleQuestionGraded}
                  />
                ))}
              </div>
            </div>
          ) : (
            /* Fallback: Start Session button if no questions available */
            <button
              onClick={() => onStartSession?.(data.next_topic!.track_id, data.next_topic!.topic_name)}
              className="w-full text-left p-4 bg-white border-2 border-gray-200 hover:border-gray-400 transition-all hover:translate-x-1 mb-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={clsx(
                    'w-2 h-2 rounded-full',
                    'bg-gray-400'
                  )} />
                  <div>
                    <div className="font-semibold text-sm">{data.next_topic.topic_name}</div>
                    {data.next_topic.example_systems.length > 0 && (
                      <div className="text-[11px] text-gray-400 mt-1">
                        Examples: {data.next_topic.example_systems.slice(0, 3).join(', ')}
                      </div>
                    )}
                  </div>
                </div>
                <span className="bg-coral hover:bg-coral-dark text-white px-3 py-1.5 text-xs font-semibold">
                  Start Session
                </span>
              </div>
            </button>
          )}
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
      {(data.recent_score !== undefined || data.sessions_this_week > 0) && (
        <div className="flex items-center gap-4 pt-3 mt-3 border-t border-gray-200 text-xs text-gray-500">
          {data.recent_score != null && (
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
          className="text-xs text-coral hover:text-coral-dark hover:underline"
        >
          View all tracks &rarr;
        </Link>
      </div>
    </div>
  )
}
