'use client'

import { useState, useRef, useMemo, useCallback } from 'react'
import { clsx } from 'clsx'
import type { MLCodingDailyExercise } from '@/lib/api'
import { highlightPython } from './python-highlight'

interface MLCodingExerciseCardProps {
  exercise: MLCodingDailyExercise
  onSubmit: (exerciseId: string, code: string) => Promise<void>
}

type CardState = 'pending' | 'answering' | 'submitting' | 'graded'

function LineNumbers({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className="line-num">{i + 1}</span>
      ))}
    </>
  )
}

export function MLCodingExerciseCard({ exercise, onSubmit }: MLCodingExerciseCardProps) {
  const initialState: CardState = exercise.status === 'completed' ? 'graded' : 'pending'
  const [state, setState] = useState<CardState>(initialState)
  const [code, setCode] = useState(exercise.submitted_code || exercise.starter_code || '')
  const [expanded, setExpanded] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const highlightRef = useRef<HTMLPreElement>(null)

  const isPass = exercise.verdict === 'pass' || (exercise.score != null && exercise.score >= 7)

  const lineCount = useMemo(() => {
    const lines = code.split('\n').length
    return Math.max(lines, 15)
  }, [code])

  const highlightedCode = useMemo(() => highlightPython(code), [code])

  // Keep highlight layer scroll in sync with textarea
  const handleScroll = useCallback(() => {
    if (textareaRef.current && highlightRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft
    }
  }, [])

  const handleCodeChange = (value: string) => {
    setCode(value)
    if (state === 'pending' && value !== (exercise.starter_code || '')) {
      setState('answering')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Tab inserts 2 spaces
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = textareaRef.current
      if (!textarea) return
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const newValue = code.substring(0, start) + '  ' + code.substring(end)
      setCode(newValue)
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2
      })
    }
    // Cmd/Ctrl+Enter submits
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && code.trim()) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleSubmit = async () => {
    if (!code.trim()) return
    setState('submitting')
    try {
      await onSubmit(exercise.id, code)
      setState('graded')
    } catch {
      setState('answering')
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  // Graded state - collapsed by default
  if (state === 'graded') {
    return (
      <div
        className="border-2 bg-white transition-all border-gray-200"
        style={isPass ? { borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color)' } : {}}
      >
        {/* Collapsed summary */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left px-4 py-3 flex items-center gap-2 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <span className="tag text-[10px]">{exercise.problem_title || 'ML CODING'}</span>
          {exercise.is_review && (
            <span className="badge badge-accent text-[9px]">Review</span>
          )}
          <span className="text-xs text-gray-600 flex-1 truncate">
            {exercise.prompt_text.slice(0, 60)}...
          </span>
          {exercise.score != null && (
            <span className={clsx('text-lg font-bold font-mono', getScoreColor(exercise.score))}>
              {exercise.score.toFixed(1)}
            </span>
          )}
          {exercise.verdict && (
            isPass
              ? <span className="badge badge-accent text-[9px]">Pass</span>
              : exercise.verdict === 'borderline'
                ? <span className="badge badge-default text-[9px]">Borderline</span>
                : <span className="badge badge-default text-[9px]">Needs Work</span>
          )}
          <span className="text-gray-400 text-xs ml-1">{expanded ? '\u25B2' : '\u25BC'}</span>
        </button>

        {/* Expanded details */}
        {expanded && (
          <div className="px-4 pb-4 border-t border-gray-100 space-y-3 pt-3">
            {/* Sub-scores */}
            <div className="grid grid-cols-3 gap-2">
              {exercise.correctness_score != null && (
                <div className="bg-gray-50 p-2 text-center">
                  <p className={clsx('font-mono font-bold text-sm', getScoreColor(exercise.correctness_score))}>
                    {exercise.correctness_score.toFixed(1)}
                  </p>
                  <p className="text-[10px] text-gray-500 uppercase">Correctness</p>
                </div>
              )}
              {exercise.code_quality_score != null && (
                <div className="bg-gray-50 p-2 text-center">
                  <p className={clsx('font-mono font-bold text-sm', getScoreColor(exercise.code_quality_score))}>
                    {exercise.code_quality_score.toFixed(1)}
                  </p>
                  <p className="text-[10px] text-gray-500 uppercase">Code Quality</p>
                </div>
              )}
              {exercise.math_understanding_score != null && (
                <div className="bg-gray-50 p-2 text-center">
                  <p className={clsx('font-mono font-bold text-sm', getScoreColor(exercise.math_understanding_score))}>
                    {exercise.math_understanding_score.toFixed(1)}
                  </p>
                  <p className="text-[10px] text-gray-500 uppercase">Math</p>
                </div>
              )}
            </div>

            {/* Feedback */}
            {exercise.feedback && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Feedback:</span>
                <p className="text-xs text-gray-700 mt-1">{exercise.feedback}</p>
              </div>
            )}

            {/* Submitted code - with syntax highlighting */}
            {exercise.submitted_code && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Your Code:</span>
                <div className="code-display mt-1">
                  <div className="code-display-gutter">
                    <LineNumbers count={exercise.submitted_code.split('\n').length} />
                  </div>
                  <div className="code-display-content">
                    <pre dangerouslySetInnerHTML={{ __html: highlightPython(exercise.submitted_code) }} />
                  </div>
                </div>
              </div>
            )}

            {/* Missed concepts */}
            {exercise.missed_concepts.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Missed Concepts:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {exercise.missed_concepts.map((c, i) => (
                    <span key={i} className="tag text-[10px]">{c}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested improvements */}
            {exercise.suggested_improvements.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Improvements:</span>
                <ul className="mt-1 space-y-1">
                  {exercise.suggested_improvements.map((s, i) => (
                    <li key={i} className="text-xs text-gray-600 pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-gray-400">{s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  // Pending / Answering / Submitting states
  return (
    <div className="code-editor">
      {/* Header bar */}
      <div className="code-editor-header">
        <div className="flex items-center gap-2">
          <h3>{exercise.problem_title || 'ML Coding'}</h3>
          {exercise.is_review && (
            <span className="badge badge-accent text-[9px]">Review</span>
          )}
        </div>
        <span className="badge text-[10px]">Python</span>
      </div>

      {/* Problem prompt */}
      <div className="px-4 py-3 text-sm text-gray-800 whitespace-pre-wrap border-b border-gray-200 bg-white">
        {exercise.prompt_text}
      </div>

      {/* Editor body with syntax highlight overlay */}
      <div className="code-editor-body">
        <div className="code-editor-gutter">
          <LineNumbers count={lineCount} />
        </div>
        <div className="code-editor-overlay">
          <pre
            ref={highlightRef}
            className="code-editor-highlight"
            aria-hidden="true"
            dangerouslySetInnerHTML={{ __html: highlightedCode + '\n' }}
          />
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(e) => handleCodeChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            placeholder="# Write your Python solution here..."
            disabled={state === 'submitting'}
            spellCheck={false}
            className={clsx(
              'code-editor-textarea',
              state === 'submitting' && 'opacity-50 cursor-not-allowed'
            )}
          />
        </div>
      </div>

      {/* Footer toolbar */}
      <div className="code-editor-footer">
        <span className="text-[11px] text-gray-400">
          <kbd>Tab</kbd> indent &middot; <kbd>{typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '\u2318' : 'Ctrl'}+Enter</kbd> submit
        </span>
        <button
          onClick={handleSubmit}
          disabled={state === 'submitting' || !code.trim()}
          className={clsx(
            'btn-primary text-[11px] font-semibold uppercase tracking-wider !px-5 !py-2',
            (state === 'submitting' || !code.trim()) && 'opacity-40 cursor-not-allowed pointer-events-none'
          )}
        >
          {state === 'submitting' ? 'Grading...' : 'Submit'}
        </button>
      </div>
    </div>
  )
}
