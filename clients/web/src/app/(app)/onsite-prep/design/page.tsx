'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { leetloopApi, type OnsitePrepQuestion } from '@/lib/api'

export default function DesignPage() {
  const [questions, setQuestions] = useState<OnsitePrepQuestion[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const data = await leetloopApi.getOnsitePrepQuestions('design')
        setQuestions(data)
      } catch (e) {
        console.error('Failed to load design questions:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-coral border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <Link href="/onsite-prep" className="text-sm text-gray-400 hover:text-gray-600">
          &larr; Dashboard
        </Link>
        <h1 className="text-xl font-semibold mt-2">System Design</h1>
        <p className="text-sm text-gray-500 mt-1">
          Longer-form practice &bull; Target: 5-8 minutes &bull; End-to-end ML system walkthrough
        </p>
      </div>

      {/* Info banner */}
      <div className="card-sm bg-coral/10 mb-5">
        <div className="text-xs text-gray-700 leading-relaxed">
          These map to the <strong>ML Application slot</strong>. The interviewer will give a broad problem and expect you to structure a solution: problem framing &rarr; data signals &rarr; architecture &rarr; training &rarr; evaluation &rarr; deployment.
        </div>
      </div>

      {/* Design problem cards */}
      <div className="space-y-4">
        {questions.map((q) => (
          <Link key={q.id} href={`/onsite-prep/practice/${q.id}`} className="card block hover:shadow-lg transition-all">
            <div className="flex items-center justify-between mb-2">
              <span className="badge badge-accent">{q.subcategory}</span>
              <span className="badge badge-default">&mdash; Not practiced</span>
            </div>
            <div className="text-base font-medium mb-2">
              &ldquo;{q.prompt_text}&rdquo;
            </div>
            {q.context_hint && (
              <div className="text-xs text-gray-500 leading-relaxed">{q.context_hint}</div>
            )}
          </Link>
        ))}
      </div>
    </div>
  )
}
