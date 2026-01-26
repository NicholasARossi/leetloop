'use client'

import type { DomainScore } from '@/lib/api'

interface DomainCardProps {
  domain: DomainScore
  onClick?: () => void
}

const statusStyles = {
  WEAK: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    badge: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
    progress: 'bg-red-500',
  },
  FAIR: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    border: 'border-yellow-200 dark:border-yellow-800',
    badge: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300',
    progress: 'bg-yellow-500',
  },
  GOOD: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    badge: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
    progress: 'bg-blue-500',
  },
  STRONG: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-200 dark:border-green-800',
    badge: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
    progress: 'bg-green-500',
  },
}

export function DomainCard({ domain, onClick }: DomainCardProps) {
  const styles = statusStyles[domain.status] || statusStyles.WEAK

  return (
    <button
      onClick={onClick}
      className={`w-full p-4 rounded-lg border ${styles.bg} ${styles.border} hover:opacity-90 transition-opacity text-left`}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-slate-900 dark:text-white text-sm">
          {domain.name}
        </h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${styles.badge}`}>
          {domain.status}
        </span>
      </div>

      <div className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
        {domain.score.toFixed(0)}%
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full transition-all duration-500 ${styles.progress}`}
          style={{ width: `${Math.min(domain.score, 100)}%` }}
        />
      </div>

      <div className="text-xs text-slate-500">
        {domain.problems_solved}/{domain.problems_attempted} problems solved
      </div>
    </button>
  )
}
