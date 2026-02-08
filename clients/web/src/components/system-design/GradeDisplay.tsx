'use client'

import { clsx } from 'clsx'
import type { SystemDesignGrade } from '@/lib/api'

interface GradeDisplayProps {
  grade: SystemDesignGrade
}

export function GradeDisplay({ grade }: GradeDisplayProps) {
  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  const getScoreLabel = (score: number) => {
    if (score >= 8) return 'Strong Pass'
    if (score >= 7) return 'Likely Pass'
    if (score >= 5) return 'Borderline'
    if (score >= 3) return 'Needs Work'
    return 'Significant Gaps'
  }

  const getHireDecision = () => {
    if (grade.would_hire === true) {
      return (
        <span className="tag tag-accent">
          Would Hire
        </span>
      )
    }
    if (grade.would_hire === false) {
      return (
        <span className="tag bg-coral text-white">
          Would Not Hire
        </span>
      )
    }
    return (
      <span className="tag">
        Inconclusive
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <div className="card text-center py-8">
        <div className="mb-2">
          <span className={clsx('stat-value text-6xl', getScoreColor(grade.overall_score))}>
            {grade.overall_score.toFixed(1)}
          </span>
          <span className="text-2xl text-gray-400">/10</span>
        </div>
        <div className="text-sm font-medium text-gray-600 mb-4">
          {getScoreLabel(grade.overall_score)}
        </div>
        {getHireDecision()}
      </div>

      {/* Overall Feedback */}
      <div className="card">
        <h3 className="font-semibold text-black mb-3">Overall Feedback</h3>
        <p className="text-sm text-gray-700 leading-relaxed">
          {grade.overall_feedback}
        </p>
      </div>

      {/* Strengths & Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Strengths */}
        {grade.strengths.length > 0 && (
          <div className="card border-l-4 border-l-coral">
            <h3 className="font-semibold text-black mb-3">Strengths</h3>
            <ul className="space-y-2">
              {grade.strengths.map((strength, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-coral mt-0.5">+</span>
                  <span className="text-gray-700">{strength}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Gaps */}
        {grade.gaps.length > 0 && (
          <div className="card border-l-4 border-l-black">
            <h3 className="font-semibold text-black mb-3">Gaps</h3>
            <ul className="space-y-2">
              {grade.gaps.map((gap, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-black mt-0.5">-</span>
                  <span className="text-gray-700">{gap}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Topics to Review */}
      {grade.review_topics.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-black mb-3">Topics Added to Review Queue</h3>
          <div className="flex flex-wrap gap-2">
            {grade.review_topics.map((topic, i) => (
              <span key={i} className="tag">
                {topic}
              </span>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">
            These topics will appear in your review queue using spaced repetition.
          </p>
        </div>
      )}
    </div>
  )
}
