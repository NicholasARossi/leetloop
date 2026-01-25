'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type UserStats, type SkillScore, type ProgressTrend, type Submission, type RecommendedProblem } from '@/lib/api'
import { StatsCard } from '@/components/ui/StatsCard'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { SkillRadar } from '@/components/charts/SkillRadar'
import { ProgressLine } from '@/components/charts/ProgressLine'
import { formatDistanceToNow } from 'date-fns'

export default function DashboardPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<UserStats | null>(null)
  const [skills, setSkills] = useState<SkillScore[]>([])
  const [trends, setTrends] = useState<ProgressTrend[]>([])
  const [recentSubmissions, setRecentSubmissions] = useState<Submission[]>([])
  const [recommendations, setRecommendations] = useState<RecommendedProblem[]>([])

  useEffect(() => {
    async function loadData() {
      if (!userId) return

      setLoading(true)
      setError(null)

      try {
        const [progressData, recsData] = await Promise.all([
          leetloopApi.getProgress(userId),
          leetloopApi.getRecommendations(userId, 3),
        ])

        setStats(progressData.stats)
        setSkills(progressData.skill_scores)
        setTrends(progressData.trends)
        setRecentSubmissions(progressData.recent_submissions)
        setRecommendations(recsData.recommendations)
      } catch (err) {
        console.error('Failed to load dashboard data:', err)
        setError('Failed to load data. Make sure the backend is running.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [userId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-slate-500">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-500 mb-4">{error}</p>
        <p className="text-sm text-slate-500">
          Make sure the backend API is running at{' '}
          <code className="bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded">
            {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}
          </code>
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Submissions"
          value={stats?.total_submissions || 0}
        />
        <StatsCard
          title="Problems Solved"
          value={stats?.problems_solved || 0}
          subtitle={`of ${stats?.problems_attempted || 0} attempted`}
        />
        <StatsCard
          title="Success Rate"
          value={`${Math.round((stats?.success_rate || 0) * 100)}%`}
          trend={stats?.success_rate && stats.success_rate >= 0.5 ? 'up' : 'down'}
        />
        <StatsCard
          title="Reviews Due"
          value={stats?.reviews_due || 0}
          subtitle={stats?.reviews_due ? 'Problems need review' : 'All caught up!'}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Skill Distribution
          </h2>
          <SkillRadar skills={skills} />
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Progress Over Time
          </h2>
          <ProgressLine trends={trends} />
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Submissions */}
        <div className="card p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Recent Submissions
            </h2>
            <Link
              href="/submissions"
              className="text-sm text-brand-600 hover:text-brand-700"
            >
              View all
            </Link>
          </div>

          {recentSubmissions.length === 0 ? (
            <p className="text-slate-500 text-center py-8">
              No submissions yet. Start solving problems on LeetCode!
            </p>
          ) : (
            <div className="space-y-3">
              {recentSubmissions.slice(0, 5).map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-700 last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 dark:text-white truncate">
                      {sub.problem_title}
                    </p>
                    <p className="text-sm text-slate-500">
                      {formatDistanceToNow(new Date(sub.submitted_at), { addSuffix: true })}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {sub.difficulty && <DifficultyBadge difficulty={sub.difficulty} />}
                    <StatusBadge status={sub.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div className="card p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Recommended Problems
            </h2>
            <Link
              href="/reviews"
              className="text-sm text-brand-600 hover:text-brand-700"
            >
              View reviews
            </Link>
          </div>

          {recommendations.length === 0 ? (
            <p className="text-slate-500 text-center py-8">
              No recommendations yet. Keep practicing!
            </p>
          ) : (
            <div className="space-y-3">
              {recommendations.map((rec, idx) => (
                <div
                  key={`${rec.problem_slug}-${idx}`}
                  className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <a
                        href={`https://leetcode.com/problems/${rec.problem_slug}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-slate-900 dark:text-white hover:text-brand-600"
                      >
                        {rec.problem_title || rec.problem_slug}
                      </a>
                      <p className="text-sm text-slate-500 mt-1">{rec.reason}</p>
                    </div>
                    {rec.difficulty && <DifficultyBadge difficulty={rec.difficulty} />}
                  </div>
                  {rec.tags.length > 0 && (
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {rec.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
