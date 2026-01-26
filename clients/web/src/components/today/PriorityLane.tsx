'use client'

import { DifficultyBadge } from '@/components/ui/DifficultyBadge'
import type { DailyFocusProblem } from '@/lib/api'

interface PriorityLaneProps {
  title: string
  problems: DailyFocusProblem[]
  variant: 'reviews' | 'path' | 'skills'
  emptyMessage?: string
}

const variantStyles = {
  reviews: {
    header: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    headerText: 'text-red-700 dark:text-red-400',
    icon: '⏰',
    badge: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
  },
  path: {
    header: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    headerText: 'text-blue-700 dark:text-blue-400',
    icon: '📚',
    badge: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  },
  skills: {
    header: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    headerText: 'text-yellow-700 dark:text-yellow-400',
    icon: '💪',
    badge: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
  },
}

export function PriorityLane({ title, problems, variant, emptyMessage }: PriorityLaneProps) {
  const styles = variantStyles[variant]

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 border-b ${styles.header}`}>
        <div className="flex items-center gap-2">
          <span className="text-lg">{styles.icon}</span>
          <h3 className={`font-semibold ${styles.headerText}`}>{title}</h3>
          <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full ${styles.badge}`}>
            {problems.length}
          </span>
        </div>
      </div>

      {/* Problems list */}
      <div className="p-4 space-y-3">
        {problems.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">
            {emptyMessage || 'No problems'}
          </p>
        ) : (
          problems.map((problem, idx) => (
            <a
              key={`${problem.slug}-${idx}`}
              href={`https://leetcode.com/problems/${problem.slug}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 dark:text-white truncate">
                    {problem.title}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{problem.reason}</p>
                </div>
                {problem.difficulty && (
                  <DifficultyBadge difficulty={problem.difficulty} />
                )}
              </div>
              <div className="mt-2">
                <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded">
                  {problem.category}
                </span>
              </div>
            </a>
          ))
        )}
      </div>
    </div>
  )
}
