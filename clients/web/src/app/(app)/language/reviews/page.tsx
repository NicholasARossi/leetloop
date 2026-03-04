'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type LanguageReviewItem } from '@/lib/api'

export default function ReviewsPage() {
  const { userId } = useAuth()

  const [reviews, setReviews] = useState<LanguageReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState<string | null>(null)

  const loadReviews = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    try {
      const data = await leetloopApi.getLanguageReviews(userId, 20)
      setReviews(data)
    } catch (err) {
      console.error('[Reviews] Failed to load:', err)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadReviews()
  }, [loadReviews])

  async function handleComplete(reviewId: string, success: boolean) {
    setCompleting(reviewId)
    try {
      await leetloopApi.completeLanguageReview(reviewId, success)
      setReviews((prev) => prev.filter((r) => r.id !== reviewId))
    } catch (err) {
      console.error('[Reviews] Failed to complete review:', err)
    } finally {
      setCompleting(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <p className="text-gray-500 text-sm">Chargement des révisions...</p>
      </div>
    )
  }

  if (reviews.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500 text-sm">Aucune révision en attente.</p>
        <p className="text-gray-400 text-xs mt-1">
          Les révisions apparaîtront après vos exercices.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="section-title">Révisions</h2>
        <p className="text-xs text-gray-500">
          {reviews.length} révision{reviews.length > 1 ? 's' : ''} en attente
        </p>
      </div>

      <div className="space-y-3">
        {reviews.map((review) => {
          const isCompleting = completing === review.id
          return (
            <div key={review.id} className="card-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{review.topic}</p>
                  {review.reason && (
                    <p className="text-xs text-gray-500 mt-1">{review.reason}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-[10px] text-gray-400">
                      Intervalle : {review.interval_days}j
                    </span>
                    <span className="text-[10px] text-gray-400">
                      Révisions : {review.review_count}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleComplete(review.id, false)}
                    disabled={isCompleting}
                    className="px-3 py-1.5 text-xs border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50"
                    style={{
                      clipPath: 'polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px)',
                    }}
                  >
                    Raté
                  </button>
                  <button
                    onClick={() => handleComplete(review.id, true)}
                    disabled={isCompleting}
                    className="btn-primary px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    <span className="relative z-10">Réussi</span>
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
