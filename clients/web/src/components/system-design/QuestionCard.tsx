'use client'

import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import type { SessionQuestion } from '@/lib/api'

interface QuestionCardProps {
  question: SessionQuestion
  questionNumber: number
  totalQuestions: number
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function QuestionCard({
  question,
  questionNumber,
  totalQuestions,
  value,
  onChange,
  disabled = false,
}: QuestionCardProps) {
  const [wordCount, setWordCount] = useState(0)

  useEffect(() => {
    const words = value.trim().split(/\s+/).filter(w => w.length > 0)
    setWordCount(words.length)
  }, [value])

  const getWordCountColor = () => {
    if (wordCount < 50) return 'text-coral'
    if (wordCount < 150) return 'text-gray-500'
    return 'text-coral'
  }

  const getWordCountHint = () => {
    if (wordCount < 50) return 'Need more detail'
    if (wordCount < 150) return 'Good start'
    if (wordCount < 300) return 'Solid response'
    return 'Comprehensive'
  }

  return (
    <div className="card space-y-4">
      {/* Question Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="tag tag-accent">
            Q{questionNumber}/{totalQuestions}
          </span>
          <span className="text-xs text-gray-500 font-mono uppercase">
            {question.focus_area}
          </span>
        </div>
      </div>

      {/* Question Text */}
      <div className="p-4 bg-gray-50 border-l-4 border-black">
        <p className="text-sm leading-relaxed">
          {question.text}
        </p>
      </div>

      {/* Key Concepts */}
      {question.key_concepts.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">Key concepts to address:</p>
          <div className="flex flex-wrap gap-1">
            {question.key_concepts.map((concept, i) => (
              <span key={i} className="tag text-xs">
                {concept}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Answer Textarea */}
      <div className="space-y-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Write your response here. Be specific about architecture decisions, tradeoffs, and scaling considerations..."
          className={clsx(
            'w-full h-64 p-4 border-2 border-black bg-white',
            'text-sm leading-relaxed font-mono',
            'focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2',
            'placeholder:text-gray-400',
            'disabled:bg-gray-100 disabled:cursor-not-allowed',
            'resize-y min-h-[200px]'
          )}
        />

        {/* Word Count */}
        <div className="flex justify-between items-center text-xs">
          <span className={getWordCountColor()}>
            {wordCount} words - {getWordCountHint()}
          </span>
          <span className="text-gray-400">
            Aim for 200-400 words per question
          </span>
        </div>
      </div>
    </div>
  )
}
