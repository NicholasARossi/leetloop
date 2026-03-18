'use client'

import { useState, useCallback } from 'react'
import { clsx } from 'clsx'
import { leetloopApi, type OralFollowUpResponse, type FollowUpGradeResult } from '@/lib/api'
import { AudioRecorder } from './AudioRecorder'
import { AudioUploader } from './AudioUploader'

interface FollowUpRecorderProps {
  questionId: string
  followUpIndex: number
  followUpText: string
  existingResponse?: OralFollowUpResponse
}

type FollowUpState = 'idle' | 'recording' | 'grading' | 'graded'
type InputMode = 'record' | 'upload'

export function FollowUpRecorder({
  questionId,
  followUpIndex,
  followUpText,
  existingResponse,
}: FollowUpRecorderProps) {
  const [state, setState] = useState<FollowUpState>(
    existingResponse?.status === 'graded' ? 'graded' : 'idle'
  )
  const [result, setResult] = useState<FollowUpGradeResult | null>(
    existingResponse?.status === 'graded'
      ? {
          transcript: existingResponse.transcript || '',
          score: existingResponse.score || 0,
          feedback: existingResponse.feedback || '',
          addressed_gap: existingResponse.addressed_gap || false,
        }
      : null
  )
  const [error, setError] = useState<string | null>(null)
  const [inputMode, setInputMode] = useState<InputMode>('record')
  const [showTranscript, setShowTranscript] = useState(false)
  const [uploading, setUploading] = useState(false)

  const handleAudioSubmit = useCallback(async (audioData: Blob | File) => {
    setState('grading')
    setError(null)
    setUploading(true)

    try {
      const gradeResult = await leetloopApi.submitFollowUpAudio(questionId, followUpIndex, audioData)
      setResult(gradeResult)
      setState('graded')
    } catch (err) {
      console.error('Failed to grade follow-up:', err)
      setError('Failed to grade follow-up. Please try again.')
      setState('idle')
    } finally {
      setUploading(false)
    }
  }, [questionId, followUpIndex])

  function getScoreBadge(score: number) {
    const color = score >= 7 ? 'bg-coral text-black' : score >= 5 ? 'bg-yellow-400 text-black' : 'bg-gray-400 text-white'
    return (
      <span className={clsx('text-xs font-mono font-bold px-2 py-0.5 border border-black', color)}>
        {score}/10
      </span>
    )
  }

  return (
    <div className="border-l-2 border-gray-200 pl-3">
      {/* Question text */}
      <div className="flex items-start gap-2 mb-2">
        <span className="text-coral font-mono text-sm flex-shrink-0">{followUpIndex + 1}.</span>
        <span className="text-sm font-mono text-gray-700">{followUpText}</span>
      </div>

      {/* Idle state — show Record button */}
      {state === 'idle' && (
        <div className="ml-5">
          {error && (
            <p className="text-xs text-coral mb-2">{error}</p>
          )}
          <button
            onClick={() => setState('recording')}
            className="text-xs font-mono uppercase text-gray-500 hover:text-coral border border-gray-300 hover:border-coral px-3 py-1 transition-colors"
          >
            Record Answer
          </button>
        </div>
      )}

      {/* Recording state — show AudioRecorder inline */}
      {state === 'recording' && (
        <div className="ml-5 mt-2 space-y-2">
          {/* Tab toggle */}
          <div className="flex gap-1">
            <button
              onClick={() => setInputMode('record')}
              className={clsx(
                'px-3 py-1 text-xs font-mono uppercase border transition-colors',
                inputMode === 'record'
                  ? 'border-black bg-black text-white'
                  : 'border-gray-200 text-gray-500 hover:border-gray-400'
              )}
            >
              Record
            </button>
            <button
              onClick={() => setInputMode('upload')}
              className={clsx(
                'px-3 py-1 text-xs font-mono uppercase border transition-colors',
                inputMode === 'upload'
                  ? 'border-black bg-black text-white'
                  : 'border-gray-200 text-gray-500 hover:border-gray-400'
              )}
            >
              Upload
            </button>
            <button
              onClick={() => setState('idle')}
              className="ml-auto text-xs text-gray-400 hover:text-gray-600"
            >
              Cancel
            </button>
          </div>

          {inputMode === 'record' ? (
            <AudioRecorder
              suggestedDuration={1}
              onSubmit={handleAudioSubmit}
              isUploading={uploading}
            />
          ) : (
            <AudioUploader
              onSubmit={handleAudioSubmit}
              isUploading={uploading}
            />
          )}
        </div>
      )}

      {/* Grading state */}
      {state === 'grading' && (
        <div className="ml-5 flex items-center gap-2 py-3">
          <div className="w-4 h-4 border-2 border-coral border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-mono text-gray-500">Evaluating follow-up...</span>
        </div>
      )}

      {/* Graded state — compact result card */}
      {state === 'graded' && result && (
        <div className="ml-5 mt-2 card-sm bg-gray-50">
          <div className="flex items-center gap-2 mb-2">
            {getScoreBadge(result.score)}
            <span className={clsx(
              'text-xs font-mono uppercase px-2 py-0.5 border',
              result.addressed_gap
                ? 'border-coral text-coral bg-coral-light'
                : 'border-gray-400 text-gray-600 bg-gray-100'
            )}>
              {result.addressed_gap ? 'Gap Addressed' : 'Gap Not Addressed'}
            </span>
          </div>
          <p className="text-xs font-mono text-gray-600">{result.feedback}</p>

          {/* Collapsible transcript */}
          {result.transcript && (
            <button
              onClick={() => setShowTranscript(!showTranscript)}
              className="text-xs text-gray-400 hover:text-gray-600 mt-2"
            >
              {showTranscript ? 'Hide transcript' : 'Show transcript'}
            </button>
          )}
          {showTranscript && result.transcript && (
            <p className="text-xs text-gray-500 mt-1 leading-relaxed whitespace-pre-wrap font-mono">
              {result.transcript}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
