'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { clsx } from 'clsx'
import { leetloopApi, type OralSession, type OralGradeResult } from '@/lib/api'
import { OralGradeDisplay } from '@/components/system-design'

export default function SessionDetailPage() {
  const params = useParams()
  const sessionId = params.id as string

  const [session, setSession] = useState<OralSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set([0, 1, 2]))

  useEffect(() => {
    async function load() {
      try {
        const data = await leetloopApi.getOralSession(sessionId)
        setSession(data)
      } catch {
        setError('Failed to load session.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [sessionId])

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case 'pass': return 'tag-accent'
      case 'borderline': return ''
      case 'fail': return 'bg-gray-200 text-black'
      default: return ''
    }
  }

  const toggleQuestion = (idx: number) => {
    setExpandedQuestions(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  // Compute dimension averages across all graded questions
  const computeDimensionAverages = (): Record<string, number> => {
    if (!session) return {}
    const totals: Record<string, number[]> = {}
    for (const q of session.questions) {
      if (q.status === 'graded' && q.dimension_scores) {
        for (const dim of q.dimension_scores) {
          if (!totals[dim.name]) totals[dim.name] = []
          totals[dim.name].push(dim.score)
        }
      }
    }
    const avgs: Record<string, number> = {}
    for (const [name, scores] of Object.entries(totals)) {
      avgs[name] = Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
    }
    return avgs
  }

  // Build OralGradeResult from a graded OralSubQuestion
  const buildGradeResult = (q: OralSession['questions'][0]): OralGradeResult | null => {
    if (q.status !== 'graded' || !q.dimension_scores) return null
    return {
      transcript: q.transcript || '',
      dimensions: q.dimension_scores,
      overall_score: q.overall_score || 0,
      verdict: (q.verdict || 'fail') as 'pass' | 'borderline' | 'fail',
      feedback: q.feedback || '',
      missed_concepts: q.missed_concepts || [],
      strongest_moment: q.strongest_moment || '',
      weakest_moment: q.weakest_moment || '',
      follow_up_questions: q.follow_up_questions || [],
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading session...</div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error || 'Session not found'}</p>
        <Link href="/dashboard" className="text-sm text-coral hover:underline">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  const gradedQuestions = session.questions.filter(q => q.status === 'graded')
  const dimensionAverages = computeDimensionAverages()
  const overallScore = gradedQuestions.length > 0
    ? Math.round(
        (gradedQuestions.reduce((sum, q) => sum + (q.overall_score || 0), 0) / gradedQuestions.length) * 10
      ) / 10
    : null

  const DIMENSION_LABELS: Record<string, string> = {
    technical_depth: 'Technical Depth',
    structure_and_approach: 'Structure & Approach',
    tradeoff_reasoning: 'Trade-off Reasoning',
    ml_data_fluency: 'ML/Data Fluency',
    communication_quality: 'Communication',
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
        &larr; Back to Dashboard
      </Link>

      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="heading-accent text-lg">{session.topic}</h1>
            <p className="text-xs text-gray-400 font-mono mt-1">
              {new Date(session.created_at).toLocaleDateString('en-US', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
              })}
              {' '}&bull; {gradedQuestions.length}/{session.questions.length} questions graded
            </p>
          </div>
          {overallScore !== null && (
            <div className="text-right">
              <div className={clsx('stat-value text-3xl', getScoreColor(overallScore))}>
                {overallScore}
              </div>
              <span className="text-xs text-gray-400">/10</span>
              {session.status === 'completed' && (
                <div className="mt-1">
                  <span className={clsx(
                    'tag text-[10px] uppercase',
                    getVerdictStyle(overallScore >= 7 ? 'pass' : overallScore >= 5 ? 'borderline' : 'fail')
                  )}>
                    {overallScore >= 7 ? 'pass' : overallScore >= 5 ? 'borderline' : 'fail'}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Scenario */}
        <div className="p-3 bg-gray-50 border-l-4 border-black text-sm text-gray-700 leading-relaxed">
          {session.scenario}
        </div>
      </div>

      {/* Dimension Averages */}
      {Object.keys(dimensionAverages).length > 0 && (
        <div className="card">
          <h2 className="section-title text-sm mb-3">Dimension Averages</h2>
          <div className="space-y-2">
            {Object.entries(dimensionAverages).map(([name, avg]) => (
              <div key={name} className="flex items-center gap-3">
                <span className="text-xs font-mono uppercase text-gray-600 w-40 truncate">
                  {DIMENSION_LABELS[name] || name.replace(/_/g, ' ')}
                </span>
                <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
                  <div
                    className={clsx('h-2 rounded', avg >= 7 ? 'bg-coral' : avg >= 5 ? 'bg-gray-400' : 'bg-black')}
                    style={{ width: `${(avg / 10) * 100}%` }}
                  />
                </div>
                <span className={clsx('text-sm font-mono font-bold w-12 text-right', getScoreColor(avg))}>
                  {avg}/10
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Questions */}
      {session.questions.map((q, i) => {
        const isExpanded = expandedQuestions.has(i)
        const gradeResult = buildGradeResult(q)

        return (
          <div key={q.id} id={`q${i}`} className="space-y-2">
            {/* Question header */}
            <button
              onClick={() => toggleQuestion(i)}
              className="card w-full text-left flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'w-8 h-8 flex items-center justify-center text-xs font-mono font-bold border-2 flex-shrink-0',
                  q.status === 'graded'
                    ? 'bg-coral border-black text-black'
                    : 'bg-gray-100 border-gray-300 text-gray-400'
                )} style={{ clipPath: 'polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px)' }}>
                  {q.status === 'graded' ? (q.overall_score ? Math.round(q.overall_score) : '\u2713') : (i + 1)}
                </div>
                <div>
                  <span className="text-sm font-mono uppercase font-semibold">
                    Q{i + 1}: {q.focus_area}
                  </span>
                  {q.status === 'graded' && q.overall_score && (
                    <span className={clsx('ml-2 text-sm font-mono', getScoreColor(q.overall_score))}>
                      {q.overall_score.toFixed(1)}/10
                    </span>
                  )}
                </div>
              </div>
              <svg className={clsx('w-5 h-5 text-gray-400 transition-transform', isExpanded && 'rotate-180')} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Expanded content */}
            {isExpanded && (
              <div className="pl-2">
                {/* Question text */}
                <div className="p-4 bg-gray-50 border-l-4 border-black mb-4">
                  <p className="text-sm leading-relaxed">{q.question_text}</p>
                </div>

                {/* Key concepts */}
                <div className="mb-4">
                  <div className="flex flex-wrap gap-1">
                    {q.key_concepts.map((concept, ci) => (
                      <span key={ci} className="tag text-xs">{concept}</span>
                    ))}
                  </div>
                </div>

                {q.status === 'graded' && gradeResult ? (
                  <OralGradeDisplay grade={gradeResult} />
                ) : (
                  <div className="card-sm text-center py-6">
                    <p className="text-gray-400 text-sm mb-3">Not yet answered</p>
                    <Link
                      href={`/system-design?session=${session.id}&q=${i}`}
                      className="btn-primary px-4 py-1.5 text-sm inline-block"
                    >
                      Record Answer
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}

      {/* Bottom nav */}
      <div className="flex justify-center">
        <Link href="/dashboard" className="btn-secondary px-6 py-2">
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
