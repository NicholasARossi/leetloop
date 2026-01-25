'use client'

import { clsx } from 'clsx'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const isAccepted = status === 'Accepted'

  return (
    <span
      className={clsx(
        className,
        isAccepted ? 'badge-accepted' : 'badge-failed'
      )}
    >
      {status}
    </span>
  )
}
