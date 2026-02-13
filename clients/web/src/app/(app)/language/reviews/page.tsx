'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type LanguageReviewItem } from '@/lib/api'
import { clsx } from 'clsx'

export default function LanguageReviewsPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [reviews, setReviews] = useState<LanguageReviewItem[]>([])
  const [completing, setCompleting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadReviews() {
      if (!userId) return

      setLoading(true)
      try {
        const data = await leetloopApi.getLanguageReviews(userId)
        setReviews(data)
      } catch (err) {
        console.error('Failed to load reviews:', err)
        setError('Failed to load reviews.')
      } finally {
        setLoading(false)
      }
    }

    loadReviews()
  }, [userId])

  async function handleComplete(reviewId: string, success: boolean) {
    setCompleting(reviewId)
    try {
      const result = await leetloopApi.completeLanguageReview(reviewId, success)
      // Remove from list or update
      setReviews(prev => prev.filter(r => r.id !== reviewId))
    } catch (err) {
      console.error('Failed to complete review:', err)
      setError('Failed to complete review.')
    } finally {
      setCompleting(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading reviews...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex items-center gap-3 mb-2">
          <div className="status-light status-light-active" />
          <h1 className="heading-accent text-xl">LANGUAGE REVIEWS</h1>
        </div>
        <p className="text-sm text-gray-600">
          Topics due for spaced repetition review. Pass to increase interval, fail to reset.
        </p>
      </div>

      {error && (
        <div className="card border-l-4 border-l-coral">
          <p className="text-coral text-sm">{error}</p>
        </div>
      )}

      {reviews.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-gray-500">No reviews due right now.</p>
          <p className="text-sm text-gray-400 mt-2">
            Reviews are added when you score below 7/10 on an exercise.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <div key={review.id} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-sm">{review.topic}</h3>
                  <p className="text-xs text-gray-500 mt-1">
                    {review.reason || 'Spaced repetition review'}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    <span>Interval: {review.interval_days} day{review.interval_days !== 1 ? 's' : ''}</span>
                    <span>Reviews: {review.review_count}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleComplete(review.id, false)}
                    disabled={completing === review.id}
                    className={clsx(
                      'px-4 py-2 border-2 border-gray-300 text-sm font-medium',
                      'hover:border-black transition-colors',
                      completing === review.id && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    Fail
                  </button>
                  <button
                    onClick={() => handleComplete(review.id, true)}
                    disabled={completing === review.id}
                    className={clsx(
                      'px-4 py-2 border-2 border-coral text-coral text-sm font-medium',
                      'hover:bg-coral-light transition-colors',
                      completing === review.id && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    Pass
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
