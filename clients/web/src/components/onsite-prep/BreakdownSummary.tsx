'use client'

import { useState } from 'react'
import type { OnsitePrepPhaseSubmission, OnsitePrepDesignPhase } from '@/lib/api'

interface BreakdownSummaryProps {
  phases: OnsitePrepDesignPhase[]
  submissions: OnsitePrepPhaseSubmission[]
  overallScore: number
  overallVerdict: string
  onBack: () => void
}

const DIMENSION_LABELS: Record<string, string> = {
  scope_clarity: 'Scope Clarity',
  constraint_identification: 'Constraints',
  metric_selection: 'Metric Selection',
  metric_tradeoffs: 'Metric Tradeoffs',
  business_alignment: 'Business Alignment',
  component_design: 'Component Design',
  data_flow_clarity: 'Data Flow',
  data_strategy: 'Data Strategy',
  feature_engineering: 'Feature Engineering',
  data_quality: 'Data Quality',
  model_choice_justification: 'Model Choice',
  training_strategy: 'Training Strategy',
  technical_depth: 'Technical Depth',
  serving_architecture: 'Serving Architecture',
  latency_awareness: 'Latency Awareness',
  scalability: 'Scalability',
  eval_strategy: 'Evaluation Strategy',
  monitoring_plan: 'Monitoring Plan',
  iteration_approach: 'Iteration Approach',
}

function getScoreColor(score: number): string {
  if (score >= 4) return 'text-green-600'
  if (score >= 3) return 'text-yellow-600'
  return 'text-red-500'
}

function getVerdictBadge(verdict: string): string {
  switch (verdict) {
    case 'pass': return 'badge-pass'
    case 'borderline': return 'badge-warn'
    case 'fail': return 'badge-fail'
    default: return 'badge-default'
  }
}

function getVerdictLabel(verdict: string): string {
  switch (verdict) {
    case 'pass': return 'Strong'
    case 'borderline': return 'Needs Polish'
    case 'fail': return 'Needs Work'
    default: return verdict
  }
}

export function BreakdownSummary({ phases, submissions, overallScore, overallVerdict, onBack }: BreakdownSummaryProps) {
  const [expandedPhase, setExpandedPhase] = useState<number | null>(null)

  return (
    <div>
      {/* Overall Score */}
      <div className="card text-center">
        <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">
          Breakdown Complete
        </div>
        <div className="text-4xl font-semibold">
          {overallScore}
          <span className="text-base text-gray-400"> / 5</span>
        </div>
        <div className="mt-2">
          <span className={`badge ${getVerdictBadge(overallVerdict)}`}>
            {getVerdictLabel(overallVerdict)}
          </span>
        </div>
        <div className="text-[10px] text-gray-400 mt-2">
          Weighted: Phases 3-5 (Architecture, Data, Model) count 2x
        </div>
      </div>

      {/* Per-Phase Breakdown */}
      <div className="card">
        <div className="text-[10px] uppercase tracking-widest text-gray-500 font-semibold mb-3">
          Phase-by-Phase Results
        </div>
        <div className="space-y-2">
          {phases.map((phase, i) => {
            const phaseNum = i + 1
            const sub = submissions.find(s => s.phase_number === phaseNum)
            const isExpanded = expandedPhase === phaseNum

            return (
              <div key={i} className="border border-gray-100 rounded-lg">
                <button
                  onClick={() => setExpandedPhase(isExpanded ? null : phaseNum)}
                  className="w-full flex items-center gap-3 p-3 text-left hover:bg-gray-50 transition-colors"
                >
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    sub?.overall_score != null && sub.overall_score >= 4 ? 'bg-green-100 text-green-700' :
                    sub?.overall_score != null && sub.overall_score >= 3 ? 'bg-yellow-100 text-yellow-700' :
                    sub?.overall_score != null ? 'bg-red-100 text-red-600' :
                    'bg-gray-100 text-gray-400'
                  }`}>
                    {sub?.overall_score?.toFixed(1) ?? '—'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-gray-700">{phase.name}</div>
                    {sub?.feedback && (
                      <div className="text-[10px] text-gray-400 truncate">{sub.feedback}</div>
                    )}
                  </div>
                  <div className="text-gray-400 text-xs">{isExpanded ? '\u25B2' : '\u25BC'}</div>
                </button>

                {isExpanded && sub && (
                  <div className="px-3 pb-3 border-t border-gray-100">
                    {/* Dimension scores */}
                    {sub.dimensions && (
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        {sub.dimensions.map((dim) => (
                          <div key={dim.name} className="flex items-center justify-between text-xs">
                            <span className="text-gray-500">{DIMENSION_LABELS[dim.name] || dim.name}</span>
                            <span className={`font-semibold ${getScoreColor(dim.score)}`}>{dim.score}/5</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Feedback */}
                    {sub.feedback && (
                      <div className="bg-gray-50 border-l-[3px] border-coral/30 p-2 mt-2 text-xs text-gray-600 leading-relaxed">
                        {sub.feedback}
                      </div>
                    )}

                    {/* Transcript snippet */}
                    {sub.transcript && (
                      <div className="mt-2">
                        <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">Transcript</div>
                        <div className="text-[10px] text-gray-500 max-h-20 overflow-y-auto">
                          {sub.transcript.slice(0, 500)}{sub.transcript.length > 500 ? '...' : ''}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="flex gap-3 mt-4">
        <button onClick={onBack} className="btn-secondary px-4 py-2 text-sm">
          Back to Attempts
        </button>
      </div>
    </div>
  )
}
