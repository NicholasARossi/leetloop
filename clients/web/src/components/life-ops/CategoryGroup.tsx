'use client'

import { ChecklistItem } from './ChecklistItem'
import type { LifeOpsDailyItem } from '@/lib/api'

interface CategoryGroupProps {
  categoryName: string
  color: string
  items: LifeOpsDailyItem[]
  onToggle: (itemId: string) => Promise<void>
}

export function CategoryGroup({ categoryName, color, items, onToggle }: CategoryGroupProps) {
  const completedCount = items.filter((i) => i.is_completed).length

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-1 px-4">
        <div
          className="w-3 h-3 rounded-full border border-gray-300"
          style={{ backgroundColor: color }}
        />
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {categoryName}
        </span>
        <span className="text-xs text-gray-400">
          {completedCount}/{items.length}
        </span>
      </div>
      <div>
        {items.map((item) => (
          <ChecklistItem
            key={item.id}
            id={item.id}
            title={item.task_title}
            isCompleted={item.is_completed}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  )
}
