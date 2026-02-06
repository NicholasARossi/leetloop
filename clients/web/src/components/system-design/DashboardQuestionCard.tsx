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
        return 'bg-green-100 text-green-800 border-green-300'
      case 'borderline':
        return 'bg-amber-100 text-amber-800 border-amber-300'
      case 'fail':
        return 'bg-red-100 text-red-800 border-red-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-green-600'
    if (score >= 5) return 'text-amber-600'
    return 'text-red-600'
  }

  return (
    <div
      className={clsx(
        'border-2 transition-all',
        state === 'collapsed' && !question.completed && 'bg-white border-sky-200 hover:border-sky-400 cursor-pointer',
        state === 'collapsed' && question.completed && 'bg-gray-50 border-gray-200',
        state === 'expanded' && 'bg-white border-sky-400',
        state === 'submitting' && 'bg-white border-sky-300 opacity-75',
        state === 'graded' && grade && 'bg-white border-sky-200'
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
              ? 'bg-green-500 text-white'
              : 'bg-sky-500 text-white'
          )}>
            {question.completed || state === 'graded' ? '✓' : question.part_number}
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
                <span key={i} className="text-[10px] px-1.5 py-0.5 bg-sky-100 text-sky-700 rounded">
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
              className="w-full h-24 p-3 border border-gray-300 rounded text-sm resize-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 outline-none"
              disabled={state === 'submitting'}
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-gray-400">
                {answerText.trim().split(/\s+/).filter(Boolean).length} words
                <span className="text-gray-300 ml-1">(aim for 50-100)</span>
              </span>
              <div className="flex items-center gap-2">
                {error && (
                  <span className="text-[11px] text-red-600">{error}</span>
                )}
                <button
                  onClick={handleSubmit}
                  disabled={state === 'submitting'}
                  className={clsx(
                    'px-3 py-1.5 text-xs font-semibold text-white transition-colors',
                    state === 'submitting'
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-sky-500 hover:bg-sky-600'
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
                    <span className="text-[10px] text-red-500">Missed:</span>
                    {grade.missed_concepts.map((concept, i) => (
                      <span key={i} className="text-[10px] px-1 py-0.5 bg-red-50 text-red-700 rounded">
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
