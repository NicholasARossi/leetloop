'use client'

import { SideQuest } from '@/lib/api'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'
import { clsx } from 'clsx'

interface SideQuestCardProps {
  quest: SideQuest
}

const questTypeLabels: Record<string, { label: string; className: string }> = {
  review_due: {
    label: 'Review Due',
    className: 'bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400',
  },
  skill_gap: {
    label: 'Skill Gap',
    className: 'bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400',
  },
  slow_solve: {
    label: 'Needs Practice',
    className: 'bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400',
  },
}

export function SideQuestCard({ quest }: SideQuestCardProps) {
  const leetcodeUrl = `https://leetcode.com/problems/${quest.slug}/`
  const typeInfo = questTypeLabels[quest.quest_type] || questTypeLabels.skill_gap

  return (
    <div
      className={clsx(
        'bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 rounded-xl p-4',
        quest.completed && 'opacity-60'
      )}
    >
      {/* Type badge */}
      <div className="flex items-center gap-2 mb-3">
        <span className={clsx('px-2 py-0.5 text-xs rounded-full font-medium', typeInfo.className)}>
          {typeInfo.label}
        </span>
      </div>

      {/* Problem row */}
      <div className="flex items-center gap-3">
        {/* Checkbox */}
        <div
          className={clsx(
            'w-6 h-6 border-2 rounded flex items-center justify-center flex-shrink-0',
            quest.completed
              ? 'bg-emerald-100 dark:bg-emerald-500/20 border-emerald-500'
              : 'border-slate-300 dark:border-slate-600'
          )}
        >
          {quest.completed && (
            <svg className="w-4 h-4 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={clsx(
              'font-medium text-sm hover:text-sky-600 dark:hover:text-sky-400 transition-colors',
              quest.completed
                ? 'line-through text-slate-400 dark:text-slate-500'
                : 'text-slate-900 dark:text-white'
            )}
          >
            {quest.title}
          </a>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">
            {quest.reason}
          </p>
        </div>

        {/* Difficulty */}
        {quest.difficulty && <DifficultyBadge difficulty={quest.difficulty} />}
      </div>
    </div>
  )
}
