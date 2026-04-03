'use client'

import { useState } from 'react'
import type { OnsitePrepGradeResult, OnsitePrepQuestion, IdealResponse } from '@/lib/api'
import { DesignPhaseGuide } from '@/components/onsite-prep/RecordingView'

interface GradeResultProps {
  result: OnsitePrepGradeResult
  question: OnsitePrepQuestion
  onReRecord: () => void
  onFollowUps: () => void
  idealResponse?: IdealResponse | null
  idealLoading?: boolean
  followUpsReady?: boolean
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

export function GradeResult({ result, question, onReRecord, onFollowUps, idealResponse, idealLoading, followUpsReady }: GradeResultProps) {
  const [showFullResponse, setShowFullResponse] = useState(false)
  const weakDimensions = result.dimensions.filter((dim) => dim.score < 4)

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
          Coach Debrief
        </div>
        <div className="bg-coral/10 border-l-[3px] border-coral p-4 text-xs leading-relaxed">
          {result.feedback}
        </div>

        {weakDimensions.length > 0 && (
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-2">Focus On Next Attempt</div>
            <div className="flex flex-wrap gap-2">
              {weakDimensions.map((dim) => (
                <span key={dim.name} className="badge badge-default">
                  {DIMENSION_LABELS[dim.name] || dim.name}
                </span>
              ))}
            </div>
          </div>
        )}

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

      {question.category === 'design' && (
        <div className="card">
          <div className="text-[10px] uppercase tracking-widest text-gray-500 font-semibold mb-3">
            Unlocked Coach View
          </div>
          <div className="text-xs text-gray-500 mb-4">
            This structure is hidden during the cold attempt. Use it now to repair gaps, then re-record without leaning on the outline.
          </div>
          {question.context_hint && (
            <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 text-xs text-gray-600 mb-4">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">Coach Context</div>
              {question.context_hint}
            </div>
          )}
          {question.phases.length > 0 && <DesignPhaseGuide phases={question.phases} />}
          <div className="card-sm bg-gray-50 mt-4">
            <div className="section-title" style={{ borderBottomColor: 'var(--gray-300)' }}>Grading Rubric</div>
            <div className="grid grid-cols-2 gap-3 mt-3">
              {question.rubric_dimensions.map((dim) => (
                <div key={dim.name}>
                  <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">{dim.label}</div>
                  <div className="text-xs text-gray-400">{dim.description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* What You Should Have Said */}
      <div className="card">
        <div className="text-[10px] uppercase tracking-widest text-blue-600 font-semibold mb-3">
          Model Debrief
        </div>

        {idealLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
            <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            Generating ideal L6 response...
          </div>
        )}

        {idealResponse && (
          <>
            <div className="bg-blue-50 border-l-[3px] border-blue-400 p-4 text-xs leading-relaxed text-blue-900 mb-3">
              {idealResponse.summary}
            </div>

            <div className="mb-3">
              <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-2">Ideal Outline</div>
              <ol className="list-decimal list-inside space-y-1">
                {idealResponse.outline.map((point, i) => (
                  <li key={i} className="text-xs text-gray-700 leading-relaxed">{point}</li>
                ))}
              </ol>
            </div>

            <div>
              <button
                onClick={() => setShowFullResponse(!showFullResponse)}
                className="text-xs text-blue-600 hover:text-blue-800 uppercase tracking-wide"
              >
                {showFullResponse ? 'Hide' : 'Show'} Full Model Answer {showFullResponse ? '\u25B2' : '\u25BC'}
              </button>
              {showFullResponse && (
                <div className="bg-gray-50 border-l-[3px] border-blue-300 p-4 text-xs leading-relaxed text-gray-700 mt-2 max-h-64 overflow-y-auto">
                  {idealResponse.full_response}
                </div>
              )}
            </div>
          </>
        )}

        {!idealLoading && !idealResponse && (
          <div className="text-xs text-gray-400 py-2">Ideal response will appear here after grading.</div>
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
        <button
          onClick={onFollowUps}
          disabled={followUpsReady === false}
          className="btn-primary px-6 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {followUpsReady === false ? (
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Loading Follow-ups...
            </span>
          ) : (
            'Start Adaptive Follow-ups \u2192'
          )}
        </button>
      </div>
    </div>
  )
}
