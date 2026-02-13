'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import type { LanguageAttemptGrade } from '@/lib/api'
import { leetloopApi } from '@/lib/api'

interface DashboardExerciseCardProps {
  trackId: string
  topic: string
  exerciseType?: string
  userId: string
  onGraded?: (grade: LanguageAttemptGrade) => void
}

type CardState = 'idle' | 'generating' | 'answering' | 'submitting' | 'graded'

export function DashboardExerciseCard({
  trackId,
  topic,
  exerciseType = 'vocabulary',
  userId,
  onGraded,
}: DashboardExerciseCardProps) {
  const [state, setState] = useState<CardState>('idle')
  const [questionText, setQuestionText] = useState('')
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [answerText, setAnswerText] = useState('')
  const [grade, setGrade] = useState<LanguageAttemptGrade | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async () => {
    setState('generating')
    setError(null)

    try {
      const attempt = await leetloopApi.createLanguageAttempt(userId, {
        track_id: trackId,
        topic,
        exercise_type: exerciseType,
      })
      setQuestionText(attempt.question_text)
      setAttemptId(attempt.id)
      setState('answering')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate exercise')
      setState('idle')
    }
  }

  const handleSubmit = async () => {
    if (!attemptId || !answerText.trim()) return

    setState('submitting')
    setError(null)

    try {
      const result = await leetloopApi.submitLanguageAttempt(attemptId, answerText)
      setGrade(result)
      setState('graded')
      onGraded?.(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer')
      setState('answering')
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  if (state === 'idle') {
    return (
      <button
        onClick={handleStart}
        className="w-full text-left p-3 bg-white border-2 border-gray-200 hover:border-coral transition-all"
      >
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Quick exercise: <strong>{topic}</strong></span>
          <span className="bg-coral text-white px-3 py-1 text-xs font-semibold">Start</span>
        </div>
      </button>
    )
  }

  if (state === 'generating') {
    return (
      <div className="p-3 border-2 border-gray-200 bg-gray-50">
        <span className="text-sm text-gray-500 animate-pulse">Generating exercise...</span>
      </div>
    )
  }

  return (
    <div className="border-2 border-l-4 border-l-coral border-gray-200 bg-white">
      {/* Question */}
      <div className="p-3">
        <p className="text-sm text-gray-800 whitespace-pre-wrap">{questionText}</p>
      </div>

      {/* Answer input */}
      {(state === 'answering' || state === 'submitting') && (
        <div className="px-3 pb-3">
          <textarea
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            placeholder="Write your answer..."
            className="w-full h-20 p-2 border border-gray-300 rounded text-sm resize-none focus:border-coral focus:ring-1 focus:ring-coral outline-none"
            disabled={state === 'submitting'}
          />
          <div className="flex items-center justify-between mt-2">
            {error && <span className="text-[11px] text-coral">{error}</span>}
            <button
              onClick={handleSubmit}
              disabled={state === 'submitting' || !answerText.trim()}
              className={clsx(
                'ml-auto px-3 py-1.5 text-xs font-semibold text-white transition-colors',
                state === 'submitting' ? 'bg-gray-400 cursor-not-allowed' : 'bg-black hover:bg-gray-800'
              )}
            >
              {state === 'submitting' ? 'Grading...' : 'Submit'}
            </button>
          </div>
        </div>
      )}

      {/* Grade */}
      {state === 'graded' && grade && (
        <div className="px-3 pb-3 border-t border-gray-100">
          <div className="flex items-start gap-3 pt-2">
            <span className={clsx('text-lg font-bold', getScoreColor(grade.score))}>
              {grade.score.toFixed(1)}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-700">{grade.feedback}</p>
              {grade.corrections && (
                <p className="text-xs text-coral mt-1">
                  Correction: {grade.corrections}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
