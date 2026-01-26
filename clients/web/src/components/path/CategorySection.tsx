'use client'

import { useState } from 'react'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'

interface Problem {
  slug: string
  title: string
  difficulty?: string
  completed: boolean
}

interface CategorySectionProps {
  name: string
  total: number
  completed: number
  problems: Problem[]
  defaultOpen?: boolean
}

export function CategorySection({
  name,
  total,
  completed,
  problems,
  defaultOpen = false,
}: CategorySectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const progress = total > 0 ? (completed / total) * 100 : 0
  const isComplete = completed === total && total > 0

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>

        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-900 dark:text-white">{name}</span>
            {isComplete && <span className="text-green-500">✓</span>}
          </div>
          <div className="text-sm text-slate-500">
            {completed}/{total} completed
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-32 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              isComplete
                ? 'bg-green-500'
                : progress > 50
                ? 'bg-brand-500'
                : 'bg-yellow-500'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </button>

      {/* Problems list */}
      {isOpen && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-100 dark:border-slate-700">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {problems.map((problem) => (
              <a
                key={problem.slug}
                href={`https://leetcode.com/problems/${problem.slug}/`}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex items-center gap-2 p-2 rounded-lg transition-colors ${
                  problem.completed
                    ? 'bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/30'
                    : 'bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700'
                }`}
              >
                <span className={`flex-shrink-0 w-5 h-5 flex items-center justify-center rounded-full ${
                  problem.completed
                    ? 'bg-green-500 text-white'
                    : 'bg-slate-200 dark:bg-slate-600'
                }`}>
                  {problem.completed ? (
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <span className="w-2 h-2 bg-slate-400 dark:bg-slate-400 rounded-full" />
                  )}
                </span>
                <span className={`flex-1 text-sm truncate ${
                  problem.completed
                    ? 'text-green-800 dark:text-green-200'
                    : 'text-slate-700 dark:text-slate-300'
                }`}>
                  {problem.title}
                </span>
                {problem.difficulty && (
                  <DifficultyBadge difficulty={problem.difficulty as 'Easy' | 'Medium' | 'Hard'} />
                )}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
