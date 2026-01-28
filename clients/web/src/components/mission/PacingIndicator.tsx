'use client'

import { clsx } from 'clsx'

interface PacingIndicatorProps {
  status?: string
  note?: string
}

const statusConfig: Record<string, { label: string; color: string; icon: string }> = {
  ahead: {
    label: 'Ahead',
    color: 'bg-green-100 text-green-700 border-green-300',
    icon: 'M5 10l7-7m0 0l7 7m-7-7v18',
  },
  on_track: {
    label: 'On Track',
    color: 'bg-blue-100 text-blue-700 border-blue-300',
    icon: 'M5 13l4 4L19 7',
  },
  behind: {
    label: 'Behind',
    color: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  },
  critical: {
    label: 'Critical',
    color: 'bg-red-100 text-red-700 border-red-300',
    icon: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
}

export function PacingIndicator({ status, note }: PacingIndicatorProps) {
  if (!status) return null

  const config = statusConfig[status] || statusConfig.on_track

  return (
    <div className={clsx('inline-flex items-center gap-2 px-3 py-1.5 border-[2px] text-sm', config.color)}>
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
      </svg>
      <span className="font-bold">{config.label}</span>
      {note && <span className="text-xs opacity-75 hidden sm:inline">- {note}</span>}
    </div>
  )
}
