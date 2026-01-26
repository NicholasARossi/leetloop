'use client'

import type { DomainDetailResponse } from '@/lib/api'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'

interface DomainDetailProps {
  data: DomainDetailResponse
  onClose: () => void
}

export function DomainDetail({ data, onClose }: DomainDetailProps) {
  const { domain, failure_analysis, recommended_path, recent_submissions } = data

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              {domain.name}
            </h2>
            <p className="text-sm text-slate-500">
              Score: {domain.score.toFixed(0)}% ({domain.status})
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
          >
            <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Sub-patterns */}
          {domain.sub_patterns.length > 0 && (
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                Sub-patterns
              </h3>
              <div className="space-y-2">
                {domain.sub_patterns.map((pattern) => (
                  <div
                    key={pattern.name}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                  >
                    <span className="text-slate-700 dark:text-slate-300">
                      {pattern.name}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-slate-500">
                        {pattern.attempted} attempted
                      </span>
                      <span className={`font-medium ${
                        pattern.score >= 70 ? 'text-green-600 dark:text-green-400' :
                        pattern.score >= 40 ? 'text-yellow-600 dark:text-yellow-400' :
                        'text-red-600 dark:text-red-400'
                      }`}>
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
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                Failure Analysis
              </h3>
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-800 dark:text-red-200">
                  {failure_analysis}
                </p>
              </div>
            </div>
          )}

          {/* Recommended Path */}
          {recommended_path.length > 0 && (
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                Recommended Practice Path
              </h3>
              <div className="space-y-2">
                {recommended_path.map((problem, idx) => (
                  <a
                    key={problem.slug}
                    href={`https://leetcode.com/problems/${problem.slug}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  >
                    <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 rounded-full text-sm font-medium">
                      {idx + 1}
                    </span>
                    <span className="flex-1 text-slate-700 dark:text-slate-300">
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
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                Recent Submissions
              </h3>
              <div className="space-y-2">
                {recent_submissions.slice(0, 5).map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                  >
                    <span className="text-slate-700 dark:text-slate-300 truncate">
                      {sub.problem_title}
                    </span>
                    <span className={`text-sm font-medium ${
                      sub.status === 'Accepted'
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      {sub.status}
                    </span>
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
