'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type LifeOpsChecklistResponse,
  type LifeOpsStatsResponse,
} from '@/lib/api'
import { ChecklistView } from '@/components/life-ops'

export default function LifeOpsPage() {
  const { userId } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [checklist, setChecklist] = useState<LifeOpsChecklistResponse | null>(null)
  const [currentStreak, setCurrentStreak] = useState(0)

  const loadChecklist = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      const [checklistData, statsData] = await Promise.all([
        leetloopApi.getLifeOpsChecklist(userId),
        leetloopApi.getLifeOpsStats(userId).catch(() => null),
      ])
      setChecklist(checklistData)
      if (statsData) {
        setCurrentStreak(statsData.streak.current_streak)
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to load checklist.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadChecklist()
  }, [loadChecklist])

  async function handleToggle(itemId: string): Promise<void> {
    const result = await leetloopApi.toggleLifeOpsItem(itemId)

    setChecklist((prev) => {
      if (!prev) return prev
      const updatedItems = prev.items.map((item) =>
        item.id === itemId
          ? { ...item, is_completed: result.is_completed, completed_at: result.completed_at }
          : item
      )
      const completedCount = updatedItems.filter((i) => i.is_completed).length
      return { ...prev, items: updatedItems, completed_count: completedCount }
    })
  }

  return (
    <>
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-pulse mb-3">
              <div className="w-12 h-12 mx-auto border-3 border-black rounded-full flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
            </div>
            <p className="text-gray-500 text-sm">Loading checklist...</p>
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="card mb-4" style={{ borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color)' }}>
          <p style={{ color: 'var(--accent-color-dark)' }} className="text-sm">{error}</p>
          <button
            onClick={loadChecklist}
            className="btn-primary mt-2 text-xs px-3 py-1"
          >
            <span className="relative z-10">Retry</span>
          </button>
        </div>
      )}

      {!loading && !error && checklist && (
        <div className="animate-fadeIn">
          <ChecklistView
            items={checklist.items}
            completedCount={checklist.completed_count}
            totalCount={checklist.total_count}
            currentStreak={currentStreak}
            onToggle={handleToggle}
          />
        </div>
      )}
    </>
  )
}
