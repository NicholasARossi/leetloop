'use client'

import { useState } from 'react'
import { AudioRecorder } from '@/components/system-design/AudioRecorder'
import type { OnsitePrepQuestion, OnsitePrepDesignPhase, SubmitAudioResponse } from '@/lib/api'
import { leetloopApi } from '@/lib/api'

interface RecordingViewProps {
  question: OnsitePrepQuestion
  onGraded: (response: SubmitAudioResponse) => void
  showCoaching?: boolean
}

const CATEGORY_LABELS: Record<string, string> = {
  lp: 'LP Story',
  breadth: 'ML Breadth',
  depth: 'ML Depth',
  design: 'System Design',
}

function formatMinutes(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s === 0 ? `${m} min` : `${m}m ${s}s`
}

export function DesignPhaseGuide({ phases }: { phases: OnsitePrepDesignPhase[] }) {
  const [expanded, setExpanded] = useState<number | null>(null)
  const totalSeconds = phases.reduce((sum, p) => sum + p.duration_seconds, 0)

  return (
    <div className="card-sm bg-gray-50 mt-4">
      <div className="flex items-center justify-between mb-3">
        <div className="section-title" style={{ borderBottomColor: 'var(--gray-300)' }}>
          Interview Phases
        </div>
        <div className="text-[10px] uppercase tracking-widest text-gray-400">
          {formatMinutes(totalSeconds)} total
        </div>
      </div>
      <div className="space-y-1">
        {phases.map((phase, i) => (
          <div key={i}>
            <button
              onClick={() => setExpanded(expanded === i ? null : i)}
              className="w-full flex items-center gap-3 py-2 px-1 text-left hover:bg-gray-100 rounded transition-colors"
            >
              <div className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-[10px] font-bold flex items-center justify-center">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-gray-700">{phase.name}</span>
              </div>
              <div className="text-[10px] text-gray-400 flex-shrink-0">
                {formatMinutes(phase.duration_seconds)}
              </div>
              <div className="text-gray-400 text-xs flex-shrink-0">
                {expanded === i ? '▲' : '▼'}
              </div>
            </button>
            {expanded === i && (
              <div className="ml-8 mb-2 pb-2 border-l-2 border-gray-200 pl-3">
                <p className="text-xs text-gray-600 mb-2 italic">{phase.prompt}</p>
                <ul className="space-y-1">
                  {phase.key_areas.map((area, j) => (
                    <li key={j} className="text-xs text-gray-500 flex gap-1.5">
                      <span className="text-gray-300 flex-shrink-0 mt-0.5">›</span>
                      <span>{area}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function RecordingView({ question, onGraded, showCoaching = false }: RecordingViewProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const suggestedMinutes = question.target_duration_seconds / 60

  const handleSubmit = async (blob: Blob) => {
    setIsUploading(true)
    setError(null)
    try {
      const result = await leetloopApi.submitOnsitePrepAudio(question.id, blob)
      onGraded(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to grade audio')
      setIsUploading(false)
    }
  }

  return (
    <div>
      <div className="card">
        <div className="text-center py-4">
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-3">
            {CATEGORY_LABELS[question.category]} &bull; {question.subcategory}
          </div>
          <div className="text-base font-medium leading-relaxed px-6 mb-4">
            &ldquo;{question.prompt_text}&rdquo;
          </div>

          {!showCoaching && (
            <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 mx-auto max-w-lg text-left mb-6">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">
                Interview Mode
              </div>
              <div className="text-xs text-gray-600">
                Give your cold answer first. Coaching structure and targeted hints unlock after grading so you practice framing and follow-ups without a script.
              </div>
            </div>
          )}

          {showCoaching && question.context_hint && (
            <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 mx-auto max-w-lg text-left mb-6">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">
                {question.category === 'lp' ? 'Mapped Story' : 'Coach Context'}
              </div>
              <div className="text-xs text-gray-600">{question.context_hint}</div>
            </div>
          )}

          <AudioRecorder
            suggestedDuration={suggestedMinutes}
            onSubmit={handleSubmit}
            isUploading={isUploading}
          />

          {error && (
            <div className="card-sm bg-red-50 text-red-700 text-sm mt-4">{error}</div>
          )}
        </div>
      </div>

      {/* Phase guide for design questions */}
      {showCoaching && question.category === 'design' && question.phases.length > 0 && (
        <DesignPhaseGuide phases={question.phases} />
      )}

      {showCoaching && (
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
      )}
    </div>
  )
}
