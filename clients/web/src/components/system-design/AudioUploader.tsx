'use client'

import { useRef, useState, useCallback } from 'react'

interface AudioUploaderProps {
  onSubmit: (file: File) => void
  isUploading: boolean
}

const ACCEPTED_TYPES = ['audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/mp4', 'audio/webm', 'audio/ogg', 'audio/m4a']
const ACCEPTED_EXTENSIONS = '.mp3,.wav,.m4a,.webm,.ogg'
const MAX_SIZE = 25 * 1024 * 1024 // 25MB

export function AudioUploader({ onSubmit, isUploading }: AudioUploaderProps) {
  const [file, setFile] = useState<File | null>(null)
  const [duration, setDuration] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const validateAndSetFile = useCallback((f: File) => {
    setError(null)

    if (f.size > MAX_SIZE) {
      setError(`File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Maximum is 25MB.`)
      return
    }

    // Check duration via Audio element
    const audio = new Audio()
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => {
      setDuration(Math.round(audio.duration))
      URL.revokeObjectURL(audio.src)
    }
    audio.onerror = () => {
      URL.revokeObjectURL(audio.src)
      // Still allow the file even if we can't read duration
      setDuration(null)
    }
    audio.src = URL.createObjectURL(f)

    setFile(f)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) validateAndSetFile(f)
  }, [validateAndSetFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) validateAndSetFile(f)
  }, [validateAndSetFile])

  const handleSubmit = useCallback(() => {
    if (file) onSubmit(file)
  }, [file, onSubmit])

  const clearFile = useCallback(() => {
    setFile(null)
    setDuration(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }, [])

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="card-sm bg-red-50 border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {!file ? (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            border-2 border-dashed p-8 text-center cursor-pointer transition-colors
            ${isDragging
              ? 'border-coral bg-coral-light'
              : 'border-gray-300 hover:border-gray-400'
            }
          `}
          style={{ clipPath: 'polygon(16px 0, 100% 0, 100% calc(100% - 16px), calc(100% - 16px) 100%, 0 100%, 0 16px)' }}
          onClick={() => inputRef.current?.click()}
        >
          <div className="text-gray-500 font-mono text-sm">
            <p className="mb-1">Drop audio file here</p>
            <p className="text-xs text-gray-400">or click to browse</p>
            <p className="text-xs text-gray-400 mt-2">MP3, WAV, M4A, WebM &middot; Max 25MB</p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      ) : (
        <div className="card-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-mono text-sm truncate flex-1">
              {file.name}
            </div>
            <button
              onClick={clearFile}
              className="text-gray-400 hover:text-gray-600 ml-2 text-xs"
            >
              clear
            </button>
          </div>
          <div className="flex gap-4 text-xs font-mono text-gray-500">
            <span>{formatSize(file.size)}</span>
            {duration !== null && <span>{formatDuration(duration)}</span>}
          </div>

          {/* Uploading state */}
          {isUploading ? (
            <div className="flex items-center gap-2 py-2">
              <div className="w-4 h-4 border-2 border-coral border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-mono text-gray-500">Sending to Gemini for evaluation...</span>
            </div>
          ) : (
            <button
              onClick={handleSubmit}
              className="btn-primary px-6 py-2 w-full"
              disabled={isUploading}
            >
              Upload &amp; Grade
            </button>
          )}
        </div>
      )}
    </div>
  )
}
