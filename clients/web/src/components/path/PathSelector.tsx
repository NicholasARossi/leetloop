'use client'

import type { LearningPathSummary } from '@/lib/api'

interface PathSelectorProps {
  paths: LearningPathSummary[]
  selectedPathId: string | null
  onSelect: (pathId: string) => void
  loading?: boolean
}

export function PathSelector({ paths, selectedPathId, onSelect, loading }: PathSelectorProps) {
  return (
    <div className="relative">
      <select
        value={selectedPathId || ''}
        onChange={(e) => onSelect(e.target.value)}
        disabled={loading}
        className="input w-full sm:w-64 pr-10 appearance-none bg-white dark:bg-slate-800"
      >
        <option value="" disabled>Select a path...</option>
        {paths.map((path) => (
          <option key={path.id} value={path.id}>
            {path.name} ({path.total_problems} problems)
          </option>
        ))}
      </select>
      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
        <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  )
}
