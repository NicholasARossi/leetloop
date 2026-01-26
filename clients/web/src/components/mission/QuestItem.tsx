'use client'

import { MainQuest, QuestStatus } from '@/lib/api'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'
import { clsx } from 'clsx'

interface QuestItemProps {
  quest: MainQuest
  index: number
}

export function QuestItem({ quest, index }: QuestItemProps) {
  const isCompleted = quest.status === 'completed'
  const isCurrent = quest.status === 'current'

  const leetcodeUrl = `https://leetcode.com/problems/${quest.slug}/`

  return (
    <div
      className={clsx(
        'rounded-xl p-4 transition-transform',
        isCompleted && 'bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 opacity-60',
        isCurrent && 'bg-white dark:bg-slate-800 border-2 border-sky-500/50 relative overflow-hidden',
        !isCompleted && !isCurrent && 'bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/30'
      )}
    >
      {/* Highlight gradient for current */}
      {isCurrent && (
        <div className="absolute inset-0 bg-gradient-to-r from-sky-500/5 to-transparent pointer-events-none" />
      )}

      <div className="relative flex items-center gap-4">
        {/* Status indicator */}
        <div
          className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
            isCompleted && 'bg-emerald-100 dark:bg-emerald-500/20',
            isCurrent && 'bg-sky-100 dark:bg-sky-500/20',
            !isCompleted && !isCurrent && 'bg-slate-200 dark:bg-slate-700/50'
          )}
        >
          {isCompleted ? (
            <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <span className={clsx(
              'font-semibold text-sm',
              isCurrent && 'text-sky-600 dark:text-sky-400',
              !isCurrent && 'text-slate-400 dark:text-slate-500'
            )}>
              {index + 1}
            </span>
          )}
        </div>

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={clsx(
                'font-medium',
                isCompleted && 'line-through text-slate-400 dark:text-slate-500',
                isCurrent && 'text-slate-900 dark:text-white',
                !isCompleted && !isCurrent && 'text-slate-500 dark:text-slate-400'
              )}
            >
              {quest.title}
            </span>
            {quest.difficulty && <DifficultyBadge difficulty={quest.difficulty} />}
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
            {quest.category}
          </p>
        </div>

        {/* Action / Status */}
        {isCompleted ? (
          <span className="text-emerald-600 dark:text-emerald-400 text-sm font-medium">Done</span>
        ) : isCurrent ? (
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-sky-500 hover:bg-sky-400 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Start
          </a>
        ) : null}
      </div>
    </div>
  )
}
