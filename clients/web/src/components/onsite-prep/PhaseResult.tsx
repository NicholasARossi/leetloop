'use client'

import type { SubmitPhaseAudioResponse, OnsitePrepDesignPhase } from '@/lib/api'

interface PhaseResultProps {
  response: SubmitPhaseAudioResponse
  phase: OnsitePrepDesignPhase
  onReRecord: () => void
  onContinue: () => void
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

function getScoreClass(score: number): string {
  if (score >= 4) return 'border-l-green-500'
  if (score >= 3) return 'border-l-yellow-500'
  return 'border-l-red-400'
}

export function PhaseResult({ response, phase, onReRecord, onContinue }: PhaseResultProps) {
  const { result, gate_passed, attempt_complete, overall_score, overall_verdict } = response

  return (
    <div>
      {/* Score Header */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-gray-500">
              Phase {response.phase_number}: {phase.name}
            </div>
            <div className="text-3xl font-semibold mt-1">
              {result.overall_score}
              <span className="text-base text-gray-400"> / 5</span>
            </div>
          </div>
          <div>
            {gate_passed ? (
              <span className="badge badge-pass">Gate Passed</span>
            ) : (
              <span className="badge badge-fail">Below 3.0 — Re-record</span>
            )}
          </div>
        </div>

        {/* Dimension scores */}
        <div className="grid grid-cols-2 gap-2">
          {result.dimensions.map((dim) => (
            <div key={dim.name} className={`p-2 bg-gray-50 border-l-[3px] ${getScoreClass(dim.score)}`}>
              <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-0.5">
                {DIMENSION_LABELS[dim.name] || dim.name}
              </div>
              <div className="text-lg font-semibold">{dim.score}</div>
              {dim.summary && (
                <div className="text-[10px] text-gray-500 mt-0.5">{dim.summary}</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Feedback */}
      <div className="card">
        <div className="bg-coral/10 border-l-[3px] border-coral p-3 text-xs leading-relaxed">
          {result.feedback}
        </div>
        {result.strongest_moment && (
          <div className="mt-2">
            <div className="text-[10px] uppercase tracking-widest text-green-600 mb-0.5">Strongest</div>
            <div className="text-xs text-gray-600 italic">&ldquo;{result.strongest_moment}&rdquo;</div>
          </div>
        )}
        {result.weakest_moment && (
          <div className="mt-2">
            <div className="text-[10px] uppercase tracking-widest text-red-500 mb-0.5">Weakest</div>
            <div className="text-xs text-gray-600">{result.weakest_moment}</div>
          </div>
        )}
      </div>

      {/* Overall score if attempt complete */}
      {attempt_complete && overall_score != null && (
        <div className="card bg-gray-50">
          <div className="text-center">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Overall Breakdown Score</div>
            <div className="text-4xl font-semibold">
              {overall_score}
              <span className="text-base text-gray-400"> / 5</span>
            </div>
            <div className="mt-1">
              <span className={`badge ${overall_verdict === 'pass' ? 'badge-pass' : overall_verdict === 'borderline' ? 'badge-warn' : 'badge-fail'}`}>
                {overall_verdict === 'pass' ? 'Strong' : overall_verdict === 'borderline' ? 'Needs Polish' : 'Needs Work'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-4">
        <button onClick={onReRecord} className="btn-secondary px-4 py-2 text-sm">
          Re-record Phase
        </button>
        {gate_passed && (
          <button onClick={onContinue} className="btn-primary px-6 py-2 text-sm">
            {attempt_complete ? 'View Summary' : `Continue to Phase ${response.next_phase} \u2192`}
          </button>
        )}
      </div>
    </div>
  )
}
