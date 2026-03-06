'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type WinRateStats } from '@/lib/api'
import { WinRateCard } from '@/components/winrate/WinRateCard'
import { WinRateTrend } from '@/components/winrate/WinRateTrend'
import { WinRateSetup } from '@/components/winrate/WinRateSetup'

export default function WinRatePage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<WinRateStats | null>(null)
  const [period, setPeriod] = useState<'30d' | 'alltime'>('30d')
  const [showSetup, setShowSetup] = useState(false)
  const loadedRef = useRef<string | null>(null)

  const loadStats = useCallback(async () => {
    if (!userId) return
    setLoading(true)
    try {
      const data = await leetloopApi.getWinRateStats(userId)
      setStats(data)
      if (!data.targets) {
        setShowSetup(true)
      }
    } catch (err) {
      console.error('Failed to load win rate stats:', err)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    if (!userId || loadedRef.current === userId) return
    loadedRef.current = userId
    loadStats()
  }, [loadStats, userId])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card animate-pulse h-48" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-display">Win Rate</h1>
        <button
          onClick={() => setShowSetup(!showSetup)}
          className="text-xs font-mono px-3 py-1.5 border-2 border-black hover:bg-gray-100 transition-colors"
        >
          {showSetup ? 'Hide Settings' : 'Edit Targets'}
        </button>
      </div>

      {/* Setup/Edit form */}
      {showSetup && userId && (
        <div className="card">
          <h3 className="section-title mb-4">Win Rate Targets</h3>
          <WinRateSetup
            userId={userId}
            initialTargets={stats?.targets ? {
              easy_target: stats.targets.easy_target,
              medium_target: stats.targets.medium_target,
              hard_target: stats.targets.hard_target,
              optimality_threshold: stats.targets.optimality_threshold,
            } : undefined}
            onComplete={() => {
              setShowSetup(false)
              loadedRef.current = null
              loadStats()
            }}
          />
        </div>
      )}

      {/* Win Rate Card */}
      {stats && (
        <>
          <WinRateCard
            stats={stats}
            period={period}
            onTogglePeriod={() => setPeriod(p => p === '30d' ? 'alltime' : '30d')}
          />
          <WinRateTrend stats={stats} />
        </>
      )}

      {!stats?.targets && !showSetup && (
        <div className="card text-center py-8">
          <p className="text-gray-500 mb-4">No win rate targets set yet.</p>
          <button
            onClick={() => setShowSetup(true)}
            className="btn-primary"
          >
            Set Targets
          </button>
        </div>
      )}
    </div>
  )
}
