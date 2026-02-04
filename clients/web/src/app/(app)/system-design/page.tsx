'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type SystemDesignTrackSummary,
  type SystemDesignTrack,
  type SessionHistoryItem,
  type UserTrackProgressData,
} from '@/lib/api'
import { TrackCard } from '@/components/system-design'
import { clsx } from 'clsx'

export default function SystemDesignPage() {
  const { userId } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tracks, setTracks] = useState<SystemDesignTrackSummary[]>([])
  const [trackProgress, setTrackProgress] = useState<Record<string, UserTrackProgressData>>({})
  const [history, setHistory] = useState<SessionHistoryItem[]>([])
  const [selectedTrack, setSelectedTrack] = useState<SystemDesignTrack | null>(null)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null)
  const [settingActive, setSettingActive] = useState(false)

  useEffect(() => {
    async function loadData() {
      if (!userId) return

      setLoading(true)
      setError(null)

      try {
        // Load tracks, history, and active track in parallel
        const [tracksData, historyData, activeTrackData] = await Promise.all([
          leetloopApi.getSystemDesignTracks(),
          leetloopApi.getSystemDesignHistory(userId, 10),
          leetloopApi.getActiveSystemDesignTrack(userId).catch(() => null),
        ])

        setTracks(tracksData)
        setHistory(historyData.sessions)
        setActiveTrackId(activeTrackData?.active_track_id || null)

        // Load progress for each track
        const progressMap: Record<string, UserTrackProgressData> = {}
        for (const track of tracksData) {
          try {
            const progress = await leetloopApi.getTrackProgress(track.id, userId)
            if (progress.progress) {
              progressMap[track.id] = progress.progress
            }
          } catch {
            // Ignore errors for individual track progress
          }
        }
        setTrackProgress(progressMap)
      } catch (err) {
        console.error('Failed to load system design data:', err)
        setError('Failed to load data. Make sure the backend is running.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [userId])

  async function handleTrackSelect(track: SystemDesignTrackSummary) {
    try {
      const fullTrack = await leetloopApi.getSystemDesignTrack(track.id)
      setSelectedTrack(fullTrack)
      setSelectedTopic(null)
    } catch (err) {
      console.error('Failed to load track:', err)
      setError('Failed to load track details.')
    }
  }

  async function handleStartSession() {
    if (!userId || !selectedTrack || !selectedTopic) return

    setStarting(true)
    try {
      const session = await leetloopApi.createSystemDesignSession(userId, {
        track_id: selectedTrack.id,
        topic: selectedTopic,
        session_type: 'track',
      })
      router.push(`/system-design/session/${session.id}`)
    } catch (err) {
      console.error('Failed to start session:', err)
      setError('Failed to start session. Please try again.')
      setStarting(false)
    }
  }

  function handleCloseModal() {
    setSelectedTrack(null)
    setSelectedTopic(null)
  }

  async function handleSetActiveTrack(trackId: string) {
    if (!userId || settingActive) return

    setSettingActive(true)
    try {
      await leetloopApi.setActiveSystemDesignTrack(userId, trackId)
      setActiveTrackId(trackId)
    } catch (err) {
      console.error('Failed to set active track:', err)
      setError('Failed to set active track.')
    } finally {
      setSettingActive(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading system design tracks...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <p className="text-sm text-gray-500">
          Make sure the backend API is running.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center gap-3 mb-2">
          <div className="status-light status-light-active" />
          <h1 className="heading-accent text-xl">SYSTEM DESIGN</h1>
        </div>
        <p className="text-sm text-gray-600">
          Practice system design with AI-generated questions and harsh senior-level grading.
          Each session includes 2-3 hard questions with detailed rubric-based feedback.
        </p>
      </div>

      {/* Track Selection */}
      <div>
        <h2 className="section-title">Select a Track</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tracks.map((track) => (
            <TrackCard
              key={track.id}
              track={track}
              progress={trackProgress[track.id]}
              isActive={activeTrackId === track.id}
              onClick={() => handleTrackSelect(track)}
            />
          ))}
        </div>
      </div>

      {/* Recent Sessions */}
      {history.length > 0 && (
        <div>
          <h2 className="section-title">Recent Sessions</h2>
          <div className="space-y-2">
            {history.map((session) => (
              <button
                key={session.id}
                onClick={() => router.push(
                  session.status === 'completed'
                    ? `/system-design/session/${session.id}/results`
                    : `/system-design/session/${session.id}`
                )}
                className="list-item w-full text-left flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className={clsx(
                    'status-light',
                    session.status === 'completed' ? 'status-light-active' : 'status-light-inactive'
                  )} />
                  <div>
                    <span className="font-medium text-sm">{session.topic}</span>
                    {session.track_name && (
                      <span className="text-xs text-gray-500 ml-2">
                        {session.track_name}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {session.overall_score && (
                    <span className={clsx(
                      'font-mono font-bold',
                      session.overall_score >= 7 ? 'text-green-600' :
                      session.overall_score >= 5 ? 'text-yellow-600' : 'text-coral'
                    )}>
                      {session.overall_score.toFixed(1)}/10
                    </span>
                  )}
                  <span className="tag text-xs">
                    {session.status === 'completed' ? 'Completed' : 'In Progress'}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Topic Selection Modal */}
      {selectedTrack && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="card max-w-lg w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <h2 className="heading-accent">{selectedTrack.name}</h2>
                {activeTrackId === selectedTrack.id && (
                  <span className="bg-sky-100 text-sky-700 text-[10px] font-semibold px-2 py-0.5 border border-sky-300">
                    ACTIVE
                  </span>
                )}
              </div>
              <button
                onClick={handleCloseModal}
                className="text-gray-500 hover:text-black"
              >
                Close
              </button>
            </div>

            {/* Set as Active button */}
            {activeTrackId !== selectedTrack.id && (
              <button
                onClick={() => handleSetActiveTrack(selectedTrack.id)}
                disabled={settingActive}
                className="w-full mb-4 py-2 px-4 border-2 border-sky-500 text-sky-700 text-sm font-medium hover:bg-sky-50 transition-colors disabled:opacity-50"
              >
                {settingActive ? 'Setting...' : 'Set as Active Track for Dashboard'}
              </button>
            )}

            {selectedTrack.description && (
              <p className="text-sm text-gray-600 mb-4">
                {selectedTrack.description}
              </p>
            )}

            <h3 className="text-sm font-semibold mb-3">Select a Topic</h3>
            <div className="space-y-2 mb-6">
              {selectedTrack.topics.map((topic) => {
                const isCompleted = trackProgress[selectedTrack.id]?.completed_topics?.includes(topic.name)
                return (
                  <button
                    key={topic.name}
                    onClick={() => setSelectedTopic(topic.name)}
                    className={clsx(
                      'w-full p-3 border-2 text-left transition-colors',
                      selectedTopic === topic.name
                        ? 'border-black bg-gray-50'
                        : 'border-gray-200 hover:border-gray-400'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {isCompleted && (
                          <span className="text-green-500 text-sm">completed</span>
                        )}
                        <span className="font-medium text-sm">{topic.name}</span>
                      </div>
                      <span className={clsx(
                        'tag text-xs',
                        topic.difficulty === 'hard' && 'tag-accent'
                      )}>
                        {topic.difficulty}
                      </span>
                    </div>
                    {topic.example_systems.length > 0 && (
                      <div className="text-xs text-gray-500 mt-1">
                        Examples: {topic.example_systems.slice(0, 3).join(', ')}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>

            <button
              onClick={handleStartSession}
              disabled={!selectedTopic || starting}
              className={clsx(
                'btn btn-primary w-full',
                (!selectedTopic || starting) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {starting ? 'Starting Session...' : 'Start Session'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
