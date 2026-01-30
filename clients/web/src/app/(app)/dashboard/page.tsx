'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type MissionResponseV2, type OnboardingStatus } from '@/lib/api'
import {
  MissionProblemCard,
  MissionSkeleton,
  PacingIndicator,
  MainQuestColumn,
  SideQuestColumn,
} from '@/components/mission'
import { format } from 'date-fns'
import { clsx } from 'clsx'

export default function DashboardPage() {
  const router = useRouter()
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mission, setMission] = useState<MissionResponseV2 | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const loadMission = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      // Check onboarding status first
      const onboardingStatus = await leetloopApi.getOnboardingStatus(userId).catch(() => null)

      // If not onboarded, redirect to onboarding
      if (onboardingStatus && !onboardingStatus.onboarding_complete) {
        router.push('/onboarding')
        return
      }

      const data = await leetloopApi.getDailyMissionV2(userId)
      setMission(data)
    } catch (err) {
      console.error('Failed to load mission:', err)
      setError('Failed to load mission. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [userId, router])

  useEffect(() => {
    loadMission()
  }, [loadMission])

  const handleRegenerate = async () => {
    if (!userId || isRegenerating || !mission?.can_regenerate) return

    setIsRegenerating(true)
    try {
      const data = await leetloopApi.regenerateMission(userId) as MissionResponseV2
      setMission(data)
    } catch (err) {
      console.error('Failed to regenerate mission:', err)
    } finally {
      setIsRegenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <MissionSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500 mb-4">
            Make sure the backend API is running at{' '}
            <code className="bg-gray-100 px-2 py-1">
              {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}
            </code>
          </p>
          <button
            onClick={loadMission}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!mission) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center">
          <p className="text-gray-500">No mission data available.</p>
        </div>
      </div>
    )
  }

  const today = new Date()
  const formattedDate = format(today, 'EEEE, MMMM d')

  // Use main_quests/side_quests if available, otherwise derive from problems
  const mainQuests = mission.main_quests || []
  const sideQuests = mission.side_quests || []
  const hasQuestData = mainQuests.length > 0 || sideQuests.length > 0

  // For progress, count from main quests if available
  const mainCompleted = mainQuests.filter(q => q.status === 'completed').length
  const mainTotal = mainQuests.length
  const sideCompleted = sideQuests.filter(q => q.completed).length

  // Fallback to flat problems list for backwards compatibility
  const problemsCompleted = mission.problems?.filter(p => p.completed).length || 0
  const problemsTotal = mission.problems?.length || 0

  const completedCount = hasQuestData ? mainCompleted : problemsCompleted
  const totalCount = hasQuestData ? mainTotal : problemsTotal
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <p className="text-gray-500 text-sm">{formattedDate}</p>
          <h1 className="text-xl font-display mt-1">
            Your Daily Mission
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {/* Pacing indicator */}
          {mission.pacing_status && (
            <PacingIndicator
              status={mission.pacing_status}
              note={mission.pacing_note}
            />
          )}

          {/* Streak badge */}
          {mission.streak > 0 && (
            <div className="stat-badge stat-badge-accent">
              <span className="stat-value">{mission.streak}</span>
              <span className="stat-label">Streak</span>
            </div>
          )}

          {/* Today's progress badge */}
          <div className="stat-badge">
            <span className="stat-value">{completedCount}/{totalCount}</span>
            <span className="stat-label">Today</span>
          </div>
        </div>
      </div>

      {/* Daily Objective Card */}
      <div className="card bracket-corners">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1">
            <p className="text-xs uppercase tracking-wider text-gray-500 mb-2">Today&apos;s Focus</p>
            <h2 className="text-base font-semibold text-black mb-2">
              {mission.daily_objective}
            </h2>
            {mission.balance_explanation && (
              <p className="text-gray-600 text-sm leading-relaxed">
                {mission.balance_explanation}
              </p>
            )}
          </div>

          {/* Regenerate button */}
          <button
            onClick={handleRegenerate}
            disabled={!mission.can_regenerate || isRegenerating}
            className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            title={mission.can_regenerate ? 'Regenerate mission' : 'Regeneration limit reached'}
          >
            <svg
              className={clsx('w-4 h-4 inline mr-1', isRegenerating && 'animate-spin')}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Regenerate
          </button>
        </div>

        {/* Progress bar */}
        <div className="pt-4 border-t-2 border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Today&apos;s Progress</span>
            <span className="text-sm font-medium text-black">
              {completedCount} of {totalCount} main quests
              {sideCompleted > 0 && ` + ${sideCompleted} side`}
            </span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Two Column Layout: Main Quests + Side Quests */}
      {hasQuestData ? (
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6">
          {/* Main Quests Column */}
          <MainQuestColumn quests={mainQuests} />

          {/* Side Quests Column */}
          <SideQuestColumn
            quests={sideQuests}
            streak={mission.streak}
          />
        </div>
      ) : (
        /* Fallback: Flat problems list for backwards compatibility */
        mission.problems && mission.problems.length > 0 && (
          <div className="card">
            <h3 className="section-title mb-4">
              Problems for Today
            </h3>
            <div className="space-y-2">
              {mission.problems.map((problem, index) => (
                <MissionProblemCard
                  key={problem.problem_id}
                  problem={problem}
                  index={index}
                />
              ))}
            </div>
          </div>
        )
      )}

      {/* Pacing Note */}
      {mission.pacing_note && (
        <div className="card-sm bg-gray-50">
          <p className="text-sm text-gray-600">
            <strong>Pacing:</strong> {mission.pacing_note}
          </p>
        </div>
      )}

      {/* AI Transparency */}
      <div className="text-center text-xs text-gray-400 pt-4">
        <p>
          Mission generated by Gemini AI based on your goals, path progress, and skill gaps.
        </p>
      </div>
    </div>
  )
}
