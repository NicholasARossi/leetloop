'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type SystemDesignTrackSummary,
  type SystemDesignTrack,
  type SystemDesignAttempt,
  type AttemptGrade,
  type AttemptHistoryItem,
  type UserTrackProgressData,
} from '@/lib/api'
import { TrackCard } from '@/components/system-design'
import { clsx } from 'clsx'

type FlowState = 'select' | 'question' | 'grading' | 'result'

export default function SystemDesignPage() {
  const { userId } = useAuth()

  // Data state
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tracks, setTracks] = useState<SystemDesignTrackSummary[]>([])
  const [trackProgress, setTrackProgress] = useState<Record<string, UserTrackProgressData>>({})
  const [history, setHistory] = useState<AttemptHistoryItem[]>([])
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null)

  // Flow state
  const [flowState, setFlowState] = useState<FlowState>('select')
  const [selectedTrack, setSelectedTrack] = useState<SystemDesignTrack | null>(null)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)

  // Attempt state
  const [currentAttempt, setCurrentAttempt] = useState<SystemDesignAttempt | null>(null)
  const [response, setResponse] = useState('')
  const [wordCount, setWordCount] = useState(0)
  const [grade, setGrade] = useState<AttemptGrade | null>(null)

  // UI state
  const [settingActive, setSettingActive] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showQuestion, setShowQuestion] = useState(true)

  // Load initial data
  useEffect(() => {
    async function loadData() {
      if (!userId) return

      setLoading(true)
      setError(null)

      try {
        const [tracksData, historyData, activeTrackData] = await Promise.all([
          leetloopApi.getSystemDesignTracks(),
          leetloopApi.getSystemDesignAttemptHistory(userId, 10),
          leetloopApi.getActiveSystemDesignTrack(userId).catch(() => null),
        ])

        setTracks(tracksData)
        setHistory(historyData.attempts)
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

  // Update word count
  useEffect(() => {
    const words = response.trim().split(/\s+/).filter(w => w.length > 0)
    setWordCount(words.length)
  }, [response])

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

  async function handleGetQuestion() {
    if (!userId || !selectedTrack || !selectedTopic) return

    setGenerating(true)
    setError(null)

    try {
      const attempt = await leetloopApi.createSystemDesignAttempt(userId, {
        track_id: selectedTrack.id,
        topic: selectedTopic,
      })
      setCurrentAttempt(attempt)
      setResponse('')
      setGrade(null)
      setFlowState('question')
      setShowQuestion(true)
    } catch (err) {
      console.error('Failed to generate question:', err)
      setError('Failed to generate question. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  async function handleSubmit() {
    if (!currentAttempt || submitting || wordCount < 20) return

    setSubmitting(true)
    setFlowState('grading')
    setError(null)

    try {
      const gradeResult = await leetloopApi.submitSystemDesignAttempt(
        currentAttempt.id,
        response
      )
      setGrade(gradeResult)
      setFlowState('result')
      setShowQuestion(false)

      // Refresh history
      if (userId) {
        const historyData = await leetloopApi.getSystemDesignAttemptHistory(userId, 10)
        setHistory(historyData.attempts)
      }
    } catch (err) {
      console.error('Failed to submit:', err)
      setError('Failed to submit response. Please try again.')
      setFlowState('question')
    } finally {
      setSubmitting(false)
    }
  }

  function handleTryAnother() {
    setCurrentAttempt(null)
    setResponse('')
    setGrade(null)
    setFlowState('select')
    setShowQuestion(true)
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

  const getWordCountColor = () => {
    if (wordCount < 50) return 'text-coral'
    if (wordCount < 150) return 'text-gray-500'
    return 'text-green-600'
  }

  const getWordCountHint = () => {
    if (wordCount < 20) return 'Min 20 words to submit'
    if (wordCount < 50) return 'Need more detail'
    if (wordCount < 150) return 'Good start'
    if (wordCount < 300) return 'Solid response'
    return 'Comprehensive'
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-green-600'
    if (score >= 5) return 'text-yellow-600'
    return 'text-coral'
  }

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'pass':
        return <span className="tag bg-green-100 text-green-700 border-green-300">PASS</span>
      case 'borderline':
        return <span className="tag bg-yellow-100 text-yellow-700 border-yellow-300">BORDERLINE</span>
      case 'fail':
        return <span className="tag bg-red-100 text-coral border-red-300">FAIL</span>
      default:
        return null
    }
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
          Practice system design with AI-generated questions and harsh grading.
          Pick a topic, answer one question, get immediate feedback.
        </p>
      </div>

      {/* Active Flow: Question + Answer + Grade */}
      {(flowState === 'question' || flowState === 'grading' || flowState === 'result') && currentAttempt && (
        <div className="space-y-4">
          {/* Question Section */}
          <div className="card">
            <button
              onClick={() => setShowQuestion(!showQuestion)}
              className="w-full flex items-center justify-between mb-3"
            >
              <div className="flex items-center gap-3">
                <span className="tag tag-accent">{currentAttempt.topic}</span>
                {currentAttempt.question_focus_area && (
                  <span className="text-xs text-gray-500 font-mono uppercase">
                    {currentAttempt.question_focus_area}
                  </span>
                )}
              </div>
              <span className="text-gray-400 text-sm">
                {showQuestion ? 'Hide' : 'Show'} question
              </span>
            </button>

            {showQuestion && (
              <>
                <div className="p-4 bg-gray-50 border-l-4 border-black mb-4">
                  <p className="text-sm leading-relaxed">
                    {currentAttempt.question_text}
                  </p>
                </div>

                {currentAttempt.question_key_concepts.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-2">Key concepts to address:</p>
                    <div className="flex flex-wrap gap-1">
                      {currentAttempt.question_key_concepts.map((concept, i) => (
                        <span key={i} className="tag text-xs">
                          {concept}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Answer Section */}
          {(flowState === 'question' || flowState === 'grading') && (
            <div className="card">
              <h3 className="text-sm font-semibold mb-3">Your Response</h3>
              <textarea
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                disabled={flowState === 'grading'}
                placeholder="Write your response here. Be specific about architecture decisions, tradeoffs, and scaling considerations..."
                className={clsx(
                  'w-full h-64 p-4 border-2 border-black bg-white',
                  'text-sm leading-relaxed font-mono',
                  'focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2',
                  'placeholder:text-gray-400',
                  'disabled:bg-gray-100 disabled:cursor-not-allowed',
                  'resize-y min-h-[200px]'
                )}
              />

              <div className="flex justify-between items-center mt-2 text-xs">
                <span className={getWordCountColor()}>
                  {wordCount} words - {getWordCountHint()}
                </span>
                <span className="text-gray-400">
                  Aim for 200-400 words
                </span>
              </div>

              <div className="flex justify-end mt-4">
                <button
                  onClick={handleSubmit}
                  disabled={submitting || wordCount < 20}
                  className={clsx(
                    'btn btn-primary',
                    (submitting || wordCount < 20) && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  {submitting ? 'Grading...' : 'Submit & Grade'}
                </button>
              </div>
            </div>
          )}

          {/* Grade Section */}
          {flowState === 'result' && grade && (
            <div className="space-y-4">
              {/* Score */}
              <div className="card text-center py-6">
                <div className="mb-2">
                  <span className={clsx('stat-value text-5xl', getScoreColor(grade.score))}>
                    {grade.score.toFixed(1)}
                  </span>
                  <span className="text-xl text-gray-400">/10</span>
                </div>
                {getVerdictBadge(grade.verdict)}
              </div>

              {/* Feedback */}
              <div className="card">
                <h3 className="font-semibold text-black mb-3">Feedback</h3>
                <p className="text-sm text-gray-700 leading-relaxed">
                  {grade.feedback}
                </p>
              </div>

              {/* Missed Concepts & Review Topics */}
              {(grade.missed_concepts.length > 0 || grade.review_topics.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {grade.missed_concepts.length > 0 && (
                    <div className="card border-l-4 border-l-coral">
                      <h3 className="font-semibold text-black mb-3">Missed Concepts</h3>
                      <div className="flex flex-wrap gap-1">
                        {grade.missed_concepts.map((concept, i) => (
                          <span key={i} className="tag text-xs bg-red-50 text-coral border-red-200">
                            {concept}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {grade.review_topics.length > 0 && (
                    <div className="card border-l-4 border-l-yellow-500">
                      <h3 className="font-semibold text-black mb-3">Added to Review Queue</h3>
                      <div className="flex flex-wrap gap-1">
                        {grade.review_topics.map((topic, i) => (
                          <span key={i} className="tag text-xs">
                            {topic}
                          </span>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        These will appear in spaced repetition.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Try Another */}
              <div className="flex justify-center">
                <button
                  onClick={handleTryAnother}
                  className="btn btn-primary"
                >
                  Try Another Question
                </button>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="card border-l-4 border-l-coral">
              <p className="text-coral text-sm">{error}</p>
            </div>
          )}

          {/* Grading Overlay */}
          {flowState === 'grading' && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="card text-center p-8">
                <div className="animate-pulse mb-4">
                  <div className="w-16 h-16 mx-auto border-4 border-black rounded-full flex items-center justify-center">
                    <span className="text-2xl">AI</span>
                  </div>
                </div>
                <h2 className="heading-accent mb-2">Grading Your Response</h2>
                <p className="text-sm text-gray-600">
                  Our harsh senior-level AI is reviewing your answer...
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Track Selection (when not in active flow) */}
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

          {/* Recent Attempts */}
          {history.length > 0 && (
            <div>
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="section-title flex items-center gap-2 cursor-pointer hover:text-gray-700"
              >
                Recent Attempts
                <span className="text-gray-400 text-xs font-normal">
                  ({showHistory ? 'hide' : 'show'})
                </span>
              </button>

              {showHistory && (
                <div className="space-y-2">
                  {history.map((attempt) => (
                    <div
                      key={attempt.id}
                      className="list-item flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <div className={clsx(
                          'status-light',
                          attempt.status === 'graded' ? 'status-light-active' : 'status-light-inactive'
                        )} />
                        <div>
                          <span className="font-medium text-sm">{attempt.topic}</span>
                          {attempt.track_name && (
                            <span className="text-xs text-gray-500 ml-2">
                              {attempt.track_name}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {attempt.score && (
                          <span className={clsx(
                            'font-mono font-bold',
                            getScoreColor(attempt.score)
                          )}>
                            {attempt.score.toFixed(1)}/10
                          </span>
                        )}
                        {attempt.verdict && getVerdictBadge(attempt.verdict)}
                      </div>
                    </div>
                  ))}
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
              onClick={handleGetQuestion}
              disabled={!selectedTopic || generating}
              className={clsx(
                'btn btn-primary w-full',
                (!selectedTopic || generating) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {generating ? 'Generating Question...' : 'Get Question'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
