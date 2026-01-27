'use client'

import { SideQuest } from '@/lib/api'
import { clsx } from 'clsx'

interface SideQuestCardProps {
  quest: SideQuest
}

const questTypeLabels: Record<string, string> = {
  review_due: 'Review',
  skill_gap: 'Skill Gap',
  slow_solve: 'Practice',
}

export function SideQuestCard({ quest }: SideQuestCardProps) {
  const leetcodeUrl = `https://leetcode.com/problems/${quest.slug}/`
  const typeLabel = questTypeLabels[quest.quest_type] || 'Side Quest'

  return (
    <div className={clsx('list-item', quest.completed && 'opacity-60')}>
      <div className="flex items-center gap-4">
        {/* Checkbox */}
        <div
          className={clsx(
            'checkbox',
            quest.completed && 'checked'
          )}
        />

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500 uppercase">{typeLabel}</span>
            {quest.difficulty && (
              <span className="text-xs text-gray-400">· {quest.difficulty}</span>
            )}
          </div>
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={clsx(
              'font-medium text-sm hover:underline',
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
