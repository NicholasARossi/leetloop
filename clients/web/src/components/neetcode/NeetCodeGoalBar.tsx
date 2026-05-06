'use client'

import { useState, useRef, useEffect } from 'react'
import type { CategoryProgress } from '@/lib/api'

interface NeetCodeGoalBarProps {
  completed: number
  total: number
  deadline: string
  categoriesProgress: Record<string, CategoryProgress>
}

const CATEGORY_ORDER = [
  'Arrays & Hashing',
  'Two Pointers',
  'Sliding Window',
  'Stack',
  'Binary Search',
  'Linked List',
  'Trees',
  'Tries',
  'Heap / Priority Queue',
  'Backtracking',
  'Graphs',
  'Advanced Graphs',
  '1-D Dynamic Programming',
  '2-D Dynamic Programming',
  'Greedy',
  'Intervals',
  'Math & Geometry',
  'Bit Manipulation',
]

const SHORT_NAMES: Record<string, string> = {
  'Arrays & Hashing': 'Arrays',
  'Two Pointers': '2Ptr',
  'Sliding Window': 'Window',
  'Binary Search': 'BinSearch',
  'Linked List': 'LinkedList',
  'Heap / Priority Queue': 'Heap',
  'Advanced Graphs': 'Adv Graph',
  '1-D Dynamic Programming': '1D DP',
  '2-D Dynamic Programming': '2D DP',
  'Math & Geometry': 'Math',
  'Bit Manipulation': 'Bits',
}

const DIFFICULTY_COLOR: Record<string, string> = {
  Easy: 'text-emerald-600',
  Medium: 'text-amber-600',
  Hard: 'text-red-600',
}

function getCategoryColor(completed: number, total: number): string {
  if (total === 0) return 'bg-gray-100 text-gray-400 border-gray-300'
  const pct = completed / total
  if (pct >= 1) return 'bg-emerald-50 text-emerald-700 border-emerald-400'
  if (pct >= 0.5) return 'bg-amber-50 text-amber-700 border-amber-400'
  if (pct > 0) return 'bg-red-50 text-red-600 border-red-300'
  return 'bg-gray-50 text-gray-500 border-gray-300'
}

function CategoryPopover({ name, cat, onClose }: { name: string; cat: CategoryProgress; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  const remaining = cat.problems.filter((p) => !p.completed)
  const done = cat.problems.filter((p) => p.completed)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div
        ref={ref}
        className="bg-white border-2 border-black shadow-lg w-full max-w-md max-h-[70vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b-2 border-black">
          <div>
            <h3 className="font-display text-base font-bold">{name}</h3>
            <p className="text-xs font-mono text-gray-500">
              {cat.completed}/{cat.total} completed
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black text-lg leading-none px-1">
            &times;
          </button>
        </div>

        {/* Problem list */}
        <div className="overflow-y-auto flex-1 divide-y divide-gray-100">
          {remaining.length > 0 && (
            <div className="px-4 py-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                Remaining ({remaining.length})
              </p>
              {remaining.map((p) => (
                <a
                  key={p.slug}
                  href={`https://leetcode.com/problems/${p.slug}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between py-1.5 group hover:bg-gray-50 -mx-2 px-2 rounded"
                >
                  <span className="text-sm group-hover:text-coral transition-colors">{p.title}</span>
                  <span className={`text-[10px] font-mono font-bold ${DIFFICULTY_COLOR[p.difficulty || ''] || 'text-gray-500'}`}>
                    {p.difficulty}
                  </span>
                </a>
              ))}
            </div>
          )}
          {done.length > 0 && (
            <div className="px-4 py-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                Completed ({done.length})
              </p>
              {done.map((p) => (
                <a
                  key={p.slug}
                  href={`https://leetcode.com/problems/${p.slug}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between py-1.5 group hover:bg-gray-50 -mx-2 px-2 rounded opacity-50"
                >
                  <span className="text-sm line-through">{p.title}</span>
                  <span className={`text-[10px] font-mono font-bold ${DIFFICULTY_COLOR[p.difficulty || ''] || 'text-gray-500'}`}>
                    {p.difficulty}
                  </span>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function NeetCodeGoalBar({ completed, total, deadline, categoriesProgress }: NeetCodeGoalBarProps) {
  const [openCategory, setOpenCategory] = useState<string | null>(null)
  const pct = total > 0 ? (completed / total) * 100 : 0
  const remaining = total - completed

  return (
    <>
      <div className="border-2 border-black bg-white p-4">
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <h2 className="font-display text-lg font-bold">NeetCode 150</h2>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-coral text-white px-2 py-0.5 border border-black">
              {deadline} Goal
            </span>
          </div>
          <span className="font-mono text-sm font-bold">
            {completed}<span className="text-gray-400">/{total}</span>
            <span className="text-gray-400 ml-2">({pct.toFixed(1)}%)</span>
          </span>
        </div>

        {/* Progress bar */}
        <div className="relative h-5 border-2 border-black bg-gray-100 mb-1">
          <div
            className="h-full bg-coral transition-all duration-700"
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
          <div className="absolute right-0 top-0 h-full w-0.5 bg-black" />
        </div>

        <p className="text-[11px] text-gray-500 font-mono mb-3">
          {remaining} problems remaining
        </p>

        {/* Category pills */}
        <div className="flex flex-wrap gap-1.5">
          {CATEGORY_ORDER.map((name) => {
            const cat = categoriesProgress[name]
            if (!cat) return null
            const shortName = SHORT_NAMES[name] || name
            const isComplete = cat.completed === cat.total
            return (
              <button
                key={name}
                onClick={() => setOpenCategory(name)}
                className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 border rounded transition-all ${getCategoryColor(cat.completed, cat.total)} ${isComplete ? 'cursor-default' : 'hover:ring-1 hover:ring-black cursor-pointer'}`}
                title={`${name}: ${cat.completed}/${cat.total} — click to see problems`}
              >
                {shortName}
                <span className="font-bold">{cat.completed}/{cat.total}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Category detail popover */}
      {openCategory && categoriesProgress[openCategory] && (
        <CategoryPopover
          name={openCategory}
          cat={categoriesProgress[openCategory]}
          onClose={() => setOpenCategory(null)}
        />
      )}
    </>
  )
}
