'use client'

import { useMemo } from 'react'
import { DailyExerciseCard } from './DailyExerciseCard'
import type { LanguageOralDashboard } from '@/lib/api'
import { OralPromptCard, OralGradingCard, StreakBadge } from '../language/oral'

interface DailyExercise {
  id: string
  topic: string
  exercise_type: string
  question_text: string
  focus_area?: string
  key_concepts?: string[]
  grammar_targets?: string[]
  vocab_targets?: string[]
  is_review: boolean
  review_topic_reason?: string
  status: 'pending' | 'completed' | 'skipped'
  response_format?: 'long_text' | 'free_form'
  word_target?: number
  response_text?: string
  score?: number
  verdict?: string
  feedback?: string
  corrections?: string
  missed_concepts?: string[]
  written_grading?: import('@/lib/api').WrittenGrading
}

interface ExerciseDashboardProps {
  exercises: DailyExercise[]
  completedCount: number
  totalCount: number
  averageScore: number | null
  onSubmitExercise: (exerciseId: string, responseText: string) => Promise<void>
  onRegenerate: () => Promise<void>
  isRegenerating: boolean
  oralDashboard?: LanguageOralDashboard | null
  userId?: string
  onOralSessionStarted?: () => void
}

export function ExerciseDashboard({
  exercises,
  completedCount,
  totalCount,
  averageScore,
  onSubmitExercise,
  onRegenerate,
  isRegenerating,
  oralDashboard,
  userId,
  onOralSessionStarted,
}: ExerciseDashboardProps) {
  const allCompleted = totalCount > 0 && completedCount === totalCount
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  const firstPendingId = useMemo(() => {
    const first = exercises.find(ex => ex.status === 'pending')
    return first?.id ?? null
  }, [exercises])

  const oralPromptCount = oralDashboard?.todays_prompts?.length ?? 0
  const chapter = oralDashboard?.chapter
  const streak = oralDashboard?.streak
  const chapterProgressPercent = chapter
    ? Math.min(chapter.completion_percentage, 100)
    : 0

  const hasOral = oralDashboard && (
    oralDashboard.todays_prompts.length > 0 ||
    oralDashboard.pending_sessions.length > 0 ||
    oralDashboard.recent_sessions.length > 0
  )

  return (
    <div>
      {/* Session header card — full width */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="font-display text-lg">Session du jour</h2>
            {streak && streak.current_streak > 0 && (
              <StreakBadge
                currentStreak={streak.current_streak}
                longestStreak={streak.longest_streak}
              />
            )}
          </div>
          <span className="font-mono text-sm text-gray-600">
            <span className="text-lg font-bold text-black">{completedCount}</span>
            /{totalCount} exercices
          </span>
        </div>
        <div className="progress-bar mb-2">
          <div
            className="progress-fill transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {chapter && (
          <div className="mb-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono text-gray-400">
                Ch. {chapter.order}/{chapter.total_chapters} — {chapter.name}
              </span>
              <span className="text-[10px] font-mono text-gray-500">
                {chapter.completion_percentage.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full transition-all"
                style={{ width: `${chapterProgressPercent}%`, backgroundColor: 'var(--accent-color)' }}
              />
            </div>
          </div>
        )}
        <div className="flex items-center gap-4 text-[11px] text-gray-500">
          <span>{totalCount} écrit{totalCount > 1 ? 's' : ''}</span>
          {oralPromptCount > 0 && <span>&middot; {oralPromptCount} oral{oralPromptCount > 1 ? 'aux' : ''}</span>}
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
              <p className="stat-value text-2xl leading-none">
                {exercises.filter(e => e.is_review).length}
              </p>
              <p className="stat-label mt-1">Révisions</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mb-3">Revenez demain pour de nouveaux exercices.</p>
        </div>
      )}

      {/* Two-column layout: Written (60%) | Oral (40%) */}
      <div className={hasOral ? 'grid grid-cols-1 md:grid-cols-[3fr_2fr] gap-6' : ''}>
        {/* Left column: Written exercises — flat list */}
        <div>
          <h3 className="section-id mb-3">Écrit</h3>
          {exercises.length > 0 ? (
            <div className="space-y-3">
              {exercises.map((exercise) => (
                <DailyExerciseCard
                  key={exercise.id}
                  exercise={exercise}
                  onSubmit={onSubmitExercise}
                  autoExpand={exercise.id === firstPendingId}
                />
              ))}
            </div>
          ) : (
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

        {/* Right column: Oral */}
        {hasOral && userId && (
          <div>
            <h3 className="section-id mb-3">Oral</h3>

            {/* Oral prompts */}
            {oralDashboard.todays_prompts.length > 0 && (
              <div className="space-y-3 mb-6">
                {oralDashboard.todays_prompts.map(prompt => (
                  <OralPromptCard
                    key={prompt.id}
                    prompt={prompt}
                    userId={userId}
                    onSessionStarted={onOralSessionStarted ?? (() => {})}
                  />
                ))}
              </div>
            )}

            {/* Pending grading */}
            {oralDashboard.pending_sessions.length > 0 && (
              <div className="mb-6">
                <p className="text-[10px] uppercase tracking-wide text-gray-400 mb-2">En cours d&apos;évaluation</p>
                <div className="space-y-3">
                  {oralDashboard.pending_sessions.map(session => (
                    <OralGradingCard key={session.id} session={session} />
                  ))}
                </div>
              </div>
            )}

            {/* Recent results */}
            {oralDashboard.recent_sessions.length > 0 && (
              <div className="mb-6">
                <p className="text-[10px] uppercase tracking-wide text-gray-400 mb-2">Résultats récents</p>
                <div className="space-y-3">
                  {oralDashboard.recent_sessions.map(session => (
                    <OralGradingCard key={session.id} session={session} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
