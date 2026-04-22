'use client'

import { useMemo } from 'react'
import { ProgressHeader } from './ProgressHeader'
import { CategoryGroup } from './CategoryGroup'
import type { LifeOpsDailyItem } from '@/lib/api'

interface ChecklistViewProps {
  items: LifeOpsDailyItem[]
  completedCount: number
  totalCount: number
  currentStreak: number
  onToggle: (itemId: string) => Promise<void>
}

export function ChecklistView({
  items,
  completedCount,
  totalCount,
  currentStreak,
  onToggle,
}: ChecklistViewProps) {
  // Group items by category
  const groups = useMemo(() => {
    const map = new Map<string, { name: string; color: string; items: LifeOpsDailyItem[] }>()

    for (const item of items) {
      const key = item.category_id || 'uncategorized'
      if (!map.has(key)) {
        map.set(key, {
          name: item.category_name || 'Uncategorized',
          color: '#6B7280',
          items: [],
        })
      }
      map.get(key)!.items.push(item)
    }

    return Array.from(map.values())
  }, [items])

  if (totalCount === 0) {
    return (
      <div className="card text-center py-12">
        <div className="text-4xl mb-3">
          <svg className="w-12 h-12 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <p className="text-gray-500 text-sm font-medium">No tasks for today</p>
        <p className="text-gray-400 text-xs mt-1">
          Set up your recurring tasks in Manage Tasks to get started.
        </p>
      </div>
    )
  }

  return (
    <div>
      <ProgressHeader
        completedCount={completedCount}
        totalCount={totalCount}
        currentStreak={currentStreak}
      />

      <div className="card">
        {groups.map((group) => (
          <CategoryGroup
            key={group.name}
            categoryName={group.name}
            color={group.color}
            items={group.items}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  )
}
