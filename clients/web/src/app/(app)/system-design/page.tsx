'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type SystemDesignTrackSummary,
  type SystemDesignTrack,
  type UserTrackProgressData,
  type OralSession,
  type OralGradeResult,
  type OralSessionSummary,
} from '@/lib/api'
import {
  TrackCard,
  AudioRecorder,
  AudioUploader,
  OralGradeDisplay,
  SessionProgress,
} from '@/components/system-design'
import { clsx } from 'clsx'

type FlowState = 'select' | 'session' | 'question' | 'grading' | 'result' | 'session-complete'
type InputMode = 'record' | 'upload'

export default function SystemDesignPage() {
  const { userId } = useAuth()
  const searchParams = useSearchParams()

  // Data state
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tracks, setTracks] = useState<SystemDesignTrackSummary[]>([])
  const [trackProgress, setTrackProgress] = useState<Record<string, UserTrackProgressData>>({})
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null)

  // Flow state
  const [flowState, setFlowState] = useState<FlowState>('select')
  const [selectedTrack, setSelectedTrack] = useState<SystemDesignTrack | null>(null)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)

  // Oral session state
  const [oralSession, setOralSession] = useState<OralSession | null>(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [currentGrade, setCurrentGrade] = useState<OralGradeResult | null>(null)
  const [sessionSummary, setSessionSummary] = useState<OralSessionSummary | null>(null)
  const [inputMode, setInputMode] = useState<InputMode>('record')

  // UI state
  const [settingActive, setSettingActive] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [gradingTimeout, setGradingTimeout] = useState(false)
  const [recentSessions, setRecentSessions] = useState<OralSession[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [lastAudioBlob, setLastAudioBlob] = useState<Blob | File | null>(null)

  // Load initial data
  useEffect(() => {
    async function loadData() {
      if (!userId) return

      setLoading(true)
      setError(null)

      try {
        const [tracksData, activeTrackData, sessionsData] = await Promise.all([
          leetloopApi.getSystemDesignTracks(),
          leetloopApi.getActiveSystemDesignTrack(userId).catch(() => null),
          leetloopApi.getOralSessions(userId, 10).catch(() => []),
        ])

        setTracks(tracksData)
        setActiveTrackId(activeTrackData?.active_track_id || null)
        setRecentSessions(sessionsData)

        // Load progress for each track
        const progressMap: Record<string, UserTrackProgressData> = {}
        for (const track of tracksData) {
          try {
            const progress = await leetloopApi.getTrackProgress(track.id, userId)
            if (progress.progress) {
              progressMap[track.id] = progress.progress
            }
          } catch {
            // Ignore
          }
        }
        setTrackProgress(progressMap)
      } catch (err) {
        console.error('Failed to load data:', err)
        setError('Failed to load data. Make sure the backend is running.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [userId])

  // Handle deep link from dashboard: ?session={id}&q={index}
  useEffect(() => {
    const sessionId = searchParams.get('session')
    const qIndex = searchParams.get('q')
    if (sessionId && !oralSession) {
      leetloopApi.getOralSession(sessionId).then((session) => {
        setOralSession(session)
        setCurrentQuestionIndex(qIndex ? parseInt(qIndex, 10) : 0)
        setCurrentGrade(null)
        setSessionSummary(null)
        setFlowState('question')
      }).catch(() => {
        // Session not found, fall through to normal select view
      })
    }
  }, [searchParams, oralSession])

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

  async function handleStartOralSession() {
    if (!userId || !selectedTrack || !selectedTopic) return

    setGenerating(true)
    setError(null)

    try {
      const session = await leetloopApi.createOralSession(userId, {
        track_id: selectedTrack.id,
        topic: selectedTopic,
      })
      setOralSession(session)
      setCurrentQuestionIndex(0)
      setCurrentGrade(null)
      setSessionSummary(null)
      setFlowState('question')
      setSelectedTrack(null) // Close modal
    } catch (err) {
      console.error('Failed to create oral session:', err)
      setError('Failed to create oral session. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  const handleAudioSubmit = useCallback(async (audioData: Blob | File) => {
    if (!oralSession) return

    const question = oralSession.questions[currentQuestionIndex]
    if (!question) return

    setLastAudioBlob(audioData)
    setUploading(true)
    setFlowState('grading')
    setError(null)
    setGradingTimeout(false)

    // Show timeout message after 30s
    const timeoutId = setTimeout(() => setGradingTimeout(true), 30000)

    try {
      const result = await leetloopApi.submitOralAudio(question.id, audioData)
      setCurrentGrade(result)
      setFlowState('result')
      setLastAudioBlob(null)

      // Update the session's question status locally
      setOralSession(prev => {
        if (!prev) return prev
        const updated = { ...prev, questions: [...prev.questions] }
        updated.questions[currentQuestionIndex] = {
          ...updated.questions[currentQuestionIndex],
          status: 'graded' as const,
          overall_score: result.overall_score,
          verdict: result.verdict,
        }
        return updated
      })
    } catch (err) {
      console.error('Failed to grade audio:', err)
      setError('Failed to grade audio. Your recording is preserved — click Retry to try again.')
      setFlowState('question')
    } finally {
      clearTimeout(timeoutId)
      setUploading(false)
      setGradingTimeout(false)
    }
  }, [oralSession, currentQuestionIndex])

  function handleNextQuestion() {
    if (!oralSession) return

    const nextIndex = currentQuestionIndex + 1
    if (nextIndex >= oralSession.questions.length) {
      // Complete session
      handleCompleteSession()
    } else {
      setCurrentQuestionIndex(nextIndex)
      setCurrentGrade(null)
      setFlowState('question')
    }
  }

  async function handleCompleteSession() {
    if (!oralSession) return

    try {
      const summary = await leetloopApi.completeOralSession(oralSession.id)
      setSessionSummary(summary)
      setFlowState('session-complete')

      // Refresh recent sessions
      if (userId) {
        const sessionsData = await leetloopApi.getOralSessions(userId, 10).catch(() => [])
        setRecentSessions(sessionsData)
      }
    } catch (err) {
      console.error('Failed to complete session:', err)
      setError('Failed to complete session.')
    }
  }

  function handleBackToTopics() {
    setOralSession(null)
    setCurrentGrade(null)
    setSessionSummary(null)
    setFlowState('select')
  }

  async function handleSetActiveTrack(trackId: string) {
    if (!userId || settingActive) return

    setSettingActive(true)
    try {
      await leetloopApi.setActiveSystemDesignTrack(userId, trackId)
      setActiveTrackId(trackId)
    } catch (err) {
      console.error('Failed to set active track:', err)
    } finally {
      setSettingActive(false)
    }
  }

  function handleCloseModal() {
    setSelectedTrack(null)
    setSelectedTopic(null)
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading system design tracks...</div>
      </div>
    )
  }

  if (error && flowState === 'select') {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error}</p>
        <p className="text-sm text-gray-500">Make sure the backend API is running.</p>
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
          Practice system design orally. Record or upload your answer, get AI grading with cited evidence.
        </p>
      </div>

      {/* === ORAL SESSION FLOW === */}
      {oralSession && flowState !== 'select' && flowState !== 'session-complete' && (
        <div className="space-y-4">
          {/* Session header with scenario */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <span className="tag tag-accent">{oralSession.topic}</span>
              <button
                onClick={handleBackToTopics}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Back to topics
              </button>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed mb-4">
              {oralSession.scenario}
            </p>
            <SessionProgress
              questions={oralSession.questions}
              currentIndex={currentQuestionIndex}
            />
          </div>

          {/* Current question */}
          {(flowState === 'question' || flowState === 'grading') && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <span className="coord-display">Q{currentQuestionIndex + 1}</span>
                <span className="text-xs font-mono uppercase text-gray-500">
                  {oralSession.questions[currentQuestionIndex]?.focus_area}
                </span>
              </div>

              <div className="p-4 bg-gray-50 border-l-4 border-black mb-4">
                <p className="text-sm leading-relaxed">
                  {oralSession.questions[currentQuestionIndex]?.question_text}
                </p>
              </div>

              {/* Key concepts */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-2">Key concepts to address:</p>
                <div className="flex flex-wrap gap-1">
                  {oralSession.questions[currentQuestionIndex]?.key_concepts.map((concept, i) => (
                    <span key={i} className="tag text-xs">{concept}</span>
                  ))}
                </div>
              </div>

              {/* Audio input (only when not grading) */}
              {flowState === 'question' && (
                <>
                  {/* Tab toggle */}
                  <div className="flex gap-1 mb-4">
                    <button
                      onClick={() => setInputMode('record')}
                      className={clsx(
                        'px-4 py-1.5 text-xs font-mono uppercase border-2 transition-colors',
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
                        'px-4 py-1.5 text-xs font-mono uppercase border-2 transition-colors',
                        inputMode === 'upload'
                          ? 'border-black bg-black text-white'
                          : 'border-gray-200 text-gray-500 hover:border-gray-400'
                      )}
                    >
                      Upload File
                    </button>
                  </div>

                  {inputMode === 'record' ? (
                    <AudioRecorder
                      suggestedDuration={oralSession.questions[currentQuestionIndex]?.suggested_duration_minutes || 4}
                      onSubmit={handleAudioSubmit}
                      isUploading={uploading}
                    />
                  ) : (
                    <AudioUploader
                      onSubmit={handleAudioSubmit}
                      isUploading={uploading}
                    />
                  )}
                </>
              )}

              {/* Grading state */}
              {flowState === 'grading' && (
                <div className="flex flex-col items-center gap-3 py-8">
                  <div className="w-12 h-12 border-3 border-coral border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm font-mono text-gray-600">
                    Gemini is evaluating your response...
                  </p>
                  {gradingTimeout && (
                    <p className="text-xs text-gray-400">
                      Still processing... audio evaluation can take up to a minute.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Grade result */}
          {flowState === 'result' && currentGrade && (
            <div className="space-y-4">
              <OralGradeDisplay grade={currentGrade} />

              <div className="flex justify-center">
                <button
                  onClick={handleNextQuestion}
                  className="btn-primary px-8 py-2"
                >
                  {currentQuestionIndex < oralSession.questions.length - 1
                    ? 'Next Question'
                    : 'Complete Session'
                  }
                </button>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="card border-l-4 border-l-coral">
              <p className="text-coral text-sm">{error}</p>
              {lastAudioBlob && flowState === 'question' && (
                <button
                  onClick={() => handleAudioSubmit(lastAudioBlob)}
                  className="btn-primary px-4 py-1.5 text-sm mt-3"
                >
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* === SESSION COMPLETE === */}
      {flowState === 'session-complete' && sessionSummary && (
        <div className="space-y-4">
          <div className="card text-center py-8">
            <h2 className="heading-accent text-lg mb-4">Session Complete</h2>
            <div className="mb-3">
              <span className={clsx('stat-value text-5xl', getScoreColor(sessionSummary.overall_score))}>
                {sessionSummary.overall_score}
              </span>
              <span className="text-xl text-gray-400">/10</span>
            </div>
            <span className={clsx(
              'tag text-xs uppercase',
              sessionSummary.verdict === 'pass' ? 'tag-accent' : ''
            )}>
              {sessionSummary.verdict}
            </span>
            <p className="text-sm text-gray-500 mt-2 font-mono">
              {sessionSummary.topic} &middot; {sessionSummary.questions_graded} questions graded
            </p>
          </div>

          {/* Dimension averages */}
          {Object.keys(sessionSummary.dimension_averages).length > 0 && (
            <div className="card">
              <h3 className="section-title text-sm">Dimension Averages</h3>
              <div className="space-y-2">
                {Object.entries(sessionSummary.dimension_averages).map(([name, avg]) => (
                  <div key={name} className="flex items-center justify-between">
                    <span className="text-xs font-mono uppercase text-gray-600">
                      {name.replace(/_/g, ' ')}
                    </span>
                    <span className={clsx('text-sm font-mono font-bold', getScoreColor(avg))}>
                      {avg}/10
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Review topics added */}
          {sessionSummary.review_topics_added.length > 0 && (
            <div className="card-sm border-l-4 border-l-gray-400">
              <span className="text-xs font-mono uppercase text-gray-400">Added to Review Queue</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {sessionSummary.review_topics_added.map((topic, i) => (
                  <span key={i} className="tag text-xs">{topic}</span>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 justify-center">
            <button onClick={handleBackToTopics} className="btn-secondary px-6 py-2">
              Back to Topics
            </button>
            <button
              onClick={() => {
                setOralSession(null)
                setSessionSummary(null)
                setFlowState('select')
              }}
              className="btn-primary px-6 py-2"
            >
              Start New Session
            </button>
          </div>
        </div>
      )}

      {/* === TRACK SELECTION === */}
      {flowState === 'select' && (
        <>
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

          {/* Recent Oral Sessions */}
          {recentSessions.length > 0 && (
            <div>
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="section-title flex items-center gap-2 cursor-pointer hover:text-gray-700"
              >
                Recent Sessions
                <span className="text-gray-400 text-xs font-normal">
                  ({showHistory ? 'hide' : 'show'})
                </span>
              </button>

              {showHistory && (
                <div className="space-y-2">
                  {recentSessions.map((session) => {
                    const avgScore = session.questions.reduce((sum, q) => sum + (q.overall_score || 0), 0) /
                      Math.max(session.questions.filter(q => q.status === 'graded').length, 1)
                    return (
                      <div key={session.id} className="list-item flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={clsx(
                            'status-light',
                            session.status === 'completed' ? 'status-light-active' : 'status-light-inactive'
                          )} />
                          <div>
                            <span className="font-medium text-sm">{session.topic}</span>
                            <span className="text-xs text-gray-500 ml-2">
                              {session.questions.filter(q => q.status === 'graded').length}/{session.questions.length} graded
                            </span>
                          </div>
                        </div>
                        {session.status === 'completed' && (
                          <span className={clsx('font-mono font-bold', getScoreColor(avgScore))}>
                            {avgScore.toFixed(1)}/10
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Topic Selection Modal */}
      {selectedTrack && flowState === 'select' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="card max-w-lg w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <h2 className="heading-accent">{selectedTrack.name}</h2>
                {activeTrackId === selectedTrack.id && (
                  <span className="bg-coral-light text-coral text-[10px] font-semibold px-2 py-0.5 border border-coral">
                    ACTIVE
                  </span>
                )}
              </div>
              <button onClick={handleCloseModal} className="text-gray-500 hover:text-black">
                Close
              </button>
            </div>

            {activeTrackId !== selectedTrack.id && (
              <button
                onClick={() => handleSetActiveTrack(selectedTrack.id)}
                disabled={settingActive}
                className="w-full mb-4 py-2 px-4 border-2 border-coral text-coral text-sm font-medium hover:bg-coral-light transition-colors disabled:opacity-50"
              >
                {settingActive ? 'Setting...' : 'Set as Active Track for Dashboard'}
              </button>
            )}

            {selectedTrack.description && (
              <p className="text-sm text-gray-600 mb-4">{selectedTrack.description}</p>
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
                        {isCompleted && <span className="text-coral text-sm">completed</span>}
                        <span className="font-medium text-sm">{topic.name}</span>
                      </div>
                      <span className={clsx('tag text-xs', topic.difficulty === 'hard' && 'tag-accent')}>
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
              onClick={handleStartOralSession}
              disabled={!selectedTopic || generating}
              className={clsx(
                'btn-primary w-full py-3',
                (!selectedTopic || generating) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {generating ? 'Generating Questions...' : 'Start Oral Session'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
