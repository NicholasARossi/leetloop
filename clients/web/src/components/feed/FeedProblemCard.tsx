'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import type { FeedItem } from '@/lib/api'

interface FeedProblemCardProps {
  item: FeedItem
  onSaveMistake?: (item: FeedItem, text: string) => Promise<void>
}

const difficultyColors: Record<string, string> = {
  Easy: 'text-gray-500',
  Medium: 'text-coral',
  Hard: 'text-black font-bold',
}

export function FeedProblemCard({ item, onSaveMistake }: FeedProblemCardProps) {
  const [showMistakeInput, setShowMistakeInput] = useState(false)
  const [mistakeText, setMistakeText] = useState('')
  const [savingMistake, setSavingMistake] = useState(false)

  const leetcodeUrl = `https://leetcode.com/problems/${item.problem_slug}/`
  const isCompleted = item.status === 'completed'
  const isMetric = item.feed_type === 'metric'
  const isJournal = item.practice_source === 'journal'

  const handleSaveMistake = async () => {
    if (!mistakeText.trim() || !onSaveMistake || savingMistake) return
    setSavingMistake(true)
    try {
      await onSaveMistake(item, mistakeText.trim())
      setMistakeText('')
      setShowMistakeInput(false)
    } finally {
      setSavingMistake(false)
    }
  }

  return (
    <div
      className={clsx(
        'list-item transition-all',
        isCompleted && 'opacity-60'
      )}
    >
      <div className="flex items-start gap-3">
        {/* Status indicator */}
        <div
          className={clsx(
            'w-7 h-7 flex items-center justify-center border-[2px] border-black text-xs flex-shrink-0',
            isCompleted && item.was_accepted ? 'bg-accent text-white' :
            isCompleted && !item.was_accepted ? 'bg-gray-300 text-black' :
            'bg-white'
          )}
        >
          {isCompleted ? (
            item.was_accepted ? (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )
          ) : (
            <span className="text-[10px] font-mono">{item.sort_order + 1}</span>
          )}
        </div>

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={leetcodeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={clsx(
                'font-medium text-sm hover:text-accent hover:underline',
                isCompleted ? 'line-through text-gray-400' : 'text-black'
              )}
            >
              {item.problem_title || item.problem_slug.replace(/-/g, ' ')}
            </a>

            {item.difficulty && (
              <span className={clsx('text-xs uppercase font-medium', difficultyColors[item.difficulty] || 'text-gray-500')}>
                {item.difficulty}
              </span>
            )}

            {/* Feed type badge */}
            <span className={clsx(
              'text-[10px] px-1.5 py-0.5 font-bold uppercase',
              isMetric
                ? 'bg-accent/20 text-accent border border-accent/30'
                : 'bg-gray-100 text-gray-600'
            )}>
              {isMetric ? 'Metric' : 'Practice'}
            </span>

            {/* Journal badge */}
            {isJournal && (
              <span className="text-[10px] px-1.5 py-0.5 font-bold uppercase bg-amber-100 text-amber-700 border border-amber-300">
                Journal
              </span>
            )}

            {/* Optimal badge for completed metric items */}
            {isCompleted && isMetric && item.was_optimal && (
              <span className="text-[10px] px-1.5 py-0.5 font-bold uppercase bg-green-100 text-green-700 border border-green-300">
                Optimal
              </span>
            )}
          </div>

          {/* Reason/rationale */}
          <p className="text-gray-500 text-xs mt-1">
            {isMetric
              ? (item.metric_rationale || 'Unseen problem')
              : (item.practice_reason || `Source: ${item.practice_source || 'practice'}`)}
          </p>

          {/* Completion details */}
          {isCompleted && item.runtime_percentile != null && (
            <p className="text-xs text-gray-400 mt-1 font-mono">
              Runtime: {item.runtime_percentile.toFixed(1)}th percentile
            </p>
          )}

          {/* Tags */}
          {item.tags && item.tags.length > 0 && (
            <div className="flex gap-1 mt-1.5 flex-wrap">
              {item.tags.map((tag) => (
                <span key={tag} className="tag text-[10px]">{tag}</span>
              ))}
            </div>
          )}

          {/* Log Mistake (completed items only) */}
          {isCompleted && onSaveMistake && !showMistakeInput && (
            <button
              onClick={() => setShowMistakeInput(true)}
              className="text-[10px] text-gray-400 hover:text-accent mt-1"
            >
              Log Mistake
            </button>
          )}
          {showMistakeInput && (
            <div className="flex items-center gap-1.5 mt-1.5">
              <input
                type="text"
                value={mistakeText}
                onChange={(e) => setMistakeText(e.target.value.slice(0, 1000))}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSaveMistake() }}
                placeholder="What went wrong?"
                className="flex-1 border border-gray-200 rounded px-1.5 py-1 text-[11px] text-black placeholder:text-gray-400 focus:outline-none focus:border-accent"
                autoFocus
                disabled={savingMistake}
              />
              <button
                onClick={handleSaveMistake}
                disabled={!mistakeText.trim() || savingMistake}
                className="text-[10px] text-accent hover:underline"
              >
                Save
              </button>
              <button
                onClick={() => { setShowMistakeInput(false); setMistakeText('') }}
                className="text-[10px] text-gray-400 hover:text-black"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Action */}
        {!isCompleted && (
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-xs flex-shrink-0"
          >
            Solve
          </a>
        )}
      </div>
    </div>
  )
}
