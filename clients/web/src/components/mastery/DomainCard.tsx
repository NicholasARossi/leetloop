'use client'

import type { DomainScore } from '@/lib/api'

interface DomainCardProps {
  domain: DomainScore
  onClick?: () => void
}

export function DomainCard({ domain, onClick }: DomainCardProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'WEAK':
        return 'tag'
      case 'FAIR':
        return 'tag'
      case 'GOOD':
        return 'tag'
      case 'STRONG':
        return 'tag tag-accent'
      default:
        return 'tag'
    }
  }

  const isStrong = domain.status === 'STRONG' || domain.status === 'GOOD'

  return (
    <button
      onClick={onClick}
      className="list-item w-full text-left reg-corners"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`status-light ${isStrong ? 'status-light-active' : 'status-light-inactive'}`} />
          <h3 className="font-medium text-black text-sm">
            {domain.name}
          </h3>
        </div>
        <span className={getStatusBadge(domain.status)}>
          {domain.status}
        </span>
      </div>

      <div className="stat-value text-2xl mb-2">
        {domain.score.toFixed(0)}%
      </div>

      {/* Progress bar */}
      <div className="progress-bar mb-2">
        <div
          className="progress-fill transition-all duration-500"
          style={{ width: `${Math.min(domain.score, 100)}%` }}
        />
      </div>

      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          {domain.problems_solved}/{domain.problems_attempted} problems solved
        </div>
        <div className="coord-display">
          {domain.problems_solved}:{domain.problems_attempted}
        </div>
      </div>
    </button>
  )
}
