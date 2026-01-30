'use client'

import { MainQuest } from '@/lib/api'
import { clsx } from 'clsx'

interface QuestItemProps {
  quest: MainQuest
  index: number
}

export function QuestItem({ quest, index }: QuestItemProps) {
  const isCompleted = quest.status === 'completed'
  const isCurrent = quest.status === 'current' || quest.status === 'active'

  const leetcodeUrl = `https://leetcode.com/problems/${quest.slug}/`

  return (
    <div
      className={clsx(
        'list-item-rect',
        isCurrent && 'active',
        isCompleted && 'completed'
      )}
    >
      <div className="flex items-center gap-4">
        {/* Status indicator */}
        {isCompleted ? (
          <div className="w-6 h-6 bg-coral flex items-center justify-center flex-shrink-0">
            <svg width="14" height="14" fill="none" stroke="white" strokeWidth="3" viewBox="0 0 24 24">
              <path d="M5 13l4 4L19 7"/>
            </svg>
          </div>
        ) : (
          <div
            className={clsx(
              'w-6 h-6 border-2 flex items-center justify-center flex-shrink-0 text-xs font-bold',
              isCurrent ? 'border-black bg-coral' : 'border-gray-400 text-gray-400'
            )}
          >
            {quest.order}
          </div>
        )}

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <span
            className={clsx(
              'font-medium text-sm',
              isCompleted && 'line-through text-gray-400',
              !isCompleted && 'text-black'
            )}
          >
            {quest.title}
          </span>
          <p className="text-gray-500 text-xs mt-1">
            {quest.category}
          </p>
        </div>

        {/* Difficulty + Action */}
        <div className="flex items-center gap-3">
          {quest.difficulty && (
            <span
              className={clsx(
                'tag-rect text-xs',
                isCompleted && 'opacity-50'
              )}
            >
              {quest.difficulty}
            </span>
          )}
          {isCurrent && (
            <a
              href={leetcodeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary text-xs py-1 px-3"
            >
              Solve
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
