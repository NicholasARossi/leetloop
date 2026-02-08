'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import type { DashboardQuestion, AttemptGrade } from '@/lib/api'
import { leetloopApi } from '@/lib/api'

interface DashboardQuestionCardProps {
  question: DashboardQuestion
  index: number
  showScenario?: boolean  // Only show scenario for first question
  onGraded?: (questionId: string, grade: AttemptGrade) => void
}

type CardState = 'collapsed' | 'expanded' | 'submitting' | 'graded'

export function DashboardQuestionCard({
  question,
  index,
  showScenario = false,
  onGraded,
}: DashboardQuestionCardProps) {
  const [state, setState] = useState<CardState>(question.completed ? 'graded' : 'collapsed')
  const [answerText, setAnswerText] = useState('')
  const [grade, setGrade] = useState<AttemptGrade | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleExpand = () => {
    if (state === 'collapsed') {
      setState('expanded')
    }
  }

  const handleCollapse = () => {
    if (state === 'expanded' || state === 'graded') {
      setState('collapsed')
    }
  }

  const handleSubmit = async () => {
    if (!answerText.trim()) {
      setError('Please write an answer before submitting')
      return
    }

    // Lower minimum for focused answers (2 concepts = ~30 words minimum)
    if (answerText.trim().split(/\s+/).length < 15) {
      setError('Please provide a bit more detail (at least 15 words)')
      return
    }

    setError(null)
    setState('submitting')

    try {
      const result = await leetloopApi.submitDashboardQuestion(question.id, answerText)
      setGrade(result)
      setState('graded')
      onGraded?.(question.id, result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer')
      setState('expanded')
    }
  }

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'pass':
        return 'bg-coral-light text-black border-coral'
      case 'borderline':
        return 'bg-gray-100 text-gray-700 border-gray-400'
      case 'fail':
        return 'bg-gray-200 text-black border-black'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  return (
    <div
      className={clsx(
        'border-2 border-l-4 transition-all',
        state === 'collapsed' && !question.completed && 'bg-white border-gray-200 border-l-coral hover:border-coral cursor-pointer',
        state === 'collapsed' && question.completed && 'bg-gray-50 border-gray-200 border-l-gray-400',
        state === 'expanded' && 'bg-white border-coral border-l-coral shadow-sm',
        state === 'submitting' && 'bg-white border-gray-300 border-l-gray-400 opacity-75',
        state === 'graded' && grade && 'bg-white border-gray-200 border-l-coral'
      )}
    >
      {/* Header */}
      <div
        onClick={state === 'collapsed' ? handleExpand : undefined}
        className={clsx(
          'p-3',
          state === 'collapsed' && 'cursor-pointer'
        )}
      >
        <div className="flex items-start gap-2">
          <span className={clsx(
            'flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5',
            question.completed || state === 'graded'
              ? 'bg-coral text-white'
              : 'bg-gray-300 text-gray-600'
          )}>
            {question.completed || state === 'graded' ? '✓' : '·'}
          </span>
          <div className="flex-1 min-w-0">
            {/* Sub-question text */}
            <p className={clsx(
              'text-sm',
              question.completed && state === 'collapsed' && 'line-through text-gray-500',
              !question.completed && 'text-gray-800'
            )}>
              {question.text}
            </p>

            {/* Concepts to address */}
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <span className="text-[10px] text-gray-400">Address:</span>
              {question.key_concepts.map((concept, i) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                  {concept}
                </span>
              ))}
              {state === 'graded' && grade && (
                <span className={clsx('text-[10px] px-1.5 py-0.5 rounded border ml-auto', getVerdictColor(grade.verdict))}>
                  {grade.score.toFixed(1)}/10
                </span>
              )}
            </div>
          </div>
          {state !== 'collapsed' && (
            <button
              onClick={handleCollapse}
              className="text-gray-400 hover:text-gray-600 p-1"
              aria-label="Collapse"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Expanded: Answer input */}
      {(state === 'expanded' || state === 'submitting') && (
        <div className="px-3 pb-3 pt-0">
          <div className="border-t border-gray-100 pt-3">
            <textarea
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder={`Focus on: ${question.key_concepts.join(' and ')}. Aim for 50-100 words.`}
              className="w-full h-24 p-3 border border-gray-300 rounded text-sm resize-none focus:border-coral focus:ring-1 focus:ring-coral outline-none"
              disabled={state === 'submitting'}
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-gray-400">
                {answerText.trim().split(/\s+/).filter(Boolean).length} words
                <span className="text-gray-300 ml-1">(aim for 50-100)</span>
              </span>
              <div className="flex items-center gap-2">
                {error && (
                  <span className="text-[11px] text-coral">{error}</span>
                )}
                <button
                  onClick={handleSubmit}
                  disabled={state === 'submitting'}
                  className={clsx(
                    'px-3 py-1.5 text-xs font-semibold text-white transition-colors',
                    state === 'submitting'
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-black hover:bg-gray-800'
                  )}
                >
                  {state === 'submitting' ? 'Grading...' : 'Submit'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Graded feedback */}
      {state === 'graded' && grade && (
        <div className="px-3 pb-3 pt-0">
          <div className="border-t border-gray-100 pt-3">
            {/* Compact feedback */}
            <div className="flex items-start gap-3">
              <span className={clsx('text-lg font-bold', getScoreColor(grade.score))}>
                {grade.score.toFixed(1)}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-700">{grade.feedback}</p>
                {grade.missed_concepts.length > 0 && (
                  <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-gray-500">Missed:</span>
                    {grade.missed_concepts.map((concept, i) => (
                      <span key={i} className="text-[10px] px-1 py-0.5 bg-gray-100 text-gray-600 rounded">
                        {concept}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={handleCollapse}
              className="text-[10px] text-gray-400 hover:text-gray-600 mt-2"
            >
              collapse
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
