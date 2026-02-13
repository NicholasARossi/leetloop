'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type LanguageTrackSummary,
  type LanguageTrack,
  type LanguageAttempt,
  type LanguageAttemptGrade,
  type LanguageAttemptHistoryItem,
  type LanguageTrackProgressData,
} from '@/lib/api'
import { LanguageTrackCard } from '@/components/language'
import { clsx } from 'clsx'

type FlowState = 'select' | 'question' | 'grading' | 'result'

const exerciseTypes = [
  { value: 'vocabulary', label: 'Vocabulary' },
  { value: 'grammar', label: 'Grammar' },
  { value: 'fill_blank', label: 'Fill in the Blank' },
  { value: 'conjugation', label: 'Conjugation' },
  { value: 'sentence_construction', label: 'Sentence Construction' },
  { value: 'reading_comprehension', label: 'Reading Comprehension' },
]

export default function LanguagePage() {
  const { userId } = useAuth()

  // Data state
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tracks, setTracks] = useState<LanguageTrackSummary[]>([])
  const [trackProgress, setTrackProgress] = useState<Record<string, LanguageTrackProgressData>>({})
  const [history, setHistory] = useState<LanguageAttemptHistoryItem[]>([])
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null)

  // Flow state
  const [flowState, setFlowState] = useState<FlowState>('select')
  const [selectedTrack, setSelectedTrack] = useState<LanguageTrack | null>(null)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [selectedExerciseType, setSelectedExerciseType] = useState('vocabulary')

  // Attempt state
  const [currentAttempt, setCurrentAttempt] = useState<LanguageAttempt | null>(null)
  const [response, setResponse] = useState('')
  const [wordCount, setWordCount] = useState(0)
  const [grade, setGrade] = useState<LanguageAttemptGrade | null>(null)

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
        const [tracksData, historyData] = await Promise.all([
          leetloopApi.getLanguageTracks(),
          leetloopApi.getLanguageAttemptHistory(userId, 10),
        ])

        setTracks(tracksData)
        setHistory(historyData.attempts)

        // Load progress for each track
        const progressMap: Record<string, LanguageTrackProgressData> = {}
        for (const track of tracksData) {
          try {
            const progress = await leetloopApi.getLanguageTrackProgress(track.id, userId)
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

  useEffect(() => {
    const words = response.trim().split(/\s+/).filter(w => w.length > 0)
    setWordCount(words.length)
  }, [response])

  async function handleTrackSelect(track: LanguageTrackSummary) {
    try {
      const fullTrack = await leetloopApi.getLanguageTrack(track.id)
      setSelectedTrack(fullTrack)
      setSelectedTopic(null)
    } catch (err) {
      console.error('Failed to load track:', err)
      setError('Failed to load track details.')
    }
  }

  async function handleGetExercise() {
    if (!userId || !selectedTrack || !selectedTopic) return

    setGenerating(true)
    setError(null)

    try {
      const attempt = await leetloopApi.createLanguageAttempt(userId, {
        track_id: selectedTrack.id,
        topic: selectedTopic,
        exercise_type: selectedExerciseType,
      })
      setCurrentAttempt(attempt)
      setResponse('')
      setGrade(null)
      setFlowState('question')
      setShowQuestion(true)
    } catch (err) {
      console.error('Failed to generate exercise:', err)
      setError('Failed to generate exercise. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  async function handleSubmit() {
    if (!currentAttempt || submitting || !response.trim()) return

    setSubmitting(true)
    setFlowState('grading')
    setError(null)

    try {
      const gradeResult = await leetloopApi.submitLanguageAttempt(
        currentAttempt.id,
        response
      )
      setGrade(gradeResult)
      setFlowState('result')
      setShowQuestion(false)

      if (userId) {
        const historyData = await leetloopApi.getLanguageAttemptHistory(userId, 10)
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
      await leetloopApi.setActiveLanguageTrack(userId, trackId)
      setActiveTrackId(trackId)
    } catch (err) {
      console.error('Failed to set active track:', err)
      setError('Failed to set active track.')
    } finally {
      setSettingActive(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-coral'
    if (score >= 5) return 'text-gray-600'
    return 'text-black'
  }

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'pass':
        return <span className="tag bg-coral-light text-coral border-coral">PASS</span>
      case 'borderline':
        return <span className="tag bg-gray-100 text-gray-700 border-gray-300">BORDERLINE</span>
      case 'fail':
        return <span className="tag bg-gray-200 text-black border-gray-400">FAIL</span>
      default:
        return null
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading language tracks...</div>
      </div>
    )
  }

  if (error && flowState === 'select') {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error}</p>
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
          <h1 className="heading-accent text-xl">LANGUAGES</h1>
        </div>
        <p className="text-sm text-gray-600">
          Practice languages with AI-generated exercises and immersive grading.
          Pick a topic, complete an exercise, get immediate feedback.
        </p>
      </div>

      {/* Active Flow: Exercise + Answer + Grade */}
      {(flowState === 'question' || flowState === 'grading' || flowState === 'result') && currentAttempt && (
        <div className="space-y-4">
          {/* Exercise Section */}
          <div className="card">
            <button
              onClick={() => setShowQuestion(!showQuestion)}
              className="w-full flex items-center justify-between mb-3"
            >
              <div className="flex items-center gap-3">
                <span className="tag tag-accent">{currentAttempt.topic}</span>
                <span className="tag text-xs">{currentAttempt.exercise_type}</span>
                {currentAttempt.question_focus_area && (
                  <span className="text-xs text-gray-500 font-mono uppercase">
                    {currentAttempt.question_focus_area}
                  </span>
                )}
              </div>
              <span className="text-gray-400 text-sm">
                {showQuestion ? 'Hide' : 'Show'} exercise
              </span>
            </button>

            {showQuestion && (
              <>
                <div className="p-4 bg-gray-50 border-l-4 border-black mb-4">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {currentAttempt.question_text}
                  </p>
                </div>

                {currentAttempt.question_key_concepts.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-2">Key concepts:</p>
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
                placeholder="Write your answer here..."
                className={clsx(
                  'w-full h-40 p-4 border-2 border-black bg-white',
                  'text-sm leading-relaxed font-mono',
                  'focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2',
                  'placeholder:text-gray-400',
                  'disabled:bg-gray-100 disabled:cursor-not-allowed',
                  'resize-y min-h-[120px]'
                )}
              />

              <div className="flex justify-between items-center mt-2 text-xs">
                <span className="text-gray-500">
                  {wordCount} words
                </span>
              </div>

              <div className="flex justify-end mt-4">
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !response.trim()}
                  className={clsx(
                    'btn btn-primary',
                    (submitting || !response.trim()) && 'opacity-50 cursor-not-allowed'
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
              <div className="card text-center py-6">
                <div className="mb-2">
                  <span className={clsx('stat-value text-5xl', getScoreColor(grade.score))}>
                    {grade.score.toFixed(1)}
                  </span>
                  <span className="text-xl text-gray-400">/10</span>
                </div>
                {getVerdictBadge(grade.verdict)}
              </div>

              <div className="card">
                <h3 className="font-semibold text-black mb-3">Feedback</h3>
                <p className="text-sm text-gray-700 leading-relaxed">
                  {grade.feedback}
                </p>
              </div>

              {grade.corrections && (
                <div className="card border-l-4 border-l-coral">
                  <h3 className="font-semibold text-black mb-3">Corrections</h3>
                  <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {grade.corrections}
                  </p>
                </div>
              )}

              {grade.missed_concepts.length > 0 && (
                <div className="card border-l-4 border-l-gray-400">
                  <h3 className="font-semibold text-black mb-3">Added to Review Queue</h3>
                  <div className="flex flex-wrap gap-1">
                    {grade.missed_concepts.map((concept, i) => (
                      <span key={i} className="tag text-xs">
                        {concept}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    These will appear in spaced repetition.
                  </p>
                </div>
              )}

              <div className="flex justify-center">
                <button
                  onClick={handleTryAnother}
                  className="btn btn-primary"
                >
                  Try Another Exercise
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="card border-l-4 border-l-coral">
              <p className="text-coral text-sm">{error}</p>
            </div>
          )}

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
                  Evaluating your answer...
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Track Selection */}
      {flowState === 'select' && (
        <>
          <div>
            <h2 className="section-title">Select a Track</h2>
            {tracks.length === 0 ? (
              <div className="card p-8 text-center">
                <p className="text-gray-500 mb-2">No language tracks available yet.</p>
                <p className="text-sm text-gray-400">
                  Ingest a language textbook to create a track.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tracks.map((track) => (
                  <LanguageTrackCard
                    key={track.id}
                    track={track}
                    progress={trackProgress[track.id]}
                    isActive={activeTrackId === track.id}
                    onClick={() => handleTrackSelect(track)}
                  />
                ))}
              </div>
            )}
          </div>

          {history.length > 0 && (
            <div>
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="section-title flex items-center gap-2 cursor-pointer hover:text-gray-700"
              >
                Recent Exercises
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
                          <span className="text-xs text-gray-500 ml-2">
                            {attempt.exercise_type}
                          </span>
                          {attempt.track_name && (
                            <span className="text-xs text-gray-400 ml-2">
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
                  <span className="bg-coral-light text-black text-[10px] font-semibold px-2 py-0.5 border border-coral">
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
                className="w-full mb-4 py-2 px-4 border-2 border-coral text-coral text-sm font-medium hover:bg-coral-light transition-colors disabled:opacity-50"
              >
                {settingActive ? 'Setting...' : 'Set as Active Track for Dashboard'}
              </button>
            )}

            {selectedTrack.description && (
              <p className="text-sm text-gray-600 mb-4">
                {selectedTrack.description}
              </p>
            )}

            {/* Exercise Type */}
            <h3 className="text-sm font-semibold mb-2">Exercise Type</h3>
            <div className="flex flex-wrap gap-2 mb-4">
              {exerciseTypes.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setSelectedExerciseType(type.value)}
                  className={clsx(
                    'tag text-xs cursor-pointer',
                    selectedExerciseType === type.value && 'tag-accent'
                  )}
                >
                  {type.label}
                </button>
              ))}
            </div>

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
                          <span className="text-coral text-sm">completed</span>
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
                    {topic.key_concepts && topic.key_concepts.length > 0 && (
                      <div className="text-xs text-gray-500 mt-1">
                        {topic.key_concepts.slice(0, 3).join(', ')}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>

            <button
              onClick={handleGetExercise}
              disabled={!selectedTopic || generating}
              className={clsx(
                'btn btn-primary w-full',
                (!selectedTopic || generating) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {generating ? 'Generating Exercise...' : 'Get Exercise'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
