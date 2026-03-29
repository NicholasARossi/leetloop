'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { leetloopApi, type OnsitePrepQuestion } from '@/lib/api'

const CATEGORY_LABELS: Record<string, string> = {
  lp: 'LP Stories',
  breadth: 'ML Breadth',
  depth: 'ML Depth',
  design: 'System Design',
}

const CATEGORY_BADGES: Record<string, string> = {
  lp: 'Behavioral',
  breadth: 'General ML',
  depth: 'Your Projects',
  design: 'Application',
}

interface QuestionListProps {
  category: string
}

export function QuestionList({ category }: QuestionListProps) {
  const [questions, setQuestions] = useState<OnsitePrepQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'by-sub'>('all')

  useEffect(() => {
    async function load() {
      try {
        const data = await leetloopApi.getOnsitePrepQuestions(category)
        setQuestions(data)
      } catch (e) {
        console.error('Failed to load questions:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [category])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-coral border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // Group by subcategory
  const grouped = questions.reduce<Record<string, OnsitePrepQuestion[]>>((acc, q) => {
    const key = q.subcategory || 'General'
    if (!acc[key]) acc[key] = []
    acc[key].push(q)
    return acc
  }, {})

  return (
    <div>
      <div className="mb-6">
        <Link href="/onsite-prep" className="text-sm text-gray-400 hover:text-gray-600">
          &larr; Dashboard
        </Link>
        <h1 className="text-xl font-semibold mt-2">{CATEGORY_LABELS[category] || category}</h1>
        <p className="text-sm text-gray-500 mt-1">
          {questions.length} questions &bull; <span className="badge badge-default">{CATEGORY_BADGES[category]}</span>
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 border-b-2 border-gray-200">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 text-xs uppercase tracking-wide border-b-2 -mb-[2px] ${
            filter === 'all' ? 'border-coral text-gray-900' : 'border-transparent text-gray-400'
          }`}
        >
          All ({questions.length})
        </button>
        <button
          onClick={() => setFilter('by-sub')}
          className={`px-4 py-2 text-xs uppercase tracking-wide border-b-2 -mb-[2px] ${
            filter === 'by-sub' ? 'border-coral text-gray-900' : 'border-transparent text-gray-400'
          }`}
        >
          By Topic
        </button>
      </div>

      {/* Question list */}
      <div className="card">
        {Object.entries(grouped).map(([subcategory, subQuestions]) => (
          <div key={subcategory} className="mb-6 last:mb-0">
            {filter === 'by-sub' && (
              <div className="section-title">{subcategory}</div>
            )}
            {subQuestions.map((q) => (
              <Link
                key={q.id}
                href={`/onsite-prep/practice/${q.id}`}
                className="flex items-start gap-3 px-4 py-3 border-l-4 border-transparent hover:border-coral hover:bg-gray-50 transition-all"
              >
                <span className="badge badge-default flex-shrink-0 mt-0.5">&mdash;</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm">{q.prompt_text}</div>
                  {q.context_hint && (
                    <div className="text-xs text-gray-400 mt-1 truncate">
                      {q.subcategory && <span className="font-medium">{q.subcategory}</span>}
                      {q.subcategory && ' \u2022 '}
                      {q.context_hint}
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {Math.floor(q.target_duration_seconds / 60)}:{(q.target_duration_seconds % 60).toString().padStart(2, '0')}
                </span>
              </Link>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
