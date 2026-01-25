'use client'

import { clsx } from 'clsx'

interface DifficultyBadgeProps {
  difficulty: 'Easy' | 'Medium' | 'Hard' | string
  className?: string
}

export function DifficultyBadge({ difficulty, className }: DifficultyBadgeProps) {
  return (
    <span
      className={clsx(
        className,
        difficulty === 'Easy' && 'badge-easy',
        difficulty === 'Medium' && 'badge-medium',
        difficulty === 'Hard' && 'badge-hard'
      )}
    >
      {difficulty}
    </span>
  )
}
