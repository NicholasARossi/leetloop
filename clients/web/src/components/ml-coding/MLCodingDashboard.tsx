'use client'

import { useMemo } from 'react'
import { MLCodingExerciseCard } from './MLCodingExerciseCard'
import type { MLCodingDailyExercise } from '@/lib/api'

interface MLCodingDashboardProps {
  exercises: MLCodingDailyExercise[]
  completedCount: number
  totalCount: number
  averageScore: number | null
  onSubmitExercise: (exerciseId: string, code: string) => Promise<void>
  onRegenerate: () => Promise<void>
  isRegenerating: boolean
}

export function MLCodingDashboard({
  exercises,
  completedCount,
  totalCount,
  averageScore,
  onSubmitExercise,
  onRegenerate,
  isRegenerating,
}: MLCodingDashboardProps) {
  const allCompleted = totalCount > 0 && completedCount === totalCount
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  const groups = useMemo(() => {
    const reviews: MLCodingDailyExercise[] = []
    const newProblems: MLCodingDailyExercise[] = []

    for (const ex of exercises) {
      if (ex.is_review) {
        reviews.push(ex)
      } else {
        newProblems.push(ex)
      }
    }

    return { reviews, newProblems }
  }, [exercises])

  return (
    <div>
      {/* Session header */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-lg">ML Coding Drills</h2>
          <span className="font-mono text-sm text-gray-600">
            <span className="text-lg font-bold text-black">{completedCount}</span>
            /{totalCount} problems
          </span>
        </div>
        <div className="progress-bar mb-3">
          <div
            className="progress-fill transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex items-center gap-4 text-[11px] text-gray-500">
          {groups.newProblems.length > 0 && (
            <span>{groups.newProblems.length} new</span>
          )}
          {groups.reviews.length > 0 && (
            <span>&middot; {groups.reviews.length} review{groups.reviews.length !== 1 ? 's' : ''}</span>
          )}
          {averageScore != null && (
            <span className="ml-auto">
              Avg score: <span className="font-medium text-black">{averageScore.toFixed(1)}</span>
            </span>
          )}
        </div>
      </div>

      {/* All-done summary */}
      {allCompleted && (
        <div className="card text-center mb-6">
          <p className="font-display text-lg mb-3">All done for today!</p>
          <div className="grid grid-cols-2 bg-white mb-4" style={{ gap: '1px', background: '#e0e0e0', border: '1px solid #e0e0e0' }}>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">{completedCount}</p>
              <p className="stat-label mt-1">Completed</p>
            </div>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">
                {averageScore != null ? averageScore.toFixed(1) : '\u2014'}
              </p>
              <p className="stat-label mt-1">Avg Score</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-3">Come back tomorrow for new problems.</p>
        </div>
      )}

      {/* Review problems */}
      {groups.reviews.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">Review Problems</h3>
          <div className="space-y-4">
            {groups.reviews.map((exercise) => (
              <MLCodingExerciseCard
                key={exercise.id}
                exercise={exercise}
                onSubmit={onSubmitExercise}
              />
            ))}
          </div>
        </div>
      )}

      {/* New problems */}
      {groups.newProblems.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">New Problems</h3>
          <div className="space-y-4">
            {groups.newProblems.map((exercise) => (
              <MLCodingExerciseCard
                key={exercise.id}
                exercise={exercise}
                onSubmit={onSubmitExercise}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {exercises.length === 0 && !allCompleted && (
        <div className="card text-center">
          <p className="text-gray-500 text-sm">No exercises for today.</p>
        </div>
      )}

      {/* Regenerate button */}
      <div className="text-center mt-6">
        <button
          onClick={onRegenerate}
          disabled={isRegenerating}
          className="btn-primary px-6 py-2 text-sm font-semibold"
        >
          <span className="relative z-10">
            {isRegenerating ? 'Regenerating...' : 'Regenerate'}
          </span>
        </button>
      </div>
    </div>
  )
}
