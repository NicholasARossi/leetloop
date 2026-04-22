'use client'

import { useState } from 'react'

interface ChecklistItemProps {
  id: string
  title: string
  isCompleted: boolean
  onToggle: (itemId: string) => Promise<void>
}

export function ChecklistItem({ id, title, isCompleted, onToggle }: ChecklistItemProps) {
  const [toggling, setToggling] = useState(false)
  const [optimisticCompleted, setOptimisticCompleted] = useState(isCompleted)

  async function handleToggle() {
    if (toggling) return
    setToggling(true)
    setOptimisticCompleted(!optimisticCompleted)
    try {
      await onToggle(id)
    } catch {
      setOptimisticCompleted(optimisticCompleted) // revert
    } finally {
      setToggling(false)
    }
  }

  return (
    <button
      onClick={handleToggle}
      disabled={toggling}
      className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-md group"
    >
      <div
        className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all ${
          optimisticCompleted
            ? 'bg-green-500 border-green-500'
            : 'border-gray-300 group-hover:border-gray-400'
        }`}
      >
        {optimisticCompleted && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <span
        className={`text-sm transition-all ${
          optimisticCompleted ? 'text-gray-400 line-through' : 'text-gray-900'
        }`}
      >
        {title}
      </span>
    </button>
  )
}
