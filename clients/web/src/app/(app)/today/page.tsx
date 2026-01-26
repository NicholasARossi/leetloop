'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type TodaysFocus } from '@/lib/api'
import { DailyGoalRing } from '@/components/today/DailyGoalRing'
import { StreakBadge } from '@/components/today/StreakBadge'
import { PriorityLane } from '@/components/today/PriorityLane'
import { LLMInsightCard } from '@/components/today/LLMInsightCard'

export default function TodayPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<TodaysFocus | null>(null)

  useEffect(() => {
    async function loadData() {
      if (!userId) return

      setLoading(true)
      setError(null)

      try {
        const focusData = await leetloopApi.getTodaysFocus(userId)
        setData(focusData)
      } catch (err) {
        console.error('Failed to load today\'s focus:', err)
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
        <div className="animate-pulse text-slate-500">Loading today&apos;s focus...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-500 mb-4">{error}</p>
        <p className="text-sm text-slate-500">
          Make sure the backend API is running.
        </p>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const totalProblems = data.reviews_due.length + data.path_problems.length + data.skill_builders.length

  return (
    <div className="space-y-6">
      {/* Header with Goal Ring and Streak */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <DailyGoalRing
              completed={data.completed_today}
              goal={data.daily_goal}
              size={100}
            />
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Today&apos;s Focus
              </h1>
              <p className="text-slate-500 mt-1">
                {totalProblems > 0
                  ? `${totalProblems} problem${totalProblems !== 1 ? 's' : ''} to work on`
                  : 'You\'re all caught up!'}
              </p>
            </div>
          </div>
          <StreakBadge streak={data.streak} />
        </div>
      </div>

      {/* LLM Insight */}
      <LLMInsightCard insight={data.llm_insight} />

      {/* Three Priority Lanes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <PriorityLane
          title="Reviews Due"
          problems={data.reviews_due}
          variant="reviews"
          emptyMessage="No reviews due today"
        />
        <PriorityLane
          title="Path Progress"
          problems={data.path_problems}
          variant="path"
          emptyMessage="Select a learning path to get started"
        />
        <PriorityLane
          title="Skill Builders"
          problems={data.skill_builders}
          variant="skills"
          emptyMessage="Complete more problems to get skill recommendations"
        />
      </div>

      {/* Quick Links */}
      <div className="flex flex-wrap gap-4 justify-center">
        <Link
          href="/path"
          className="btn-primary px-6 py-2"
        >
          View Path Progress
        </Link>
        <Link
          href="/mastery"
          className="px-6 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
        >
          Check Mastery
        </Link>
        <Link
          href="/reviews"
          className="px-6 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
        >
          All Reviews
        </Link>
      </div>
    </div>
  )
}
