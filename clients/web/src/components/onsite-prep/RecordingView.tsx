'use client'

import { useState } from 'react'
import { AudioRecorder } from '@/components/system-design/AudioRecorder'
import type { OnsitePrepQuestion, SubmitAudioResponse } from '@/lib/api'
import { leetloopApi } from '@/lib/api'

interface RecordingViewProps {
  question: OnsitePrepQuestion
  onGraded: (response: SubmitAudioResponse) => void
}

const CATEGORY_LABELS: Record<string, string> = {
  lp: 'LP Story',
  breadth: 'ML Breadth',
  depth: 'ML Depth',
  design: 'System Design',
}

export function RecordingView({ question, onGraded }: RecordingViewProps) {
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

          {question.context_hint && (
            <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 mx-auto max-w-lg text-left mb-6">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">
                {question.category === 'lp' ? 'Mapped Story' : 'Key Context'}
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

      {/* Rubric preview */}
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
  )
}
