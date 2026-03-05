'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type WinRateStats, type DailyFeedResponse, type SystemDesignDashboardSummary, type SystemDesignReviewItem, type ProgressTrend, type UserStats } from '@/lib/api'
import { WinRateCard } from '@/components/winrate/WinRateCard'
import { FeedSection } from '@/components/feed/FeedSection'
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

  const loadDashboard = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      const [onboardingStatus, winRateData, feedData, sdData, progressData] = await Promise.all([
        leetloopApi.getOnboardingStatus(userId).catch(() => null),
        leetloopApi.getWinRateStats(userId).catch(() => null),
        leetloopApi.getDailyFeed(userId).catch(() => null),
        leetloopApi.getSystemDesignDashboard(userId).catch(() => null),
        leetloopApi.getProgress(userId, 91).catch(() => null),
      ])

      if (onboardingStatus && !onboardingStatus.onboarding_complete) {
        router.push('/onboarding')
        return
      }

      setWinRateStats(winRateData)
      setFeed(feedData)
      setSystemDesignData(sdData)
      if (progressData) {
        setTrends(progressData.trends)
        setUserStats(progressData.stats)
      }
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
          {feed ? (
            <FeedSection feed={feed} />
          ) : (
            <div className="card text-center py-8">
              <p className="text-gray-500 text-sm">
                No feed data available. The backend may still be generating your daily problems.
              </p>
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
