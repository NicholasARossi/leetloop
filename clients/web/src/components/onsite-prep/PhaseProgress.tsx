'use client'

import type { OnsitePrepDesignPhase, OnsitePrepPhaseSubmission } from '@/lib/api'

interface PhaseProgressProps {
  phases: OnsitePrepDesignPhase[]
  currentPhase: number
  submissions: OnsitePrepPhaseSubmission[]
}

function getPhaseStatus(phaseNumber: number, currentPhase: number, submissions: OnsitePrepPhaseSubmission[]) {
  const sub = submissions.find(s => s.phase_number === phaseNumber)
  if (sub && sub.overall_score != null) {
    return { status: 'completed' as const, score: sub.overall_score, verdict: sub.verdict }
  }
  if (phaseNumber === currentPhase) {
    return { status: 'current' as const, score: null, verdict: null }
  }
  return { status: 'locked' as const, score: null, verdict: null }
}

function getStatusColor(status: 'locked' | 'current' | 'completed', verdict: string | null | undefined) {
  if (status === 'locked') return 'bg-gray-200 text-gray-400'
  if (status === 'current') return 'bg-coral text-white'
  if (verdict === 'pass') return 'bg-green-500 text-white'
  if (verdict === 'borderline') return 'bg-yellow-500 text-white'
  return 'bg-red-400 text-white'
}

export function PhaseProgress({ phases, currentPhase, submissions }: PhaseProgressProps) {
  return (
    <div className="space-y-1">
      {phases.map((phase, i) => {
        const phaseNum = i + 1
        const { status, score, verdict } = getPhaseStatus(phaseNum, currentPhase, submissions)

        return (
          <div key={i} className="flex items-center gap-3">
            {/* Phase number circle */}
            <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${getStatusColor(status, verdict)}`}>
              {status === 'completed' && score != null ? score.toFixed(1) : phaseNum}
            </div>

            {/* Phase name */}
            <div className="flex-1 min-w-0">
              <div className={`text-xs font-medium ${status === 'locked' ? 'text-gray-400' : 'text-gray-700'}`}>
                {phase.name}
              </div>
              <div className="text-[10px] text-gray-400">
                {Math.floor(phase.duration_seconds / 60)}-{Math.ceil(phase.duration_seconds / 60)} min
              </div>
            </div>

            {/* Status indicator */}
            {status === 'locked' && (
              <div className="text-[10px] text-gray-300 uppercase tracking-wider">Locked</div>
            )}
            {status === 'current' && (
              <div className="text-[10px] text-coral uppercase tracking-wider font-semibold">Current</div>
            )}
            {status === 'completed' && (
              <div className={`text-[10px] uppercase tracking-wider font-semibold ${
                verdict === 'pass' ? 'text-green-600' : verdict === 'borderline' ? 'text-yellow-600' : 'text-red-500'
              }`}>
                {verdict === 'pass' ? 'Strong' : verdict === 'borderline' ? 'Polish' : 'Redo'}
              </div>
            )}

            {/* Connector line (except last) */}
            {i < phases.length - 1 && (
              <div className="absolute left-[13px] top-7 w-0.5 h-4 bg-gray-200" />
            )}
          </div>
        )
      })}
    </div>
  )
}
