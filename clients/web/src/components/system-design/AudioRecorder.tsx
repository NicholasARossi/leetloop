'use client'

import { useRef, useState, useCallback, useEffect } from 'react'

interface AudioRecorderProps {
  suggestedDuration: number // minutes
  onSubmit: (blob: Blob) => void
  isUploading: boolean
}

type RecorderState = 'idle' | 'recording' | 'preview' | 'uploading'

export function AudioRecorder({ suggestedDuration, onSubmit, isUploading }: AudioRecorderProps) {
  const [state, setState] = useState<RecorderState>('idle')
  const [elapsed, setElapsed] = useState(0) // seconds
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const blobRef = useRef<Blob | null>(null)

  useEffect(() => {
    if (isUploading && state !== 'uploading') {
      setState('uploading')
    }
  }, [isUploading, state])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  const startRecording = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      })

      chunksRef.current = []
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        blobRef.current = blob
        const url = URL.createObjectURL(blob)
        setAudioUrl(url)
        setState('preview')
        // Stop all tracks
        stream.getTracks().forEach(t => t.stop())
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start(1000) // Collect chunks every second
      setState('recording')
      setElapsed(0)

      timerRef.current = setInterval(() => {
        setElapsed(prev => prev + 1)
      }, 1000)
    } catch (err) {
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setError('Microphone access required for recording. You can also upload a pre-recorded audio file using the Upload tab.')
      } else {
        setError('Failed to access microphone. Please check your browser permissions.')
      }
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const reRecord = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioUrl(null)
    blobRef.current = null
    setElapsed(0)
    setState('idle')
  }, [audioUrl])

  const handleSubmit = useCallback(() => {
    if (blobRef.current) {
      onSubmit(blobRef.current)
    }
  }, [onSubmit])

  const suggestedSeconds = suggestedDuration * 60

  const getTimerColor = () => {
    if (elapsed < 60) return 'text-gray-400' // too short
    if (elapsed <= suggestedSeconds) return 'text-coral' // good zone
    return 'text-yellow-600' // wrapping up
  }

  const getTimerLabel = () => {
    if (elapsed < 60) return 'warming up...'
    if (elapsed <= suggestedSeconds) return 'good pace'
    return 'consider wrapping up'
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="card-sm bg-red-50 border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Timer display */}
      {(state === 'recording' || state === 'preview') && (
        <div className="flex items-center justify-center gap-4 py-4">
          <div className="flex flex-col items-center">
            <span className={`stat-value text-3xl ${getTimerColor()}`}>
              {formatTime(elapsed)}
            </span>
            <span className="stat-label text-xs mt-1">
              {state === 'recording' ? getTimerLabel() : 'recorded'}
            </span>
          </div>
          <div className="text-xs text-gray-400 font-mono">
            / {suggestedDuration}:00 suggested
          </div>
        </div>
      )}

      {/* Recording pulse indicator */}
      {state === 'recording' && (
        <div className="flex justify-center">
          <div className="relative">
            <div className="w-4 h-4 bg-coral rounded-full animate-pulse" />
            <div className="absolute inset-0 w-4 h-4 bg-coral rounded-full animate-ping opacity-30" />
          </div>
          <span className="ml-3 text-sm font-mono text-coral uppercase">Recording</span>
        </div>
      )}

      {/* Audio preview */}
      {state === 'preview' && audioUrl && (
        <div className="card-sm">
          <audio src={audioUrl} controls className="w-full" />
        </div>
      )}

      {/* Uploading state */}
      {state === 'uploading' && (
        <div className="flex flex-col items-center gap-2 py-6">
          <div className="w-6 h-6 border-2 border-coral border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-mono text-gray-500">Sending to Gemini for evaluation...</span>
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-3 justify-center">
        {state === 'idle' && (
          <button onClick={startRecording} className="btn-primary px-6 py-2 flex items-center gap-2">
            <span className="w-3 h-3 bg-coral rounded-full" />
            Start Recording
          </button>
        )}

        {state === 'recording' && (
          <button onClick={stopRecording} className="btn-primary px-6 py-2">
            Stop &amp; Review
          </button>
        )}

        {state === 'preview' && (
          <>
            <button onClick={reRecord} className="btn-secondary px-4 py-2">
              Re-record
            </button>
            <button onClick={handleSubmit} className="btn-primary px-6 py-2" disabled={isUploading}>
              Submit
            </button>
          </>
        )}
      </div>
    </div>
  )
}
