'use client'

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'

interface DailyExerciseCardProps {
  exercise: {
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
  onSubmit: (exerciseId: string, responseText: string) => Promise<void>
}

type CardState = 'pending' | 'answering' | 'submitting' | 'graded'

const TEXTAREA_ROWS: Record<string, number> = {
  short_text: 2,
  long_text: 4,
  free_form: 8,
}

export function DailyExerciseCard({ exercise, onSubmit }: DailyExerciseCardProps) {
  const initialState: CardState = exercise.status === 'completed' ? 'graded' : 'pending'
  const [state, setState] = useState<CardState>(initialState)
  const [responseText, setResponseText] = useState(exercise.response_text || '')
  const [expanded, setExpanded] = useState(false)

  const responseFormat = exercise.response_format || 'single_line'
  const wordTarget = exercise.word_target || 3
  const isTextarea = responseFormat !== 'single_line'
  const showWordCount = responseFormat === 'long_text' || responseFormat === 'free_form'

  const wordCount = useMemo(() => {
    if (!responseText.trim()) return 0
    return responseText.trim().split(/\s+/).length
  }, [responseText])

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'pass':
        return <span className="badge badge-accent">PASS</span>
      case 'borderline':
        return <span className="badge badge-default">BORDERLINE</span>
      case 'fail':
        return <span className="badge-hard">FAIL</span>
      default:
        return null
    }
  }

  const handleInputChange = (value: string) => {
    setResponseText(value)
    if (state === 'pending' && value.length > 0) {
      setState('answering')
    } else if (state === 'answering' && value.length === 0) {
      setState('pending')
    }
  }

  const handleSubmit = async () => {
    if (!responseText.trim()) return
    setState('submitting')
    try {
      await onSubmit(exercise.id, responseText)
      setState('graded')
    } catch {
      setState('answering')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isTextarea) {
      // Cmd/Ctrl+Enter to submit for textarea
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && responseText.trim()) {
        e.preventDefault()
        handleSubmit()
      }
    } else {
      // Enter to submit for single-line input
      if (e.key === 'Enter' && !e.shiftKey && responseText.trim()) {
        e.preventDefault()
        handleSubmit()
      }
    }
  }

  // Graded state - collapsed single line
  if (state === 'graded') {
    return (
      <div
        className={clsx(
          'border-2 bg-white transition-all',
          exercise.is_review ? 'border-l-4 border-l-coral border-gray-200' : 'border-gray-200'
        )}
      >
        {/* Collapsed summary row */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left px-3 py-2.5 flex items-center gap-2 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <span className="tag text-[10px]">{exercise.exercise_type.toUpperCase()}</span>
          <span className="text-xs text-gray-600 flex-1 truncate">{exercise.focus_area || exercise.topic}</span>
          {exercise.score != null && (
            <span className={clsx('text-lg font-bold font-mono', getScoreColor(exercise.score))}>
              {exercise.score.toFixed(1)}
            </span>
          )}
          {exercise.verdict && getVerdictBadge(exercise.verdict)}
          <span className="text-gray-400 text-xs ml-1">{expanded ? '\u25B2' : '\u25BC'}</span>
        </button>

        {/* Expanded details */}
        {expanded && (
          <div className="px-3 pb-3 border-t border-gray-100 space-y-2 pt-2">
            <div>
              <span className="text-[10px] uppercase tracking-wide text-gray-400">Q:</span>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">{exercise.question_text}</p>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wide text-gray-400">A:</span>
              <p className="text-sm font-mono text-black">{exercise.response_text || responseText}</p>
            </div>
            {exercise.feedback && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Feedback:</span>
                <p className="text-xs text-gray-700">{exercise.feedback}</p>
              </div>
            )}
            {exercise.corrections && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-coral">Correction:</span>
                <p className="text-xs text-coral">{exercise.corrections}</p>
              </div>
            )}
            {exercise.missed_concepts && exercise.missed_concepts.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {exercise.missed_concepts.map((concept, i) => (
                  <span key={i} className="tag text-[10px]">{concept}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  // Pending / Answering / Submitting states
  return (
    <div
      className={clsx(
        'border-2 bg-white',
        exercise.is_review ? 'border-l-4 border-l-coral border-gray-200' : 'border-gray-200'
      )}
    >
      <div className="px-3 pt-3 pb-2">
        {/* Header: type tag + review badge + focus area */}
        <div className="flex items-center gap-2 mb-2">
          <span className="tag text-[10px]">{exercise.exercise_type.toUpperCase()}</span>
          {exercise.is_review && (
            <span className="badge badge-accent text-[10px]">Review</span>
          )}
          {exercise.focus_area && (
            <span className="text-xs text-gray-500 ml-auto">{exercise.focus_area}</span>
          )}
        </div>

        {/* Question */}
        <p className="text-sm text-gray-800 whitespace-pre-wrap mb-3">{exercise.question_text}</p>

        {/* Input area */}
        {isTextarea ? (
          <div>
            <textarea
              value={responseText}
              onChange={(e) => handleInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Your answer..."
              disabled={state === 'submitting'}
              rows={TEXTAREA_ROWS[responseFormat] || 2}
              className={clsx(
                'w-full px-3 py-1.5 border-2 border-black text-sm font-mono focus:outline-none focus:border-coral transition-colors resize-vertical',
                state === 'submitting' && 'opacity-50 cursor-not-allowed bg-gray-50'
              )}
            />
            <div className="flex items-center justify-between mt-1">
              <div className="flex items-center gap-3">
                {showWordCount && (
                  <span className="text-[10px] text-gray-400 font-mono">
                    {wordCount} word{wordCount !== 1 ? 's' : ''} — target: {wordTarget}
                  </span>
                )}
                <span className="text-[10px] text-gray-400">
                  {navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+Enter to submit
                </span>
              </div>
              <button
                onClick={handleSubmit}
                disabled={state === 'submitting' || !responseText.trim()}
                className={clsx(
                  'px-4 py-1.5 text-xs font-semibold text-white transition-colors whitespace-nowrap',
                  state === 'submitting'
                    ? 'bg-gray-400 cursor-not-allowed'
                    : !responseText.trim()
                      ? 'bg-gray-300 cursor-not-allowed'
                      : 'bg-black hover:bg-gray-800'
                )}
              >
                {state === 'submitting' ? 'Grading...' : 'Submit'}
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={responseText}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Your answer..."
                disabled={state === 'submitting'}
                className={clsx(
                  'flex-1 px-3 py-1.5 border-2 border-black text-sm font-mono focus:outline-none focus:border-coral transition-colors',
                  state === 'submitting' && 'opacity-50 cursor-not-allowed bg-gray-50'
                )}
              />
              <button
                onClick={handleSubmit}
                disabled={state === 'submitting' || !responseText.trim()}
                className={clsx(
                  'px-4 py-1.5 text-xs font-semibold text-white transition-colors whitespace-nowrap',
                  state === 'submitting'
                    ? 'bg-gray-400 cursor-not-allowed'
                    : !responseText.trim()
                      ? 'bg-gray-300 cursor-not-allowed'
                      : 'bg-black hover:bg-gray-800'
                )}
              >
                {state === 'submitting' ? 'Grading...' : 'Submit'}
              </button>
            </div>
            <p className="text-[10px] text-gray-400 mt-1">Enter to submit</p>
          </>
        )}
      </div>
    </div>
  )
}
