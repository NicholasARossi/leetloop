'use client'

import { useState, useCallback } from 'react'
import { AudioRecorder } from '@/components/system-design/AudioRecorder'
import type { LanguageOralPrompt } from '@/lib/api'
import { leetloopApi } from '@/lib/api'

interface OralPromptCardProps {
  prompt: LanguageOralPrompt
  userId: string
  onSessionStarted: (sessionId: string) => void
}

type CardState = 'ready' | 'recording' | 'uploading' | 'submitted'

export function OralPromptCard({ prompt, userId, onSessionStarted }: OralPromptCardProps) {
  const [state, setState] = useState<CardState>('ready')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleStartRecording = useCallback(async () => {
    setError(null)
    try {
      const session = await leetloopApi.createLanguageOralSession(userId, prompt.id)
      setSessionId(session.id)
      setState('recording')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create session')
    }
  }, [userId, prompt.id])

  const handleSubmit = useCallback(async (blob: Blob) => {
    if (!sessionId) return
    setIsUploading(true)
    setState('uploading')
    try {
      await leetloopApi.uploadLanguageOralAudio(sessionId, blob)
      setState('submitted')
      onSessionStarted(sessionId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to upload audio')
      setState('recording')
      setIsUploading(false)
    }
  }, [sessionId, onSessionStarted])

  const suggestedMinutes = Math.round(prompt.suggested_duration_seconds / 60)

  return (
    <div className="card-sm">
      {/* Theme tag */}
      {prompt.theme && (
        <div className="mb-2">
          <span className="inline-block px-2 py-0.5 text-xs font-mono bg-gray-100 border border-gray-300 rounded">
            {prompt.theme}
          </span>
        </div>
      )}

      {/* Prompt text */}
      <p className="text-sm leading-relaxed mb-3">{prompt.prompt_text}</p>

      {/* Grammar & vocab targets */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {prompt.grammar_targets.map((g, i) => (
          <span key={`g-${i}`} className="inline-block px-1.5 py-0.5 text-xs font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded">
            {g}
          </span>
        ))}
        {prompt.vocab_targets.map((v, i) => (
          <span key={`v-${i}`} className="inline-block px-1.5 py-0.5 text-xs font-mono bg-amber-50 text-amber-700 border border-amber-200 rounded">
            {v}
          </span>
        ))}
      </div>

      {/* Duration indicator */}
      <div className="text-xs text-gray-400 font-mono mb-3">
        {suggestedMinutes} min suggested
      </div>

      {error && (
        <div className="card-sm bg-red-50 border-red-200 text-red-700 text-sm mb-3">
          {error}
        </div>
      )}

      {/* States */}
      {state === 'ready' && (
        <button
          onClick={handleStartRecording}
          className="btn-primary px-5 py-2 flex items-center gap-2 text-sm"
        >
          <span className="w-2.5 h-2.5 bg-coral rounded-full" />
          Enregistrer
        </button>
      )}

      {state === 'recording' && (
        <AudioRecorder
          suggestedDuration={suggestedMinutes}
          onSubmit={handleSubmit}
          isUploading={isUploading}
        />
      )}

      {state === 'submitted' && (
        <div className="flex items-center gap-2 text-sm text-gray-500 font-mono py-2">
          <div className="w-4 h-4 border-2 border-coral border-t-transparent rounded-full animate-spin" />
          En cours d&apos;evaluation...
        </div>
      )}
    </div>
  )
}
