'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type BookProgressResponse,
  type LanguageDashboardSummary,
} from '@/lib/api'
import { BookProgressView } from '@/components/language'

export default function BookProgressPage() {
  const { userId } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bookProgress, setBookProgress] = useState<BookProgressResponse | null>(null)

  const loadData = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      // Get the active track ID from the dashboard summary
      const dashboard: LanguageDashboardSummary = await leetloopApi.getLanguageDashboard(userId)

      if (!dashboard.has_active_track || !dashboard.active_track) {
        setError('No active language track. Set one from the Dashboard.')
        return
      }

      const data = await leetloopApi.getBookProgress(dashboard.active_track.id, userId)
      setBookProgress(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to load book progress.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadData()
  }, [loadData])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center gap-3 mb-2">
          <div className="status-light status-light-active" />
          <h1 className="heading-accent text-xl">BOOK PROGRESS</h1>
        </div>
        <p className="text-sm text-gray-600">
          Track your progress through the book chapter by chapter.
        </p>
      </div>

      {error && (
        <div className="card p-8 text-center">
          <p className="text-coral mb-4">{error}</p>
          <button onClick={loadData} className="btn btn-primary">
            Retry
          </button>
        </div>
      )}

      {!error && (
        <BookProgressView data={bookProgress} loading={loading} />
      )}
    </div>
  )
}
