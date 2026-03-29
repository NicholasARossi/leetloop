'use client'

import type { OnsitePrepGradeResult, OnsitePrepQuestion } from '@/lib/api'

interface GradeResultProps {
  result: OnsitePrepGradeResult
  question: OnsitePrepQuestion
  onReRecord: () => void
  onFollowUps: () => void
}

const DIMENSION_LABELS: Record<string, string> = {
  star_structure: 'STAR Structure',
  specificity: 'Specificity',
  i_vs_we: '"I" vs "We"',
  lp_signal: 'LP Signal',
  timing: 'Timing',
  impact: 'Impact',
  definition: 'Definition',
  intuition: 'Intuition',
  failure_modes: 'Failure Modes',
  practical_connection: 'Practical Connection',
  completeness: 'Completeness',
  architecture_clarity: 'Architecture Clarity',
  technical_depth: 'Technical Depth',
  design_decisions: 'Design Decisions',
  honest_framing: 'Honest Framing',
  metrics_impact: 'Metrics & Impact',
  problem_framing: 'Problem Framing',
  architecture: 'Architecture',
  data_training: 'Data & Training',
  evaluation: 'Evaluation',
  production: 'Production',
  timing_structure: 'Timing & Structure',
}

function getScoreClass(score: number): string {
  if (score >= 4) return 'border-l-green-500'
  if (score >= 3) return 'border-l-yellow-500'
  return 'border-l-red-400'
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

export function GradeResult({ result, question, onReRecord, onFollowUps }: GradeResultProps) {
  return (
    <div>
      {/* Overall Score Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Overall Score</div>
            <div className="text-4xl font-semibold">
              {result.overall_score}
              <span className="text-base text-gray-400"> / 5</span>
            </div>
          </div>
          <div className="text-right">
            <span className={`badge ${getVerdictBadge(result.verdict)}`}>
              {getVerdictLabel(result.verdict)}
            </span>
          </div>
        </div>

        <div className="text-xs text-gray-600 italic mb-4">
          &ldquo;{question.prompt_text}&rdquo;
        </div>

        {/* Rubric scores grid */}
        <div className="grid grid-cols-2 gap-3">
          {result.dimensions.map((dim) => (
            <div key={dim.name} className={`p-3 bg-gray-50 border-l-[3px] ${getScoreClass(dim.score)}`}>
              <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">
                {DIMENSION_LABELS[dim.name] || dim.name}
              </div>
              <div className="text-xl font-semibold">{dim.score}</div>
              {dim.summary && (
                <div className="text-xs text-gray-500 mt-1">{dim.summary}</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* AI Feedback */}
      <div className="card">
        <div className="text-[10px] uppercase tracking-widest text-coral font-semibold mb-2">
          AI Coach Feedback
        </div>
        <div className="bg-coral/10 border-l-[3px] border-coral p-4 text-xs leading-relaxed">
          {result.feedback}
        </div>

        {result.strongest_moment && (
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-widest text-green-600 mb-1">Strongest Moment</div>
            <div className="text-xs text-gray-600 italic">&ldquo;{result.strongest_moment}&rdquo;</div>
          </div>
        )}

        {result.weakest_moment && (
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-widest text-red-500 mb-1">Weakest Moment</div>
            <div className="text-xs text-gray-600">{result.weakest_moment}</div>
          </div>
        )}
      </div>

      {/* Transcript */}
      {result.transcript && (
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <div className="section-title !border-0 !mb-0 !pb-0">Transcript</div>
          </div>
          <div className="bg-gray-50 border-l-[3px] border-gray-300 p-4 text-xs leading-relaxed text-gray-700 max-h-48 overflow-y-auto">
            {result.transcript}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-4">
        <button onClick={onReRecord} className="btn-secondary px-4 py-2 text-sm">
          Re-record
        </button>
        <button onClick={onFollowUps} className="btn-primary px-6 py-2 text-sm">
          Follow-up Probes &rarr;
        </button>
      </div>
    </div>
  )
}
