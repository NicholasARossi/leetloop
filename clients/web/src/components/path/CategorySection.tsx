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
    <div className="card p-0 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center gap-4 hover:bg-gray-50 transition-colors"
      >
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>

        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <span className="font-medium text-black">{name}</span>
            {isComplete && (
              <span className="w-4 h-4 bg-coral border-2 border-black flex items-center justify-center">
                <svg className="w-2.5 h-2.5 text-black" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </span>
            )}
          </div>
          <div className="text-sm text-gray-500">
            {completed}/{total} completed
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-32 progress-bar">
          <div
            className="progress-fill transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </button>

      {/* Problems list */}
      {isOpen && (
        <div className="px-4 pb-4 pt-2 border-t-2 border-black">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {problems.map((problem) => (
              <a
                key={problem.slug}
                href={`https://leetcode.com/problems/${problem.slug}/`}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex items-center gap-2 p-2 border-2 transition-colors ${
                  problem.completed
                    ? 'bg-coral border-black'
                    : 'bg-white border-gray-300 hover:border-black'
                }`}
              >
                <span className={`checkbox ${problem.completed ? 'checked' : ''}`} />
                <span className={`flex-1 text-sm truncate ${
                  problem.completed ? 'text-black' : 'text-gray-700'
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
