'use client'

import Link from 'next/link'
import { clsx } from 'clsx'
import type { MLCodingDashboardSummary } from '@/lib/api'

interface MLCodingDashboardCardProps {
  data: MLCodingDashboardSummary
}

export function MLCodingDashboardCard({ data }: MLCodingDashboardCardProps) {
  const progressPct = data.problems_total > 0
    ? Math.round((data.problems_attempted / data.problems_total) * 100)
    : 0

  return (
    <div className="card border-coral bg-gradient-to-br from-white to-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-coral rounded flex items-center justify-center">
            <span className="text-white text-xs font-bold">ML</span>
          </div>
          <span className="font-semibold text-sm text-gray-700">ML Coding Drills</span>
        </div>
        {data.reviews_due_count > 0 && (
          <span className="inline-flex items-center gap-1 bg-gray-100 border border-gray-400 px-2 py-1 text-[11px] text-gray-700">
            {data.reviews_due_count} review{data.reviews_due_count !== 1 ? 's' : ''} due
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-[11px] text-gray-500 mb-1">
          <span>Problems covered</span>
          <span className="font-mono">{data.problems_attempted}/{data.problems_total}</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded">
          <div
            className="h-1.5 bg-coral rounded transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-gray-50 p-2 text-center">
          <p className="font-mono font-bold text-sm text-black">
            {data.today_completed_count}/{data.today_exercise_count || '\u2014'}
          </p>
          <p className="text-[10px] text-gray-500">Today</p>
        </div>
        <div className="bg-gray-50 p-2 text-center">
          <p className={clsx(
            'font-mono font-bold text-sm',
            data.average_score != null && data.average_score >= 7 ? 'text-coral' : 'text-black'
          )}>
            {data.average_score != null ? data.average_score.toFixed(1) : '\u2014'}
          </p>
          <p className="text-[10px] text-gray-500">Avg Score</p>
        </div>
        <div className="bg-gray-50 p-2 text-center">
          <p className="font-mono font-bold text-sm text-black">
            {data.reviews_due_count}
          </p>
          <p className="text-[10px] text-gray-500">Reviews</p>
        </div>
      </div>

      {/* CTA */}
      <Link
        href="/ml-coding"
        className="w-full flex items-center justify-between p-3 bg-white border-2 border-gray-200 hover:border-coral transition-all hover:translate-x-1"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-coral/10 border-2 border-coral flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-coral" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <div>
            <div className="font-semibold text-sm">Start Coding</div>
            <div className="text-[11px] text-gray-400">
              {data.today_exercise_count > 0
                ? `${data.today_exercise_count - data.today_completed_count} problem${data.today_exercise_count - data.today_completed_count !== 1 ? 's' : ''} waiting`
                : 'Generate today\'s problems'}
            </div>
          </div>
        </div>
        <span className="bg-coral text-white px-3 py-1.5 text-xs font-semibold flex-shrink-0">Go</span>
      </Link>

      {/* Link to full page */}
      <div className="mt-3 text-right">
        <Link href="/ml-coding" className="text-xs text-coral hover:text-coral-dark hover:underline">
          View all problems &rarr;
        </Link>
      </div>
    </div>
  )
}
