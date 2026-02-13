'use client'

import { clsx } from 'clsx'
import type { LanguageAttempt } from '@/lib/api'

interface ExerciseCardProps {
  attempt: LanguageAttempt
  showQuestion?: boolean
  onToggleQuestion?: () => void
}

const exerciseTypeLabels: Record<string, string> = {
  vocabulary: 'Vocabulaire',
  grammar: 'Grammaire',
  fill_blank: 'Compl\u00e9ter',
  conjugation: 'Conjugaison',
  sentence_construction: 'Construction',
  reading_comprehension: 'Compr\u00e9hension',
  dictation: 'Dict\u00e9e',
}

export function ExerciseCard({ attempt, showQuestion = true, onToggleQuestion }: ExerciseCardProps) {
  return (
    <div className="card">
      <button
        onClick={onToggleQuestion}
        className="w-full flex items-center justify-between mb-3"
      >
        <div className="flex items-center gap-3">
          <span className="tag tag-accent">{attempt.topic}</span>
          <span className="tag text-xs">
            {exerciseTypeLabels[attempt.exercise_type] || attempt.exercise_type}
          </span>
          {attempt.question_focus_area && (
            <span className="text-xs text-gray-500 font-mono uppercase">
              {attempt.question_focus_area}
            </span>
          )}
        </div>
        <span className="text-gray-400 text-sm">
          {showQuestion ? 'Hide' : 'Show'} exercise
        </span>
      </button>

      {showQuestion && (
        <>
          <div className="p-4 bg-gray-50 border-l-4 border-black mb-4">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {attempt.question_text}
            </p>
          </div>

          {attempt.question_key_concepts.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Key concepts:</p>
              <div className="flex flex-wrap gap-1">
                {attempt.question_key_concepts.map((concept, i) => (
                  <span key={i} className="tag text-xs">
                    {concept}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
