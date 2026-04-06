'use client'

import { useState } from 'react'
import { AudioRecorder } from '@/components/system-design/AudioRecorder'
import type { OnsitePrepDesignPhase } from '@/lib/api'
import { ImageAttachment } from './ImageAttachment'

interface PhaseRecorderProps {
  phase: OnsitePrepDesignPhase
  phaseNumber: number
  onSubmit: (blob: Blob, images: File[]) => void
  isUploading: boolean
}

export function PhaseRecorder({ phase, phaseNumber, onSubmit, isUploading }: PhaseRecorderProps) {
  const [images, setImages] = useState<File[]>([])

  const handleSubmit = (blob: Blob) => {
    onSubmit(blob, images)
  }

  const suggestedMinutes = phase.duration_seconds / 60

  return (
    <div>
      <div className="card">
        <div className="text-center py-4">
          <div className="text-[10px] uppercase tracking-widest text-coral font-semibold mb-2">
            Phase {phaseNumber} of 7
          </div>
          <div className="text-sm font-medium mb-2">{phase.name}</div>
          <div className="text-xs text-gray-600 italic mb-4 px-6">
            &ldquo;{phase.prompt}&rdquo;
          </div>

          {phase.key_areas.length > 0 && (
            <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 mx-auto max-w-lg text-left mb-4">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-2">Key Areas</div>
              <ul className="space-y-1">
                {phase.key_areas.map((area, i) => (
                  <li key={i} className="text-xs text-gray-500 flex gap-1.5">
                    <span className="text-gray-300 flex-shrink-0">&#8250;</span>
                    <span>{area}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {phase.rubric_dimensions.length > 0 && (
            <div className="bg-gray-50 border-l-[3px] border-coral/30 p-3 mx-auto max-w-lg text-left mb-4">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-2">
                Grading Dimensions (need 3.0 avg to proceed)
              </div>
              <div className="space-y-1">
                {phase.rubric_dimensions.map((dim) => (
                  <div key={dim.name} className="text-xs">
                    <span className="font-medium text-gray-600">{dim.label}</span>
                    <span className="text-gray-400"> — {dim.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <AudioRecorder
            suggestedDuration={suggestedMinutes}
            onSubmit={handleSubmit}
            isUploading={isUploading}
          />
        </div>
      </div>

      <div className="mt-4">
        <ImageAttachment
          images={images}
          onImagesChange={setImages}
          maxImages={5}
        />
      </div>
    </div>
  )
}
