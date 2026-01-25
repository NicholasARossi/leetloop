'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type ReviewItem } from '@/lib/api'
import { formatDistanceToNow, format, isPast } from 'date-fns'
import { clsx } from 'clsx'

export default function ReviewsPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [reviews, setReviews] = useState<ReviewItem[]>([])
  const [completing, setCompleting] = useState<string | null>(null)

  useEffect(() => {
    loadReviews()
  }, [userId])

  async function loadReviews() {
    if (!userId) return

    setLoading(true)
    try {
      // Get all reviews including future ones
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/reviews/${userId}?limit=50&include_future=true`
      )
      const data = await response.json()
      setReviews(data)
    } catch (err) {
      console.error('Failed to load reviews:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleComplete(reviewId: string, success: boolean) {
    setCompleting(reviewId)
    try {
      await leetloopApi.completeReview(reviewId, success)
      // Reload reviews
      await loadReviews()
    } catch (err) {
      console.error('Failed to complete review:', err)
    } finally {
      setCompleting(null)
    }
  }

  const dueReviews = reviews.filter((r) => isPast(new Date(r.next_review)))
  const upcomingReviews = reviews.filter((r) => !isPast(new Date(r.next_review)))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-slate-500">Loading reviews...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Review Queue
        </h1>
        <span className="text-sm text-slate-500">
          {dueReviews.length} due now
        </span>
      </div>

      {/* Due Now */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-red-50 dark:bg-red-900/20">
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-400">
            Due Now ({dueReviews.length})
          </h2>
        </div>

        {dueReviews.length === 0 ? (
          <div className="flex items-center justify-center h-32">
            <p className="text-slate-500">
              All caught up! No reviews due right now.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {dueReviews.map((review) => (
              <div key={review.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <a
                      href={`https://leetcode.com/problems/${review.problem_slug}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-slate-900 dark:text-white hover:text-brand-600"
                    >
                      {review.problem_title || review.problem_slug}
                    </a>
                    <p className="text-sm text-slate-500 mt-1">
                      {review.reason || 'Needs review'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Review #{review.review_count + 1} &middot; Interval: {review.interval_days} day(s)
                    </p>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <a
                      href={`https://leetcode.com/problems/${review.problem_slug}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary text-sm py-1.5"
                    >
                      Review
                    </a>
                    <button
                      onClick={() => handleComplete(review.id, true)}
                      disabled={completing === review.id}
                      className={clsx(
                        'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                        'bg-green-100 text-green-700 hover:bg-green-200',
                        'dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50',
                        completing === review.id && 'opacity-50 cursor-wait'
                      )}
                    >
                      Pass
                    </button>
                    <button
                      onClick={() => handleComplete(review.id, false)}
                      disabled={completing === review.id}
                      className={clsx(
                        'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                        'bg-red-100 text-red-700 hover:bg-red-200',
                        'dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50',
                        completing === review.id && 'opacity-50 cursor-wait'
                      )}
                    >
                      Fail
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upcoming */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Upcoming ({upcomingReviews.length})
          </h2>
        </div>

        {upcomingReviews.length === 0 ? (
          <div className="flex items-center justify-center h-32">
            <p className="text-slate-500">No upcoming reviews scheduled.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {upcomingReviews.slice(0, 10).map((review) => (
              <div key={review.id} className="p-4 flex items-center justify-between">
                <div>
                  <span className="font-medium text-slate-900 dark:text-white">
                    {review.problem_title || review.problem_slug}
                  </span>
                  <p className="text-sm text-slate-500">
                    {review.reason || 'Scheduled review'}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    {formatDistanceToNow(new Date(review.next_review), { addSuffix: true })}
                  </span>
                  <p className="text-xs text-slate-400">
                    {format(new Date(review.next_review), 'MMM d, yyyy')}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How it works */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          How Spaced Repetition Works
        </h2>
        <div className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
          <p>
            When you fail a problem, it gets added to your review queue with a 1-day interval.
          </p>
          <p>
            <strong className="text-green-600">Pass:</strong> The interval doubles (up to 30 days).
            You'll see the problem again after the new interval.
          </p>
          <p>
            <strong className="text-red-600">Fail:</strong> The interval resets to 1 day.
            You'll need to review it again tomorrow.
          </p>
          <p>
            This system ensures you spend more time on problems you struggle with, while
            gradually spacing out problems you've mastered.
          </p>
        </div>
      </div>
    </div>
  )
}
