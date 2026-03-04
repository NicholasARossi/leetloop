'use client'

import { useMemo } from 'react'
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

  // Group exercises into 4 sections
  const groups = useMemo(() => {
    const reviews: DailyExercise[] = []
    const currentChapter: DailyExercise[] = []
    const adaptive: DailyExercise[] = []
    const freeForm: DailyExercise[] = []

    for (const ex of exercises) {
      if (ex.response_format === 'free_form') {
        freeForm.push(ex)
      } else if (ex.is_review) {
        reviews.push(ex)
      } else if (ex.review_topic_reason && !ex.is_review) {
        adaptive.push(ex)
      } else {
        currentChapter.push(ex)
      }
    }

    return { reviews, currentChapter, adaptive, freeForm }
  }, [exercises])

  const reviewCount = groups.reviews.length
  const newCount = groups.currentChapter.length
  const adaptiveCount = groups.adaptive.length

  return (
    <div>
      {/* Session header card */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-lg">Session du jour</h2>
          <span className="font-mono text-sm text-gray-600">
            <span className="text-lg font-bold text-black">{completedCount}</span>
            /{totalCount} exercices
          </span>
        </div>
        <div className="progress-bar mb-3">
          <div
            className="progress-fill transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex items-center gap-4 text-[11px] text-gray-500">
          {newCount > 0 && <span>{newCount} nouveau{newCount > 1 ? 'x' : ''}</span>}
          {reviewCount > 0 && <span>&middot; {reviewCount} révision{reviewCount > 1 ? 's' : ''} ciblée{reviewCount > 1 ? 's' : ''}</span>}
          {adaptiveCount > 0 && <span>&middot; {adaptiveCount} pratique adaptée</span>}
          {averageScore != null && (
            <span className="ml-auto">
              Score moyen : <span className="font-medium text-black">{averageScore.toFixed(1)}</span>
            </span>
          )}
        </div>
      </div>

      {/* All-done summary */}
      {allCompleted && (
        <div className="card text-center mb-6">
          <p className="font-display text-lg mb-3">Session terminée !</p>
          <div className="grid grid-cols-3 bg-white mb-4" style={{ gap: '1px', background: '#e0e0e0', border: '1px solid #e0e0e0' }}>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">{completedCount}</p>
              <p className="stat-label mt-1">Terminés</p>
            </div>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">
                {averageScore != null ? averageScore.toFixed(1) : '—'}
              </p>
              <p className="stat-label mt-1">Score moyen</p>
            </div>
            <div className="bg-white py-3 px-2 text-center">
              <p className="stat-value text-2xl leading-none">{reviewCount}</p>
              <p className="stat-label mt-1">Révisions</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-3">Revenez demain pour de nouveaux exercices.</p>
        </div>
      )}

      {/* Section 1: Révisions ciblées */}
      {groups.reviews.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">Révisions ciblées</h3>
          <div className="space-y-3">
            {groups.reviews.map((exercise) => (
              <DailyExerciseCard
                key={exercise.id}
                exercise={exercise}
                onSubmit={onSubmitExercise}
              />
            ))}
          </div>
        </div>
      )}

      {/* Section 2: Chapitre en cours */}
      {groups.currentChapter.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">Chapitre en cours</h3>
          <div className="space-y-3">
            {groups.currentChapter.map((exercise) => (
              <DailyExerciseCard
                key={exercise.id}
                exercise={exercise}
                onSubmit={onSubmitExercise}
              />
            ))}
          </div>
        </div>
      )}

      {/* Section 3: Pratique adaptée */}
      {groups.adaptive.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">Pratique adaptée</h3>
          <div className="space-y-3">
            {groups.adaptive.map((exercise) => (
              <DailyExerciseCard
                key={exercise.id}
                exercise={exercise}
                onSubmit={onSubmitExercise}
              />
            ))}
          </div>
        </div>
      )}

      {/* Section 4: Expression libre */}
      {groups.freeForm.length > 0 && (
        <div className="mb-6">
          <h3 className="section-id mb-3">Expression libre</h3>
          <div className="space-y-3">
            {groups.freeForm.map((exercise) => (
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
          <p className="text-gray-500 text-sm">Aucun exercice pour aujourd&apos;hui.</p>
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
            {isRegenerating ? 'Régénération...' : 'Régénérer'}
          </span>
        </button>
      </div>
    </div>
  )
}
