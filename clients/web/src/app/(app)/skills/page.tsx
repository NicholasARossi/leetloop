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
    if (score >= 70) return 'text-black'
    if (score >= 40) return 'text-gray-600'
    return 'text-gray-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading skills...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="heading-accent text-xl">Skill Breakdown</h1>

      {/* Radar Chart */}
      <div className="card">
        <h2 className="section-title">Skill Distribution</h2>
        <SkillRadar skills={skills} className="max-w-2xl mx-auto" />
      </div>

      {/* Skill List */}
      <div className="card p-0 overflow-hidden">
        <div className="p-4 border-b-2 border-black bg-gray-100">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700">
            All Skills
          </h2>
        </div>

        {skills.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-500">
              No skill data yet. Start solving problems to build your skill profile!
            </p>
          </div>
        ) : (
          <div>
            {skills
              .sort((a, b) => a.score - b.score) // Weakest first
              .map((skill) => (
                <div
                  key={skill.tag}
                  className="p-4 border-b border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="font-medium text-black">
                        {skill.tag.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </span>
                      <span className="text-sm text-gray-500 ml-2">
                        {skill.total_attempts} attempts
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-500">
                        {Math.round(skill.success_rate * 100)}% success
                      </span>
                      <span className={clsx('font-semibold', getScoreColor(skill.score))}>
                        {Math.round(skill.score)}
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="progress-bar">
                    <div
                      className="progress-fill transition-all"
                      style={{ width: `${skill.score}%` }}
                    />
                  </div>

                  {skill.last_practiced && (
                    <p className="text-xs text-gray-500 mt-2">
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
        <div className="card">
          <h2 className="section-title">Focus Areas</h2>
          <p className="text-gray-600 mb-4">
            These skills need the most attention based on your performance:
          </p>
          <div className="flex flex-wrap gap-2">
            {skills
              .filter((s) => s.score < 50)
              .slice(0, 5)
              .map((skill) => (
                <span
                  key={skill.tag}
                  className="tag"
                >
                  {skill.tag.replace(/-/g, ' ')}
                </span>
              ))}
            {skills.filter((s) => s.score < 50).length === 0 && (
              <span className="text-gray-500">
                Great job! All your skills are above 50. Keep practicing to maintain them!
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
