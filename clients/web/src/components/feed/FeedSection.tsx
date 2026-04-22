'use client'

import type { DailyFeedResponse, FeedItem } from '@/lib/api'
import { FeedProblemCard } from './FeedProblemCard'

interface FeedSectionProps {
  feed: DailyFeedResponse
  onSaveMistake?: (item: FeedItem, text: string) => Promise<void>
}

export function FeedSection({ feed, onSaveMistake }: FeedSectionProps) {
  // Sort: pending first, then completed
  const sortedItems = [...feed.items].sort((a, b) => {
    if (a.status === 'completed' && b.status !== 'completed') return 1
    if (a.status !== 'completed' && b.status === 'completed') return -1
    return a.sort_order - b.sort_order
  })

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-1">
        <h3 className="section-title !mb-0 !pb-0 !border-0">
          Today&apos;s Problems
        </h3>
        <span className="text-sm font-mono font-bold">
          {feed.completed_count}/{feed.total_count}
        </span>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Practice: {feed.practice_count} | Metric: {feed.metric_count}
      </p>

      {/* Progress bar */}
      <div className="progress-bar mb-4">
        <div
          className="progress-fill transition-all duration-500"
          style={{ width: `${feed.total_count > 0 ? Math.round((feed.completed_count / feed.total_count) * 100) : 0}%` }}
        />
      </div>

      {sortedItems.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-4">
          No problems in today&apos;s feed yet.
        </p>
      ) : (
        <div className="space-y-1">
          {sortedItems.map((item) => (
            <FeedProblemCard key={item.id} item={item} onSaveMistake={onSaveMistake} />
          ))}
        </div>
      )}
    </div>
  )
}
