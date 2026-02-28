'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'
import {
  leetloopApi,
  type LanguageTrackSummary,
  type DailyExerciseBatch,
  type DailyExerciseGrade,
  type BookProgressResponse,
} from '@/lib/api'
import { ExerciseDashboard } from '@/components/language'
import { clsx } from 'clsx'

export default function LanguagePage() {
  const { userId } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batch, setBatch] = useState<DailyExerciseBatch | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // Book progress state (compact bar)
  const [bookProgress, setBookProgress] = useState<BookProgressResponse | null>(null)

  // Track selection state (shown when no active track)
  const [needsTrackSelection, setNeedsTrackSelection] = useState(false)
  const [tracks, setTracks] = useState<LanguageTrackSummary[]>([])
  const [settingActive, setSettingActive] = useState<string | null>(null)

  // Active track name for display
  const [activeTrackName, setActiveTrackName] = useState<string | null>(null)
  const [showTrackSwitcher, setShowTrackSwitcher] = useState(false)
  const [switchingTrack, setSwitchingTrack] = useState<string | null>(null)

  const loadTracks = useCallback(async () => {
    try {
      const tracksData = await leetloopApi.getLanguageTracks()
      setTracks(tracksData)
    } catch {
      // Non-critical
    }
  }, [])

  const loadExercises = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)
    setNeedsTrackSelection(false)

    try {
      const data = await leetloopApi.getDailyExercises(userId)
      setBatch(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      // Backend returns 400 when no active track is set
      if (message.includes('No active language track')) {
        setNeedsTrackSelection(true)
        await loadTracks()
      } else {
        setError(message || 'Failed to load daily exercises.')
      }
    } finally {
      setLoading(false)
    }
  }, [userId, loadTracks])

  useEffect(() => {
    loadExercises()
    loadTracks()
  }, [loadExercises, loadTracks])

  // Load book progress and resolve active track name when batch is available
  useEffect(() => {
    if (!userId || !batch?.track_id) return
    if (!bookProgress) {
      leetloopApi.getBookProgress(batch.track_id, userId)
        .then(setBookProgress)
        .catch(() => {})
    }
    // Set active track name from loaded tracks
    if (tracks.length > 0 && !activeTrackName) {
      const active = tracks.find(t => t.id === batch.track_id)
      if (active) setActiveTrackName(active.name)
    }
  }, [userId, batch?.track_id, bookProgress, tracks, activeTrackName])

  async function handleSubmitExercise(exerciseId: string, responseText: string): Promise<void> {
    const grade: DailyExerciseGrade = await leetloopApi.submitDailyExercise(exerciseId, responseText)

    // Update the exercise in local state with the grade result
    setBatch((prev) => {
      if (!prev) return prev
      const updatedExercises = prev.exercises.map((ex) => {
        if (ex.id === exerciseId) {
          return {
            ...ex,
            status: 'completed' as const,
            response_text: responseText,
            score: grade.score,
            verdict: grade.verdict,
            feedback: grade.feedback,
            corrections: grade.corrections,
            missed_concepts: grade.missed_concepts,
          }
        }
        return ex
      })

      const completedCount = updatedExercises.filter((e) => e.status === 'completed').length
      const scores = updatedExercises
        .filter((e) => e.status === 'completed' && e.score != null)
        .map((e) => e.score!)
      const averageScore = scores.length > 0
        ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
        : null

      return {
        ...prev,
        exercises: updatedExercises,
        completed_count: completedCount,
        average_score: averageScore,
      }
    })

    // Invalidate book progress so it reloads with updated completion
    setBookProgress(null)
  }

  async function handleRegenerate(): Promise<void> {
    if (!userId) return

    setIsRegenerating(true)
    try {
      const data = await leetloopApi.regenerateDailyExercises(userId)
      setBatch(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to regenerate exercises.')
    } finally {
      setIsRegenerating(false)
    }
  }

  async function handleSetActiveTrack(trackId: string) {
    if (!userId || settingActive) return

    setSettingActive(trackId)
    try {
      await leetloopApi.setActiveLanguageTrack(userId, trackId)
      // Reset state for fresh load
      setBatch(null)
      setBookProgress(null)
      setActiveTrackName(null)
      setShowTrackSwitcher(false)
      // Now load daily exercises with the newly active track
      await loadExercises()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to set active track.')
    } finally {
      setSettingActive(null)
    }
  }

  async function handleSwitchTrack(trackId: string) {
    if (!userId || switchingTrack) return

    setSwitchingTrack(trackId)
    try {
      await leetloopApi.setActiveLanguageTrack(userId, trackId)
      setBatch(null)
      setBookProgress(null)
      setActiveTrackName(null)
      setShowTrackSwitcher(false)
      await loadExercises()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to switch track.')
    } finally {
      setSwitchingTrack(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-pulse mb-3">
            <div className="w-12 h-12 mx-auto border-3 border-black rounded-full flex items-center justify-center">
              <span className="text-lg font-bold">AI</span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">Loading today&apos;s exercises...</p>
          <p className="text-gray-400 text-xs mt-1">First load of the day may take a moment while exercises are generated.</p>
        </div>
      </div>
    )
  }

  if (error && !needsTrackSelection) {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error}</p>
        <button
          onClick={loadExercises}
          className="btn btn-primary"
        >
          Retry
        </button>
      </div>
    )
  }

  // Track selection view
  if (needsTrackSelection) {
    return (
      <div className="space-y-6">
        <div className="card">
          <div className="flex items-center gap-3 mb-2">
            <div className="status-light status-light-active" />
            <h1 className="heading-accent text-xl">LANGUAGES</h1>
          </div>
          <p className="text-sm text-gray-600">
            Choose a track to start your daily exercises.
          </p>
        </div>

        {error && (
          <div className="card border-l-4 border-l-coral">
            <p className="text-coral text-sm">{error}</p>
          </div>
        )}

        <div>
          <h2 className="section-title">Choose a Track</h2>
          {tracks.length === 0 ? (
            <div className="card p-8 text-center">
              <p className="text-gray-500 mb-2">No language tracks available yet.</p>
              <p className="text-sm text-gray-400">
                Ingest a language textbook to create a track.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {tracks.map((track) => (
                <div
                  key={track.id}
                  className="border-2 border-gray-200 bg-white hover:border-black transition-colors"
                >
                  <div className="px-4 py-3 flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-sm">{track.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="tag text-[10px]">{track.language.toUpperCase()}</span>
                        <span className="tag text-[10px]">{track.level.toUpperCase()}</span>
                        <span className="text-xs text-gray-500">
                          {track.total_topics} topics
                        </span>
                      </div>
                      {track.description && (
                        <p className="text-xs text-gray-500 mt-1">{track.description}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleSetActiveTrack(track.id)}
                      disabled={settingActive !== null}
                      className={clsx(
                        'px-4 py-1.5 text-xs font-semibold text-white transition-colors whitespace-nowrap',
                        settingActive === track.id
                          ? 'bg-gray-400 cursor-not-allowed'
                          : settingActive !== null
                            ? 'bg-gray-300 cursor-not-allowed'
                            : 'bg-black hover:bg-gray-800'
                      )}
                    >
                      {settingActive === track.id ? 'Setting...' : 'Set Active'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Daily exercise dashboard
  if (batch) {
    return (
      <div className="space-y-6">
        {/* Header with track switcher */}
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="status-light status-light-active" />
              <h1 className="heading-accent text-xl">LANGUAGES</h1>
            </div>
            {tracks.length > 1 && (
              <div className="relative">
                <button
                  onClick={() => setShowTrackSwitcher(!showTrackSwitcher)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium border-2 border-gray-200 hover:border-black transition-colors bg-white"
                >
                  <span className="text-gray-600">{activeTrackName || 'Track'}</span>
                  <svg className={clsx('w-3 h-3 text-gray-400 transition-transform', showTrackSwitcher && 'rotate-180')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {showTrackSwitcher && (
                  <div className="absolute right-0 top-full mt-1 w-64 bg-white border-2 border-black shadow-lg z-10">
                    {tracks.map((track) => {
                      const isActive = track.id === batch?.track_id
                      return (
                        <button
                          key={track.id}
                          onClick={() => !isActive && handleSwitchTrack(track.id)}
                          disabled={isActive || switchingTrack !== null}
                          className={clsx(
                            'w-full px-4 py-3 text-left border-b border-gray-100 last:border-0 transition-colors',
                            isActive
                              ? 'bg-gray-50 cursor-default'
                              : switchingTrack
                                ? 'opacity-50 cursor-not-allowed'
                                : 'hover:bg-gray-50'
                          )}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-sm font-medium">{track.name}</div>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="tag text-[9px]">{track.language.toUpperCase()}</span>
                                <span className="tag text-[9px]">{track.level.toUpperCase()}</span>
                              </div>
                            </div>
                            {isActive && (
                              <span className="text-[10px] font-semibold text-green-600 uppercase">Active</span>
                            )}
                            {switchingTrack === track.id && (
                              <span className="text-[10px] text-gray-400">Switching...</span>
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
          <p className="text-sm text-gray-600">
            Complete today&apos;s exercises. Answer inline and get immediate feedback.
          </p>
        </div>

        {/* Compact book progress bar */}
        {bookProgress && bookProgress.total_chapters > 0 && (
          <Link href="/language/book-progress" className="block card-sm hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-gray-500 uppercase tracking-wider">Book Progress</span>
              <span className="text-[11px] font-medium text-black">
                {bookProgress.completed_chapters}/{bookProgress.total_chapters} chapters &middot; {bookProgress.completion_percentage.toFixed(0)}%
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill transition-all duration-500"
                style={{ width: `${bookProgress.completion_percentage}%` }}
              />
            </div>
          </Link>
        )}

        {error && (
          <div className="card border-l-4 border-l-coral mb-4">
            <p className="text-coral text-sm">{error}</p>
          </div>
        )}

        <ExerciseDashboard
          exercises={batch.exercises}
          completedCount={batch.completed_count}
          totalCount={batch.total_count}
          averageScore={batch.average_score}
          onSubmitExercise={handleSubmitExercise}
          onRegenerate={handleRegenerate}
          isRegenerating={isRegenerating}
        />
      </div>
    )
  }

  return null
}
