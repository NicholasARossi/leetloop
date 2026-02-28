'use client'

import { DailyExerciseCard } from './DailyExerciseCard'

interface DailyExercise {
  id: string
  topic: string
  exercise_type: string
  question_text: string
  focus_area?: string
  key_concepts?: string[]
  is_review: boolean
  review_topic_reason?: string
  status: 'pending' | 'completed' | 'skipped'
  response_format?: 'single_line' | 'short_text' | 'long_text' | 'free_form'
  word_target?: number
  response_text?: string
  score?: number
  verdict?: string
  feedback?: string
  corrections?: string
  missed_concepts?: string[]
}

interface ExerciseDashboardProps {
  exercises: DailyExercise[]
  completedCount: number
  totalCount: number
  averageScore: number | null
  onSubmitExercise: (exerciseId: string, responseText: string) => Promise<void>
  onRegenerate: () => Promise<void>
  isRegenerating: boolean
}

export function ExerciseDashboard({
  exercises,
  completedCount,
  totalCount,
  averageScore,
  onSubmitExercise,
  onRegenerate,
  isRegenerating,
}: ExerciseDashboardProps) {
  const allCompleted = totalCount > 0 && completedCount === totalCount
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  const reviewExercises = exercises.filter((e) => e.is_review)
  const newExercises = exercises.filter((e) => !e.is_review)
  const reviewsCompleted = reviewExercises.filter((e) => e.status === 'completed').length

  return (
    <div>
      {/* Progress header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="section-title mb-0 pb-0 border-b-0">Today&apos;s Exercises</h2>
          <span className="font-mono text-sm text-gray-600">
            <span className="text-lg font-bold text-black">{completedCount}</span>
            /{totalCount}
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* All-done summary */}
      {allCompleted && (
        <div className="card text-center mb-6">
          <p className="font-display text-lg mb-3">Today&apos;s exercises complete!</p>
          <div className="grid grid-cols-3 gap-px bg-black border-2 border-black mb-4">
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">{completedCount}</p>
              <p className="stat-label mt-1">Done</p>
            </div>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">
                {averageScore != null ? averageScore.toFixed(1) : '—'}
              </p>
              <p className="stat-label mt-1">Avg Score</p>
            </div>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">{reviewsCompleted}</p>
              <p className="stat-label mt-1">Reviews</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-3">Come back tomorrow for new exercises.</p>
          <button
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="btn-primary px-6 py-2 text-sm font-semibold"
          >
            <span className="relative z-10">
              {isRegenerating ? 'Regenerating...' : 'Regenerate Exercises'}
            </span>
          </button>
        </div>
      )}

      {/* Review exercises section */}
      {reviewExercises.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">Reviews</h3>
          <div className="space-y-3">
            {reviewExercises.map((exercise) => (
              <DailyExerciseCard
                key={exercise.id}
                exercise={exercise}
                onSubmit={onSubmitExercise}
              />
            ))}
          </div>
        </div>
      )}

      {/* New exercises section */}
      {newExercises.length > 0 && (
        <div>
          {reviewExercises.length > 0 && (
            <h3 className="section-id mb-3">Exercises</h3>
          )}
          <div className="space-y-3">
            {newExercises.map((exercise) => (
              <DailyExerciseCard
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
          <p className="text-gray-500 text-sm">No exercises for today yet.</p>
        </div>
      )}
    </div>
  )
}
