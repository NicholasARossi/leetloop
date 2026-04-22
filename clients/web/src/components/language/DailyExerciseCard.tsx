'use client'

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import type { WrittenGrading, GrammarTargetHit } from '@/lib/api'

interface DailyExerciseCardProps {
  exercise: {
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
    written_grading?: WrittenGrading
  }
  onSubmit: (exerciseId: string, responseText: string) => Promise<void>
  autoExpand?: boolean
}

type CardState = 'pending' | 'answering' | 'submitting' | 'graded'

const TEXTAREA_ROWS: Record<string, number> = {
  long_text: 6,
  free_form: 10,
}

export function DailyExerciseCard({ exercise, onSubmit, autoExpand = false }: DailyExerciseCardProps) {
  const initialState: CardState = exercise.status === 'completed' ? 'graded' : 'pending'
  const [state, setState] = useState<CardState>(initialState)
  const [responseText, setResponseText] = useState(exercise.response_text || '')
  const [expanded, setExpanded] = useState(false)
  const [pendingExpanded, setPendingExpanded] = useState(autoExpand)

  const responseFormat = exercise.response_format || 'long_text'
  const wordTarget = exercise.word_target || 100

  const wordCount = useMemo(() => {
    if (!responseText.trim()) return 0
    return responseText.trim().split(/\s+/).length
  }, [responseText])

  const wordProgressPercent = Math.min((wordCount / wordTarget) * 100, 120)

  const isPass = exercise.verdict === 'pass' || exercise.verdict === 'strong' || (exercise.score != null && exercise.score >= 7)

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
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && responseText.trim()) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const grammarTargets = exercise.grammar_targets ?? exercise.key_concepts ?? []
  const vocabTargets = exercise.vocab_targets ?? []

  // Graded state - collapsed single line
  if (state === 'graded') {
    return (
      <div
        className={clsx(
          'border-2 bg-white transition-all',
          'border-gray-200'
        )}
        style={
          isPass
            ? { borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color)' }
            : exercise.is_review
              ? { borderLeftWidth: '4px', borderLeftColor: '#b0b0b0' }
              : {}
        }
      >
        {/* Collapsed summary row */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left px-3 py-2.5 flex items-center gap-2 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <span className="tag text-[10px]">{exercise.exercise_type.toUpperCase()}</span>
          {exercise.is_review && (
            <span className="badge badge-accent text-[9px]">Révision</span>
          )}
          {exercise.review_topic_reason && !exercise.is_review && (
            <span className="badge badge-default text-[9px]">Adapté</span>
          )}
          <span className="text-xs text-gray-600 flex-1 truncate">{exercise.focus_area || exercise.topic}</span>
          {exercise.score != null && (
            <span
              className={clsx('text-lg font-bold font-mono')}
              style={{ color: isPass ? 'var(--accent-color-dark)' : '#737373' }}
            >
              {exercise.score.toFixed(1)}
            </span>
          )}
          {exercise.verdict && (
            isPass
              ? <span className="badge badge-accent text-[9px]">Réussi</span>
              : exercise.verdict === 'borderline' || exercise.verdict === 'developing'
                ? <span className="badge badge-default text-[9px]">Limite</span>
                : <span className="badge badge-default text-[9px]">À revoir</span>
          )}
          <span className="text-gray-400 text-xs ml-1">{expanded ? '\u25B2' : '\u25BC'}</span>
        </button>

        {/* Expanded details */}
        {expanded && (
          <div className="px-3 pb-3 border-t border-gray-100 space-y-2 pt-2">
            <div>
              <span className="text-[10px] uppercase tracking-wide text-gray-400">Q :</span>
              <p className="text-sm text-gray-800 whitespace-pre-wrap">{exercise.question_text}</p>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wide text-gray-400">R :</span>
              <p className="text-sm font-mono text-black">{exercise.response_text || responseText}</p>
            </div>
            {exercise.feedback && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Retour :</span>
                <p className="text-xs text-gray-700">{exercise.feedback}</p>
              </div>
            )}
            {exercise.corrections && (
              <div>
                <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--accent-color-dark)' }}>Correction :</span>
                <p className="text-xs" style={{ color: 'var(--accent-color-dark)' }}>{exercise.corrections}</p>
              </div>
            )}

            {/* Grammar target hits */}
            {exercise.written_grading?.grammar_target_hits && exercise.written_grading.grammar_target_hits.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Grammaire visée :</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {exercise.written_grading.grammar_target_hits.map((hit: GrammarTargetHit, i: number) => (
                    <span
                      key={i}
                      className={clsx(
                        'inline-block px-1.5 py-0.5 text-xs font-mono border rounded',
                        hit.used && hit.correct
                          ? 'bg-green-50 text-green-700 border-green-200'
                          : hit.used
                            ? 'bg-amber-50 text-amber-700 border-amber-200'
                            : 'bg-red-50 text-red-700 border-red-200'
                      )}
                    >
                      {hit.used && hit.correct ? '✓' : hit.used ? '~' : '✗'} {hit.target}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Vocab target hits */}
            {exercise.written_grading?.vocab_target_hits && exercise.written_grading.vocab_target_hits.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Lexique utilisé :</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {exercise.written_grading.vocab_target_hits.map((vocab: string, i: number) => (
                    <span
                      key={i}
                      className="inline-block px-1.5 py-0.5 text-xs font-mono bg-green-50 text-green-700 border border-green-200 rounded"
                    >
                      ✓ {vocab}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 4-dimension scores */}
            {exercise.written_grading?.scores && Object.keys(exercise.written_grading.scores).length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">Détails :</span>
                <div className="grid grid-cols-2 gap-1 mt-1">
                  {Object.entries(exercise.written_grading.scores).map(([dim, score]) => (
                    <div key={dim} className="flex items-center gap-1.5 text-xs">
                      <span className={clsx(
                        'w-2 h-2 rounded-full',
                        dim === 'grammar' ? 'bg-blue-500' :
                        dim === 'lexical' ? 'bg-amber-500' :
                        dim === 'discourse' ? 'bg-purple-500' :
                        'bg-green-500'
                      )} />
                      <span className="text-gray-600 capitalize">{dim}</span>
                      <span className="font-mono font-bold ml-auto">{score.score.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
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
  // Show collapsed summary if not expanded and still in pending state
  if (state === 'pending' && !pendingExpanded) {
    return (
      <div
        className="border-2 bg-white border-gray-200 transition-all"
        style={
          exercise.is_review
            ? { borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color-40)' }
            : {}
        }
      >
        <button
          onClick={() => setPendingExpanded(true)}
          className="w-full text-left px-3 py-2.5 flex items-center gap-2 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <span className="tag text-[10px]">{exercise.exercise_type.toUpperCase()}</span>
          {exercise.is_review && (
            <span className="badge badge-accent text-[9px]">Révision</span>
          )}
          {exercise.review_topic_reason && !exercise.is_review && (
            <span className="badge badge-default text-[9px]">Adapté</span>
          )}
          <span className="text-xs text-gray-600 flex-1 truncate">{exercise.focus_area || exercise.topic}</span>
          <span className="text-gray-400 text-xs ml-1">{'\u25BC'}</span>
        </button>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'border-2 bg-white transition-all',
        state === 'answering' || state === 'submitting'
          ? 'border-gray-300'
          : 'border-gray-200'
      )}
      style={
        (state === 'answering' || state === 'submitting')
          ? { borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color)' }
          : exercise.is_review
            ? { borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color-40)' }
            : {}
      }
    >
      {/* Collapse button for pending state */}
      {state === 'pending' && (
        <button
          onClick={() => setPendingExpanded(false)}
          className="w-full text-left px-3 pt-2 flex items-center gap-2 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <span className="tag text-[10px]">{exercise.exercise_type.toUpperCase()}</span>
          {exercise.is_review && (
            <span className="badge badge-accent text-[9px]">Révision</span>
          )}
          <span className="text-xs text-gray-600 flex-1 truncate">{exercise.focus_area || exercise.topic}</span>
          <span className="text-gray-400 text-xs ml-1">{'\u25B2'}</span>
        </button>
      )}

      <div className="px-3 pt-3 pb-2">
        {/* Header: type tag + review/adapted badge + focus area (only when answering/submitting) */}
        {state !== 'pending' && (
          <div className="flex items-center gap-2 mb-2">
            <span className="tag text-[10px]">{exercise.exercise_type.toUpperCase()}</span>
            {exercise.is_review && (
              <span className="badge badge-accent text-[10px]">Révision</span>
            )}
            {exercise.review_topic_reason && !exercise.is_review && (
              <span className="badge badge-default text-[10px]">Adapté</span>
            )}
            {exercise.focus_area && (
              <span className="text-xs text-gray-500 ml-auto">{exercise.focus_area}</span>
            )}
          </div>
        )}

        {/* Grammar + Vocab target chips */}
        {(grammarTargets.length > 0 || vocabTargets.length > 0) && (
          <div className="flex flex-wrap gap-1 mb-2">
            {grammarTargets.map((g, i) => (
              <span key={`g-${i}`} className="inline-block px-1.5 py-0.5 text-xs font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded">
                {g}
              </span>
            ))}
            {vocabTargets.map((v, i) => (
              <span key={`v-${i}`} className="inline-block px-1.5 py-0.5 text-xs font-mono bg-amber-50 text-amber-700 border border-amber-200 rounded">
                {v}
              </span>
            ))}
          </div>
        )}

        {/* Question */}
        <p className="text-sm text-gray-800 whitespace-pre-wrap mb-3">{exercise.question_text}</p>

        {/* Word target indicator */}
        {state === 'pending' && (
          <p className="text-[10px] text-gray-400 mb-2">
            {responseFormat === 'free_form' ? 'Expression libre' : 'Texte long'} — cible : {wordTarget} mot{wordTarget > 1 ? 's' : ''}
          </p>
        )}

        {/* Textarea input */}
        <div>
          <textarea
            value={responseText}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Votre réponse..."
            disabled={state === 'submitting'}
            rows={TEXTAREA_ROWS[responseFormat] || 6}
            className={clsx(
              'w-full px-3 py-1.5 border-2 border-gray-300 text-sm font-mono focus:outline-none transition-colors resize-vertical',
              state === 'submitting' && 'opacity-50 cursor-not-allowed bg-gray-50'
            )}
            style={{ borderColor: state === 'answering' ? 'var(--accent-color)' : undefined }}
          />

          {/* Word count progress bar */}
          <div className="w-full bg-gray-100 h-1 mt-1 rounded-full overflow-hidden">
            <div
              className="h-1 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(wordProgressPercent, 100)}%`,
                backgroundColor: wordProgressPercent >= 100 ? 'var(--accent-color)' : '#d1d5db',
              }}
            />
          </div>

          <div className="flex items-center justify-between mt-1">
            <div className="flex items-center gap-3">
              <span className="text-[10px] text-gray-400 font-mono">
                {wordCount} / {wordTarget} mot{wordTarget > 1 ? 's' : ''}
              </span>
              <span className="text-[10px] text-gray-400">
                {typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+Entrée pour soumettre
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
              {state === 'submitting' ? 'Évaluation...' : 'Soumettre'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
