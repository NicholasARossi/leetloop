'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type WinRateStats, type DailyFeedResponse, type SystemDesignDashboardSummary, type SystemDesignReviewItem, type ProgressTrend, type UserStats } from '@/lib/api'
import { WinRateCard } from '@/components/winrate/WinRateCard'
import { FeedSection } from '@/components/feed/FeedSection'
import { FocusNotesCard } from '@/components/feed/FocusNotesCard'
import { MissionSkeleton } from '@/components/mission'
import { SystemDesignDashboardCard } from '@/components/system-design/SystemDesignDashboardCard'
import { SideQuestColumn } from '@/components/mission/SideQuestColumn'
import { format } from 'date-fns'

export default function DashboardPage() {
  const router = useRouter()
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [winRateStats, setWinRateStats] = useState<WinRateStats | null>(null)
  const [feed, setFeed] = useState<DailyFeedResponse | null>(null)
  const [systemDesignData, setSystemDesignData] = useState<SystemDesignDashboardSummary | null>(null)
  const [trends, setTrends] = useState<ProgressTrend[]>([])
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [focusNotes, setFocusNotes] = useState<string | null>(null)

  const [feedLoading, setFeedLoading] = useState(false)

  const loadFeed = useCallback(async (uid: string) => {
    setFeedLoading(true)
    try {
      const feedData = await leetloopApi.getDailyFeed(uid)
      setFeed(feedData)
    } catch {
      // Feed generation may still be in progress
    } finally {
      setFeedLoading(false)
    }
  }, [])

  const loadDashboard = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      // Load onboarding first (fast) to avoid wasted work if redirect needed
      const onboardingStatus = await leetloopApi.getOnboardingStatus(userId).catch(() => null)

      if (onboardingStatus && !onboardingStatus.onboarding_complete) {
        router.push('/onboarding')
        return
      }

      // Load remaining data in parallel (feed has longer timeout)
      const [winRateData, feedData, sdData, progressData, focusNotesData] = await Promise.all([
        leetloopApi.getWinRateStats(userId).catch(() => null),
        leetloopApi.getDailyFeed(userId).catch(() => null),
        leetloopApi.getSystemDesignDashboard(userId).catch(() => null),
        leetloopApi.getProgress(userId, 91).catch(() => null),
        leetloopApi.getFocusNotes(userId).catch(() => null),
      ])

      setWinRateStats(winRateData)
      setFeed(feedData)
      setSystemDesignData(sdData)
      if (progressData) {
        setTrends(progressData.trends)
        setUserStats(progressData.stats)
      }
      setFocusNotes(focusNotesData?.focus_notes ?? null)
    } catch (err) {
      console.error('Failed to load dashboard:', err)
      setError('Failed to load dashboard. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [userId, router])

  const loadedUserRef = useRef<string | null>(null)

  useEffect(() => {
    if (!userId || loadedUserRef.current === userId) return
    loadedUserRef.current = userId
    loadDashboard()
  }, [loadDashboard, userId])

  const handleStartSystemDesignSession = (trackId: string, topic: string) => {
    router.push(`/system-design/session/new?track=${trackId}&topic=${encodeURIComponent(topic)}`)
  }

  const handleStartSystemDesignReview = (review: SystemDesignReviewItem) => {
    router.push(`/system-design/session/new?track=${review.track_id}&topic=${encodeURIComponent(review.topic)}&type=review`)
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <MissionSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="card text-center">
          <p className="text-coral mb-4">{error}</p>
          <p className="text-sm text-gray-500 mb-4">
            Make sure the backend API is running at{' '}
            <code className="bg-gray-100 px-2 py-1">
              {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}
            </code>
          </p>
          <button onClick={loadDashboard} className="btn-primary">
            Try Again
          </button>
        </div>
      </div>
    )
  }

  const today = new Date()
  const formattedDate = format(today, 'EEEE, MMMM d')

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <p className="text-gray-500 text-sm">{formattedDate}</p>
        <h1 className="text-xl font-display mt-1">Dashboard</h1>
      </div>

      {/* Win Rate Card at top */}
      {winRateStats && winRateStats.targets && (
        <WinRateCard stats={winRateStats} />
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Feed */}
        <div className="space-y-6">
          <FocusNotesCard
            focusNotes={focusNotes}
            onSave={async (notes) => {
              if (!userId) return
              const resp = await leetloopApi.updateFocusNotes(userId, notes)
              setFocusNotes(resp.focus_notes)
            }}
          />
          {feed ? (
            <FeedSection feed={feed} />
          ) : (
            <div className="card text-center py-8">
              {feedLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
                  <p className="text-gray-500 text-sm">Loading feed...</p>
                </div>
              ) : (
                <>
                  <p className="text-gray-500 text-sm mb-3">
                    Feed is still generating. This can take a moment on first load.
                  </p>
                  <button
                    onClick={() => userId && loadFeed(userId)}
                    className="text-sm text-accent hover:underline"
                  >
                    Retry
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Stats + System Design */}
        <div className="space-y-6">
          <SideQuestColumn
            quests={[]}
            streak={userStats?.streak_days ?? 0}
            trends={trends}
            stats={userStats}
          />

          {systemDesignData && (
            <SystemDesignDashboardCard
              data={systemDesignData}
              onStartSession={handleStartSystemDesignSession}
              onStartReview={handleStartSystemDesignReview}
            />
          )}
        </div>
      </div>

      {/* AI Transparency */}
      <div className="text-center text-xs text-gray-400 pt-4">
        <p>
          Feed generated with a mix of practice (familiar) and metric (unseen) problems.
        </p>
      </div>
    </div>
  )
}
