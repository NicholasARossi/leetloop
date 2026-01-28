'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import type { LearningPathSummary } from '@/lib/api'

interface PathStepProps {
  paths: LearningPathSummary[]
  onSelect: (pathId: string) => Promise<void>
}

const pathIcons: Record<string, string> = {
  'NeetCode 150': '150',
  'Blind 75': '75',
  'Grind 75': 'G75',
  'LeetCode 75': 'LC',
}

export function PathStep({ paths, onSelect }: PathStepProps) {
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleContinue() {
    if (!selectedPathId) return

    setSaving(true)
    try {
      await onSelect(selectedPathId)
    } finally {
      setSaving(false)
    }
  }

  // Sort paths with NeetCode 150 first
  const sortedPaths = [...paths].sort((a, b) => {
    if (a.name.includes('NeetCode 150')) return -1
    if (b.name.includes('NeetCode 150')) return 1
    return a.total_problems - b.total_problems
  })

  return (
    <div>
      <h2 className="section-title mb-2">Choose Your Learning Path</h2>
      <p className="text-gray-600 mb-6">
        This is your curriculum. Gemini will use it to guide your daily missions while adapting to your skill gaps.
      </p>

      <div className="space-y-3">
        {sortedPaths.map(path => (
          <button
            key={path.id}
            onClick={() => setSelectedPathId(path.id)}
            className={clsx(
              'w-full p-4 text-left border-[2px] transition-all flex items-start gap-4',
              selectedPathId === path.id
                ? 'border-accent bg-accent/10'
                : 'border-black bg-white hover:bg-gray-50'
            )}
          >
            {/* Icon */}
            <div className={clsx(
              'w-12 h-12 flex items-center justify-center border-[2px] border-black font-bold text-sm flex-shrink-0',
              selectedPathId === path.id ? 'bg-accent text-white' : 'bg-gray-100'
            )}>
              {pathIcons[path.name] || path.total_problems}
            </div>

            {/* Info */}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="font-bold">{path.name}</h3>
                <span className="text-sm text-gray-500">
                  {path.total_problems} problems
                </span>
              </div>
              {path.description && (
                <p className="text-sm text-gray-600 mt-1">{path.description}</p>
              )}

              {/* Recommendation badge for NeetCode 150 */}
              {path.name.includes('NeetCode 150') && (
                <span className="inline-block mt-2 px-2 py-0.5 text-xs bg-accent text-white">
                  RECOMMENDED
                </span>
              )}
            </div>

            {/* Selected indicator */}
            {selectedPathId === path.id && (
              <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-gray-50 border-[2px] border-black">
        <h4 className="font-bold text-sm mb-2">How paths work with Gemini:</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>Your path sets the order of problems to learn</li>
          <li>Gemini can reorder problems to address your skill gaps</li>
          <li>Gemini may suggest problems outside your path when needed</li>
          <li>You can change your path anytime from settings</li>
        </ul>
      </div>

      {/* Action */}
      <div className="flex justify-end mt-8">
        <button
          onClick={handleContinue}
          disabled={!selectedPathId || saving}
          className={clsx(
            'btn-primary',
            (!selectedPathId || saving) && 'opacity-50 cursor-not-allowed'
          )}
        >
          {saving ? 'Starting...' : 'Start Learning'}
        </button>
      </div>
    </div>
  )
}
