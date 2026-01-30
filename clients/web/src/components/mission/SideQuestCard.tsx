'use client'

import { SideQuest } from '@/lib/api'
import { clsx } from 'clsx'

interface SideQuestCardProps {
  quest: SideQuest
}

const questTypeLabels: Record<string, string> = {
  review_due: 'Review Due',
  skill_gap: 'Skill Gap',
  slow_solve: 'Slow Solve',
}

const questTypeIndicators: Record<string, string> = {
  review_due: 'quest-indicator-review',
  skill_gap: 'quest-indicator-gap',
  slow_solve: 'quest-indicator-slow',
}

export function SideQuestCard({ quest }: SideQuestCardProps) {
  const leetcodeUrl = `https://leetcode.com/problems/${quest.slug}/`
  const typeLabel = questTypeLabels[quest.quest_type] || 'Side Quest'
  const indicatorClass = questTypeIndicators[quest.quest_type] || 'quest-indicator-slow'

  return (
    <div className={clsx('card-sm mb-3', quest.completed && 'opacity-60')}>
      <div className="flex items-start gap-3">
        {/* Type indicator dot */}
        <div className={clsx('quest-indicator mt-1', indicatorClass)} />

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-1">
            {typeLabel}
          </p>
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={clsx(
              'font-medium text-sm hover:underline block',
              quest.completed ? 'line-through text-gray-400' : 'text-black'
            )}
          >
            {quest.title}
          </a>
          <p className="text-gray-500 text-xs mt-1">
            {quest.reason}
          </p>
        </div>
      </div>
    </div>
  )
}
