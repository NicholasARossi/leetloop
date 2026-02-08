'use client'

import { clsx } from 'clsx'
import type { LanguageAttemptGrade } from '@/lib/api'

interface GradeDisplayProps {
  grade: LanguageAttemptGrade
}

export function GradeDisplay({ grade }: GradeDisplayProps) {
  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'pass':
        return <span className="tag bg-coral-light text-coral border-coral">PASS</span>
      case 'borderline':
        return <span className="tag bg-gray-100 text-gray-700 border-gray-300">BORDERLINE</span>
      case 'fail':
        return <span className="tag bg-gray-200 text-black border-gray-400">FAIL</span>
      default:
        return null
    }
  }

  return (
    <div className="space-y-4">
      {/* Score */}
      <div className="card text-center py-6">
        <div className="mb-2">
          <span className={clsx('stat-value text-5xl', getScoreColor(grade.score))}>
            {grade.score.toFixed(1)}
          </span>
          <span className="text-xl text-gray-400">/10</span>
        </div>
        {getVerdictBadge(grade.verdict)}
      </div>

      {/* Feedback */}
      <div className="card">
        <h3 className="font-semibold text-black mb-3">Feedback</h3>
        <p className="text-sm text-gray-700 leading-relaxed">
          {grade.feedback}
        </p>
      </div>

      {/* Corrections */}
      {grade.corrections && (
        <div className="card border-l-4 border-l-coral">
          <h3 className="font-semibold text-black mb-3">Corrections</h3>
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
            {grade.corrections}
          </p>
        </div>
      )}

      {/* Missed Concepts */}
      {grade.missed_concepts.length > 0 && (
        <div className="card border-l-4 border-l-gray-400">
          <h3 className="font-semibold text-black mb-3">Missed Concepts</h3>
          <div className="flex flex-wrap gap-1">
            {grade.missed_concepts.map((concept, i) => (
              <span key={i} className="tag text-xs bg-gray-100 text-black border-gray-300">
                {concept}
              </span>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            These will appear in spaced repetition.
          </p>
        </div>
      )}
    </div>
  )
}
