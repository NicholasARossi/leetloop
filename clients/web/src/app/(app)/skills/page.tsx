'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type SkillScore } from '@/lib/api'
import { SkillRadar } from '@/components/charts/SkillRadar'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'

export default function SkillsPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [skills, setSkills] = useState<SkillScore[]>([])

  useEffect(() => {
    async function loadSkills() {
      if (!userId) return

      setLoading(true)
      try {
        const data = await leetloopApi.getSkillScores(userId)
        setSkills(data)
      } catch (err) {
        console.error('Failed to load skills:', err)
      } finally {
        setLoading(false)
      }
    }

    loadSkills()
  }, [userId])

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600 dark:text-green-400'
    if (score >= 40) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getProgressColor = (score: number) => {
    if (score >= 70) return 'bg-green-500'
    if (score >= 40) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-slate-500">Loading skills...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
        Skill Breakdown
      </h1>

      {/* Radar Chart */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Skill Distribution
        </h2>
        <SkillRadar skills={skills} className="max-w-2xl mx-auto" />
      </div>

      {/* Skill List */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            All Skills
          </h2>
        </div>

        {skills.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-slate-500">
              No skill data yet. Start solving problems to build your skill profile!
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {skills
              .sort((a, b) => a.score - b.score) // Weakest first
              .map((skill) => (
                <div
                  key={skill.tag}
                  className="p-4 hover:bg-slate-50 dark:hover:bg-slate-700/30"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="font-medium text-slate-900 dark:text-white">
                        {skill.tag.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </span>
                      <span className="text-sm text-slate-500 ml-2">
                        {skill.total_attempts} attempts
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-slate-500">
                        {Math.round(skill.success_rate * 100)}% success
                      </span>
                      <span className={clsx('font-semibold', getScoreColor(skill.score))}>
                        {Math.round(skill.score)}
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={clsx('h-full rounded-full transition-all', getProgressColor(skill.score))}
                      style={{ width: `${skill.score}%` }}
                    />
                  </div>

                  {skill.last_practiced && (
                    <p className="text-xs text-slate-500 mt-2">
                      Last practiced{' '}
                      {formatDistanceToNow(new Date(skill.last_practiced), { addSuffix: true })}
                    </p>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Weak Areas Summary */}
      {skills.length > 0 && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Focus Areas
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-4">
            These skills need the most attention based on your performance:
          </p>
          <div className="flex flex-wrap gap-2">
            {skills
              .filter((s) => s.score < 50)
              .slice(0, 5)
              .map((skill) => (
                <span
                  key={skill.tag}
                  className="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 px-3 py-1 rounded-full text-sm font-medium"
                >
                  {skill.tag.replace(/-/g, ' ')}
                </span>
              ))}
            {skills.filter((s) => s.score < 50).length === 0 && (
              <span className="text-slate-500">
                Great job! All your skills are above 50. Keep practicing to maintain them!
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
