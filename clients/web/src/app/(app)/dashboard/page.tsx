'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type MissionResponse } from '@/lib/api'
import {
  DailyObjectiveCard,
  MainQuestColumn,
  SideQuestColumn,
  MissionSkeleton,
} from '@/components/mission'
import { format } from 'date-fns'

export default function DashboardPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mission, setMission] = useState<MissionResponse | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const loadMission = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      const data = await leetloopApi.getDailyMission(userId)
      setMission(data)
    } catch (err) {
      console.error('Failed to load mission:', err)
      setError('Failed to load mission. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadMission()
  }, [loadMission])

  const handleRegenerate = async () => {
    if (!userId || isRegenerating || !mission?.can_regenerate) return

    setIsRegenerating(true)
    try {
      const data = await leetloopApi.regenerateMission(userId)
      setMission(data)
    } catch (err) {
      console.error('Failed to regenerate mission:', err)
    } finally {
      setIsRegenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto">
        <MissionSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="card p-8 text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <p className="text-sm text-slate-500">
            Make sure the backend API is running at{' '}
            <code className="bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded">
              {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}
            </code>
          </p>
          <button
            onClick={loadMission}
            className="mt-4 btn-primary"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!mission) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="card p-8 text-center">
          <p className="text-slate-500">No mission data available.</p>
        </div>
      </div>
    )
  }

  const today = new Date()
  const formattedDate = format(today, 'EEEE, MMMM d')

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header with date and regenerate */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-500 dark:text-slate-400 text-sm">{formattedDate}</p>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white mt-1">
            Your Daily Mission
          </h1>
        </div>

        {/* Streak badge */}
        {mission.streak > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-500/20 rounded-lg">
            <span className="text-2xl">🔥</span>
            <div>
              <p className="text-amber-700 dark:text-amber-400 font-semibold">{mission.streak} day streak</p>
            </div>
          </div>
        )}
      </div>

      {/* Main Objective Card */}
      <DailyObjectiveCard
        objective={mission.objective}
        onRegenerate={handleRegenerate}
        canRegenerate={mission.can_regenerate}
        isRegenerating={isRegenerating}
      />

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Main Quests (3 cols) */}
        <div className="lg:col-span-3">
          <MainQuestColumn quests={mission.main_quests} />
        </div>

        {/* Side Quests (2 cols) */}
        <div className="lg:col-span-2">
          <SideQuestColumn
            quests={mission.side_quests}
            streak={mission.streak}
          />
        </div>
      </div>
    </div>
  )
}
