'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type SystemDesignReviewItem,
} from '@/lib/api'
import { clsx } from 'clsx'

export default function SystemDesignReviewsPage() {
  const { userId } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reviews, setReviews] = useState<SystemDesignReviewItem[]>([])
  const [completing, setCompleting] = useState<string | null>(null)

  useEffect(() => {
    loadReviews()
  }, [userId])

  async function loadReviews() {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      const data = await leetloopApi.getSystemDesignReviews(userId, 20)
      setReviews(data)
    } catch (err) {
      console.error('Failed to load reviews:', err)
      setError('Failed to load review queue.')
    } finally {
      setLoading(false)
    }
  }

  async function handleComplete(reviewId: string, success: boolean) {
    setCompleting(reviewId)
    try {
      const result = await leetloopApi.completeSystemDesignReview(reviewId, success)

      // Update the review in the list
      setReviews(prev => prev.map(r => {
        if (r.id === reviewId) {
          return {
            ...r,
            next_review: result.next_review,
            interval_days: result.new_interval_days,
            review_count: r.review_count + 1,
            last_reviewed: new Date().toISOString(),
          }
        }
        return r
      }))

      // Remove from list since it's no longer due
      setTimeout(() => {
        setReviews(prev => prev.filter(r => r.id !== reviewId))
      }, 1000)
    } catch (err) {
      console.error('Failed to complete review:', err)
      setError('Failed to update review.')
    } finally {
      setCompleting(null)
    }
  }

  async function handleStartSession(review: SystemDesignReviewItem) {
    if (!userId || !review.track_id) return

    try {
      const session = await leetloopApi.createSystemDesignSession(userId, {
        track_id: review.track_id,
        topic: review.topic,
        session_type: 'review',
      })
      router.push(`/system-design/session/${session.id}`)
    } catch (err) {
      console.error('Failed to start review session:', err)
      setError('Failed to start review session.')
    }
  }

  const dueReviews = reviews.filter(r => new Date(r.next_review) <= new Date())
  const upcomingReviews = reviews.filter(r => new Date(r.next_review) > new Date())

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading review queue...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center gap-3 mb-2">
          <div className={clsx(
            'status-light',
            dueReviews.length > 0 ? 'status-light-active' : 'status-light-inactive'
          )} />
          <h1 className="heading-accent text-xl">SYSTEM DESIGN REVIEWS</h1>
        </div>
        <p className="text-sm text-gray-600">
          Topics you struggled with are added here for spaced repetition.
          Review them to strengthen your understanding.
        </p>
      </div>

      {error && (
        <div className="card border-l-4 border-l-coral">
          <p className="text-coral text-sm">{error}</p>
        </div>
      )}

      {/* Due Reviews */}
      {dueReviews.length > 0 ? (
        <div>
          <h2 className="section-title text-coral">
            Due Now ({dueReviews.length})
          </h2>
          <div className="space-y-3">
            {dueReviews.map((review) => (
              <div key={review.id} className="card border-l-4 border-l-coral">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-medium text-black">
                      {review.topic}
                    </h3>
                    {review.reason && (
                      <p className="text-xs text-gray-500 mt-1">
                        {review.reason}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="tag text-xs">
                      {review.review_count} reviews
                    </span>
                    <span className="tag text-xs">
                      {review.interval_days}d interval
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-3">
                  {review.track_id && (
                    <button
                      onClick={() => handleStartSession(review)}
                      className="btn btn-primary text-sm"
                    >
                      Practice Again
                    </button>
                  )}
                  <button
                    onClick={() => handleComplete(review.id, true)}
                    disabled={completing === review.id}
                    className={clsx(
                      'btn text-sm bg-green-50 border-green-500 text-green-700',
                      completing === review.id && 'opacity-50'
                    )}
                  >
                    {completing === review.id ? 'Updating...' : 'Mark Passed'}
                  </button>
                  <button
                    onClick={() => handleComplete(review.id, false)}
                    disabled={completing === review.id}
                    className={clsx(
                      'btn text-sm bg-red-50 border-coral text-coral',
                      completing === review.id && 'opacity-50'
                    )}
                  >
                    Still Struggling
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="card text-center py-8">
          <div className="text-4xl mb-4">complete</div>
          <h2 className="font-semibold text-black mb-2">
            No Reviews Due
          </h2>
          <p className="text-sm text-gray-600">
            Complete system design sessions to add topics to your review queue.
          </p>
          <button
            onClick={() => router.push('/system-design')}
            className="btn btn-primary mt-4"
          >
            Start a Session
          </button>
        </div>
      )}

      {/* Upcoming Reviews */}
      {upcomingReviews.length > 0 && (
        <div>
          <h2 className="section-title">
            Upcoming ({upcomingReviews.length})
          </h2>
          <div className="space-y-2">
            {upcomingReviews.map((review) => {
              const nextDate = new Date(review.next_review)
              const daysUntil = Math.ceil((nextDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24))

              return (
                <div key={review.id} className="list-item flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="status-light status-light-inactive" />
                    <span className="font-medium text-sm">{review.topic}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      in {daysUntil} day{daysUntil !== 1 ? 's' : ''}
                    </span>
                    <span className="coord-display">
                      {review.interval_days}d
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Algorithm Explanation */}
      <div className="card bg-gray-50">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
          Spaced Repetition Algorithm
        </h3>
        <div className="grid grid-cols-2 gap-4 text-xs text-gray-600">
          <div>
            <span className="font-medium text-green-600">Mark Passed</span>
            <p>Interval doubles (max 30 days)</p>
          </div>
          <div>
            <span className="font-medium text-coral">Still Struggling</span>
            <p>Interval resets to 1 day</p>
          </div>
        </div>
      </div>
    </div>
  )
}
