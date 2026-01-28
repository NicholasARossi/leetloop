'use client'

import type { DomainDetailResponse } from '@/lib/api'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'
import { StatusBadge } from '@/components/ui/StatusBadge'

interface DomainDetailProps {
  data: DomainDetailResponse
  onClose: () => void
}

export function DomainDetail({ data, onClose }: DomainDetailProps) {
  const { domain, failure_analysis, recommended_path, recent_submissions } = data

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card max-w-2xl w-full max-h-[90vh] overflow-y-auto p-0">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b-2 border-black px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-display text-black">
              {domain.name}
            </h2>
            <p className="text-sm text-gray-500">
              Score: {domain.score.toFixed(0)}% ({domain.status})
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 border-2 border-black transition-colors"
          >
            <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Sub-patterns */}
          {domain.sub_patterns.length > 0 && (
            <div>
              <h3 className="section-title">
                Sub-patterns
              </h3>
              <div className="space-y-2">
                {domain.sub_patterns.map((pattern) => (
                  <div
                    key={pattern.name}
                    className="flex items-center justify-between p-3 bg-gray-50 border-2 border-gray-300"
                  >
                    <span className="text-gray-700">
                      {pattern.name}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-500">
                        {pattern.attempted} attempted
                      </span>
                      <span className="font-medium text-black">
                        {pattern.score.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Failure Analysis */}
          {failure_analysis && (
            <div>
              <h3 className="section-title">
                Failure Analysis
              </h3>
              <div className="p-4 bg-gray-100 border-2 border-black">
                <p className="text-gray-700">
                  {failure_analysis}
                </p>
              </div>
            </div>
          )}

          {/* Recommended Path */}
          {recommended_path.length > 0 && (
            <div>
              <h3 className="section-title">
                Recommended Practice Path
              </h3>
              <div className="space-y-2">
                {recommended_path.map((problem, idx) => (
                  <a
                    key={problem.slug}
                    href={`https://leetcode.com/problems/${problem.slug}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 bg-white border-2 border-gray-300 hover:border-black hover:bg-gray-50 transition-colors"
                  >
                    <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-coral border-2 border-black text-black text-sm font-medium">
                      {idx + 1}
                    </span>
                    <span className="flex-1 text-gray-700">
                      {problem.title}
                    </span>
                    <DifficultyBadge difficulty={problem.difficulty} />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Recent Submissions */}
          {recent_submissions.length > 0 && (
            <div>
              <h3 className="section-title">
                Recent Submissions
              </h3>
              <div className="space-y-2">
                {recent_submissions.slice(0, 5).map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center justify-between p-3 bg-gray-50 border-2 border-gray-300"
                  >
                    <span className="text-gray-700 truncate">
                      {sub.problem_title}
                    </span>
                    <StatusBadge status={sub.status} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
