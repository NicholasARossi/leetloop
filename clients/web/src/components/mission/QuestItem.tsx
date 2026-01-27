'use client'

import { MainQuest } from '@/lib/api'
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
    <div className="list-item">
      <div className="flex items-center gap-4">
        {/* Status checkbox */}
        <div
          className={clsx(
            'checkbox',
            isCompleted && 'checked'
          )}
        />

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={clsx(
                'font-medium text-sm',
                isCompleted && 'line-through text-gray-400',
                !isCompleted && 'text-black'
              )}
            >
              {quest.title}
            </span>
            {quest.difficulty && (
              <span className="text-xs text-gray-500 uppercase">
                {quest.difficulty}
              </span>
            )}
          </div>
          <p className="text-gray-500 text-xs mt-1">
            {quest.category}
          </p>
        </div>

        {/* Action / Status */}
        {isCompleted ? (
          <span className="text-xs text-gray-500 uppercase">Done</span>
        ) : isCurrent ? (
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-xs"
          >
            Start
          </a>
        ) : null}
      </div>
    </div>
  )
}
