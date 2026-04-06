'use client'

import { useState } from 'react'
import {
  leetloopApi,
  type OnsitePrepQuestion,
  type OnsitePrepPhaseSubmission,
  type SubmitPhaseAudioResponse,
} from '@/lib/api'
import { PhaseProgress } from './PhaseProgress'
import { PhaseRecorder } from './PhaseRecorder'
import { PhaseResult } from './PhaseResult'
import { BreakdownSummary } from './BreakdownSummary'

type BreakdownState = 'starting' | 'phase_ready' | 'phase_grading' | 'phase_result' | 'complete'

interface BreakdownViewProps {
  question: OnsitePrepQuestion
  onDone: () => void
}

export function BreakdownView({ question, onDone }: BreakdownViewProps) {
  const [state, setState] = useState<BreakdownState>('starting')
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [currentPhase, setCurrentPhase] = useState(1)
  const [submissions, setSubmissions] = useState<OnsitePrepPhaseSubmission[]>([])
  const [lastResponse, setLastResponse] = useState<SubmitPhaseAudioResponse | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [overallScore, setOverallScore] = useState<number | null>(null)
  const [overallVerdict, setOverallVerdict] = useState<string | null>(null)

  const phases = question.breakdown_phases

  // Start a breakdown attempt
  const handleStart = async () => {
    setError(null)
    try {
      const resp = await leetloopApi.startBreakdownAttempt(question.id)
      setAttemptId(resp.attempt_id)
      setCurrentPhase(resp.current_phase)
      setState('phase_ready')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start breakdown')
    }
  }

  // Submit audio for the current phase
  const handlePhaseSubmit = async (blob: Blob, _images: File[]) => {
    if (!attemptId) return
    setIsUploading(true)
    setError(null)
    try {
      const resp = await leetloopApi.submitPhaseAudio(attemptId, currentPhase, blob)
      setLastResponse(resp)

      // Add/update submission in our local list
      const newSub: OnsitePrepPhaseSubmission = {
        id: resp.phase_submission_id,
        attempt_id: attemptId,
        phase_number: resp.phase_number,
        transcript: resp.result.transcript,
        dimensions: resp.result.dimensions,
        overall_score: resp.result.overall_score,
        verdict: resp.result.verdict,
        feedback: resp.result.feedback,
        strongest_moment: resp.result.strongest_moment,
        weakest_moment: resp.result.weakest_moment,
      }
      setSubmissions(prev => [...prev.filter(s => s.phase_number !== resp.phase_number), newSub])

      if (resp.attempt_complete) {
        setOverallScore(resp.overall_score)
        setOverallVerdict(resp.overall_verdict)
      }

      setState('phase_result')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to grade phase')
    } finally {
      setIsUploading(false)
    }
  }

  const handleReRecord = () => {
    setState('phase_ready')
  }

  const handleContinue = () => {
    if (lastResponse?.attempt_complete) {
      setState('complete')
    } else if (lastResponse?.next_phase) {
      setCurrentPhase(lastResponse.next_phase)
      setState('phase_ready')
    }
  }

  // Starting state
  if (state === 'starting') {
    return (
      <div>
        <div className="card text-center py-8">
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-3">Breakdown Mode</div>
          <div className="text-base font-medium leading-relaxed px-6 mb-4">
            &ldquo;{question.prompt_text}&rdquo;
          </div>
          <div className="text-xs text-gray-500 mb-6 max-w-md mx-auto">
            7 phases, each graded individually. Score 3.0+ to unlock the next phase.
            Phases 3-5 (Architecture, Data, Model) count double.
          </div>

          {/* Phase overview */}
          <div className="card-sm bg-gray-50 max-w-md mx-auto mb-6 text-left">
            <PhaseProgress
              phases={phases}
              currentPhase={1}
              submissions={[]}
            />
          </div>

          {error && (
            <div className="card-sm bg-red-50 text-red-700 text-sm mb-4">{error}</div>
          )}

          <button onClick={handleStart} className="btn-primary px-8 py-3 text-sm">
            Begin Phase 1
          </button>
        </div>
      </div>
    )
  }

  // Phase ready — recording
  if (state === 'phase_ready' && currentPhase <= phases.length) {
    const phase = phases[currentPhase - 1]
    return (
      <div>
        <div className="flex gap-4">
          {/* Phase progress sidebar */}
          <div className="w-48 flex-shrink-0 hidden md:block">
            <div className="card-sm bg-gray-50 sticky top-4">
              <PhaseProgress
                phases={phases}
                currentPhase={currentPhase}
                submissions={submissions}
              />
            </div>
          </div>

          {/* Recording area */}
          <div className="flex-1 min-w-0">
            {error && (
              <div className="card-sm bg-red-50 text-red-700 text-sm mb-4">{error}</div>
            )}
            <PhaseRecorder
              phase={phase}
              phaseNumber={currentPhase}
              onSubmit={handlePhaseSubmit}
              isUploading={isUploading}
            />
          </div>
        </div>
      </div>
    )
  }

  // Phase grading (uploading state is handled inline)

  // Phase result
  if (state === 'phase_result' && lastResponse) {
    const phase = phases[lastResponse.phase_number - 1]
    return (
      <div>
        <div className="flex gap-4">
          <div className="w-48 flex-shrink-0 hidden md:block">
            <div className="card-sm bg-gray-50 sticky top-4">
              <PhaseProgress
                phases={phases}
                currentPhase={lastResponse.next_phase ?? currentPhase}
                submissions={submissions}
              />
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <PhaseResult
              response={lastResponse}
              phase={phase}
              onReRecord={handleReRecord}
              onContinue={handleContinue}
            />
          </div>
        </div>
      </div>
    )
  }

  // Complete — show summary
  if (state === 'complete') {
    return (
      <BreakdownSummary
        phases={phases}
        submissions={submissions}
        overallScore={overallScore ?? 0}
        overallVerdict={overallVerdict ?? 'fail'}
        onBack={onDone}
      />
    )
  }

  return null
}
