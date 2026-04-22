'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type LifeOpsStatsResponse } from '@/lib/api'
import { StatsView } from '@/components/life-ops'

export default function LifeOpsStatsPage() {
  const { userId } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<LifeOpsStatsResponse | null>(null)

  const loadStats = useCallback(async () => {
    if (!userId) return
    setLoading(true)
    setError(null)

    try {
      const data = await leetloopApi.getLifeOpsStats(userId)
      setStats(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to load stats.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">Loading stats...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card mb-4" style={{ borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color)' }}>
        <p style={{ color: 'var(--accent-color-dark)' }} className="text-sm">{error}</p>
        <button onClick={loadStats} className="btn-primary mt-2 text-xs px-3 py-1">
          <span className="relative z-10">Retry</span>
        </button>
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="animate-fadeIn">
      <StatsView stats={stats} />
    </div>
  )
}
