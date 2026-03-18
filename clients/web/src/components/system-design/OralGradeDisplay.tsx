'use client'

import { useState } from 'react'
import type { OralGradeResult, OralFollowUpResponse } from '@/lib/api'
import { FollowUpRecorder } from './FollowUpRecorder'

interface OralGradeDisplayProps {
  grade: OralGradeResult
  questionId?: string
  followUpResponses?: OralFollowUpResponse[]
}

const DIMENSION_LABELS: Record<string, string> = {
  technical_depth: 'Technical Depth',
  structure_and_approach: 'Structure & Approach',
  tradeoff_reasoning: 'Trade-off Reasoning',
  ml_data_fluency: 'ML/Data Fluency',
  communication_quality: 'Communication',
}

function getScoreColor(score: number): string {
  if (score >= 7) return 'bg-coral'
  if (score >= 5) return 'bg-yellow-400'
  return 'bg-gray-400'
}

function getVerdictBadge(verdict: string) {
  switch (verdict) {
    case 'pass':
      return <span className="badge-accepted font-mono text-xs uppercase">Pass</span>
    case 'borderline':
      return <span className="badge-medium font-mono text-xs uppercase">Borderline</span>
    case 'fail':
      return <span className="badge-failed font-mono text-xs uppercase">Fail</span>
    default:
      return null
  }
}

export function OralGradeDisplay({ grade, questionId, followUpResponses }: OralGradeDisplayProps) {
  const [showTranscript, setShowTranscript] = useState(true)
  const [expandedDimensions, setExpandedDimensions] = useState<Set<string>>(new Set())

  const toggleDimension = (name: string) => {
    setExpandedDimensions(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div className="space-y-6">
      {/* Overall score + verdict */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-baseline gap-3">
            <span className="stat-value text-4xl">{grade.overall_score}</span>
            <span className="stat-label">/10</span>
          </div>
          {getVerdictBadge(grade.verdict)}
        </div>
        <p className="text-sm text-gray-700 font-mono">{grade.feedback}</p>
      </div>

      {/* Dimension scores */}
      <div className="card">
        <h3 className="section-title text-sm">Dimension Scores</h3>
        <div className="space-y-3">
          {grade.dimensions.map((dim) => (
            <div key={dim.name}>
              <button
                onClick={() => toggleDimension(dim.name)}
                className="w-full text-left"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono uppercase text-gray-600">
                    {DIMENSION_LABELS[dim.name] || dim.name}
                  </span>
                  <span className="text-xs font-mono font-bold">
                    {dim.score}/10
                  </span>
                </div>
                <div className="w-full h-3 bg-gray-100 border border-black" style={{ clipPath: 'polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px)' }}>
                  <div
                    className={`h-full ${getScoreColor(dim.score)} transition-all`}
                    style={{ width: `${dim.score * 10}%` }}
                  />
                </div>
              </button>

              {/* Evidence (expanded) */}
              {expandedDimensions.has(dim.name) && (
                <div className="mt-2 ml-2 pl-3 border-l-2 border-gray-200 space-y-2">
                  <p className="text-xs text-gray-500 font-mono">{dim.summary}</p>
                  {dim.evidence.map((ev, i) => (
                    <div key={i} className="text-xs space-y-1">
                      <p className="text-gray-700 italic font-mono">
                        &ldquo;{ev.quote}&rdquo;
                      </p>
                      <p className="text-gray-500">{ev.analysis}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Strongest / Weakest moments */}
      {(grade.strongest_moment || grade.weakest_moment) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {grade.strongest_moment && (
            <div className="card-sm border-l-4" style={{ borderLeftColor: 'var(--accent-color)' }}>
              <span className="text-xs font-mono uppercase text-gray-400">Strongest Moment</span>
              <p className="text-sm font-mono text-gray-700 mt-1 italic">
                &ldquo;{grade.strongest_moment}&rdquo;
              </p>
            </div>
          )}
          {grade.weakest_moment && (
            <div className="card-sm border-l-4 border-l-gray-400">
              <span className="text-xs font-mono uppercase text-gray-400">Weakest Moment</span>
              <p className="text-sm font-mono text-gray-700 mt-1">
                {grade.weakest_moment}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Missed concepts */}
      {grade.missed_concepts.length > 0 && (
        <div className="card-sm">
          <span className="text-xs font-mono uppercase text-gray-400">Missed Concepts</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {grade.missed_concepts.map((concept, i) => (
              <span key={i} className="tag">{concept}</span>
            ))}
          </div>
        </div>
      )}

      {/* Follow-up questions */}
      {grade.follow_up_questions.length > 0 && (
        <div className="card-sm">
          <span className="text-xs font-mono uppercase text-gray-400">Follow-up Questions</span>
          <div className="mt-3 space-y-4">
            {grade.follow_up_questions.map((q, i) => (
              questionId ? (
                <FollowUpRecorder
                  key={i}
                  questionId={questionId}
                  followUpIndex={i}
                  followUpText={q}
                  existingResponse={followUpResponses?.find(r => r.follow_up_index === i)}
                />
              ) : (
                <div key={i} className="text-sm font-mono text-gray-700 pl-4 relative">
                  <span className="absolute left-0 text-coral">{i + 1}.</span>
                  {q}
                </div>
              )
            ))}
          </div>
        </div>
      )}

      {/* Transcript */}
      <div className="card-sm">
        <button
          onClick={() => setShowTranscript(!showTranscript)}
          className="flex items-center justify-between w-full"
        >
          <span className="text-xs font-mono uppercase text-gray-400">Transcript</span>
          <span className="text-xs text-gray-400">{showTranscript ? '−' : '+'}</span>
        </button>
        {showTranscript && (
          <p className="text-sm text-gray-600 mt-3 leading-relaxed whitespace-pre-wrap font-mono">
            {grade.transcript}
          </p>
        )}
      </div>
    </div>
  )
}
