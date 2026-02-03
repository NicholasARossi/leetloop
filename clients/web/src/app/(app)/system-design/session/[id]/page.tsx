'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type SystemDesignSession,
} from '@/lib/api'
import { QuestionCard } from '@/components/system-design'
import { clsx } from 'clsx'

export default function SessionPage() {
  const params = useParams()
  const router = useRouter()
  const { userId } = useAuth()
  const sessionId = params.id as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<SystemDesignSession | null>(null)
  const [responses, setResponses] = useState<Record<number, string>>({})
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    async function loadSession() {
      if (!sessionId) return

      setLoading(true)
      setError(null)

      try {
        const sessionData = await leetloopApi.getSystemDesignSession(sessionId)

        // Redirect to results if already completed
        if (sessionData.status === 'completed') {
          router.replace(`/system-design/session/${sessionId}/results`)
          return
        }

        setSession(sessionData)

        // Initialize responses from session data
        const initialResponses: Record<number, string> = {}
        for (const q of sessionData.questions) {
          initialResponses[q.id] = q.response || ''
        }
        setResponses(initialResponses)
      } catch (err) {
        console.error('Failed to load session:', err)
        setError('Failed to load session. It may not exist.')
      } finally {
        setLoading(false)
      }
    }

    loadSession()
  }, [sessionId, router])

  const saveResponse = useCallback(async (questionId: number, text: string) => {
    if (!sessionId || saving) return

    setSaving(true)
    try {
      await leetloopApi.submitSystemDesignResponse(sessionId, questionId, text)
    } catch (err) {
      console.error('Failed to save response:', err)
    } finally {
      setSaving(false)
    }
  }, [sessionId, saving])

  // Auto-save on response change (debounced)
  useEffect(() => {
    if (!session) return

    const timeoutId = setTimeout(() => {
      const currentQ = session.questions[currentQuestion]
      const text = responses[currentQ.id] || ''
      if (text.trim()) {
        saveResponse(currentQ.id, text)
      }
    }, 1000)

    return () => clearTimeout(timeoutId)
  }, [responses, currentQuestion, session, saveResponse])

  async function handleSubmitAll() {
    if (!session || submitting) return

    setSubmitting(true)
    setError(null)

    try {
      // Save all responses first
      for (const q of session.questions) {
        const text = responses[q.id] || ''
        if (text.trim()) {
          await leetloopApi.submitSystemDesignResponse(sessionId, q.id, text)
        }
      }

      // Complete session and get grade
      await leetloopApi.completeSystemDesignSession(sessionId)

      // Navigate to results
      router.push(`/system-design/session/${sessionId}/results`)
    } catch (err) {
      console.error('Failed to submit session:', err)
      setError('Failed to submit session. Please try again.')
      setSubmitting(false)
    }
  }

  function handleResponseChange(questionId: number, text: string) {
    setResponses(prev => ({
      ...prev,
      [questionId]: text,
    }))
  }

  function handleNext() {
    if (session && currentQuestion < session.questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1)
    }
  }

  function handlePrev() {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1)
    }
  }

  const getResponseWordCount = (questionId: number) => {
    const text = responses[questionId] || ''
    return text.trim().split(/\s+/).filter(w => w.length > 0).length
  }

  const isAllAnswered = () => {
    if (!session) return false
    return session.questions.every(q => getResponseWordCount(q.id) >= 20)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading session...</div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-600 mb-4">{error || 'Session not found'}</p>
        <button
          onClick={() => router.push('/system-design')}
          className="btn btn-primary"
        >
          Back to System Design
        </button>
      </div>
    )
  }

  const currentQ = session.questions[currentQuestion]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="status-light status-light-active" />
            <h1 className="heading-accent text-lg">{session.topic}</h1>
          </div>
          <div className="flex items-center gap-2">
            {saving && (
              <span className="text-xs text-gray-500">Saving...</span>
            )}
            <span className="tag">
              {currentQuestion + 1} / {session.questions.length}
            </span>
          </div>
        </div>

        {/* Progress indicator */}
        <div className="flex gap-2 mt-4">
          {session.questions.map((q, i) => {
            const wordCount = getResponseWordCount(q.id)
            return (
              <button
                key={q.id}
                onClick={() => setCurrentQuestion(i)}
                className={clsx(
                  'flex-1 h-2 transition-colors',
                  i === currentQuestion ? 'bg-black' :
                  wordCount >= 20 ? 'bg-green-500' :
                  wordCount > 0 ? 'bg-yellow-500' : 'bg-gray-200'
                )}
              />
            )
          })}
        </div>
      </div>

      {/* Current Question */}
      <QuestionCard
        question={currentQ}
        questionNumber={currentQuestion + 1}
        totalQuestions={session.questions.length}
        value={responses[currentQ.id] || ''}
        onChange={(text) => handleResponseChange(currentQ.id, text)}
        disabled={submitting}
      />

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={handlePrev}
          disabled={currentQuestion === 0}
          className={clsx(
            'btn',
            currentQuestion === 0 && 'opacity-50 cursor-not-allowed'
          )}
        >
          Previous
        </button>

        <div className="flex gap-2">
          {currentQuestion < session.questions.length - 1 ? (
            <button
              onClick={handleNext}
              className="btn btn-primary"
            >
              Next Question
            </button>
          ) : (
            <button
              onClick={handleSubmitAll}
              disabled={submitting || !isAllAnswered()}
              className={clsx(
                'btn btn-primary',
                (submitting || !isAllAnswered()) && 'opacity-50 cursor-not-allowed'
              )}
            >
              {submitting ? 'Submitting & Grading...' : 'Submit All & Get Grade'}
            </button>
          )}
        </div>
      </div>

      {/* Answer Status Summary */}
      <div className="card bg-gray-50">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
          Response Status
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {session.questions.map((q, i) => {
            const wordCount = getResponseWordCount(q.id)
            return (
              <div
                key={q.id}
                className="flex items-center justify-between p-2 bg-white border"
              >
                <span className="text-xs font-medium">Q{i + 1}</span>
                <span className={clsx(
                  'text-xs',
                  wordCount >= 20 ? 'text-green-600' :
                  wordCount > 0 ? 'text-yellow-600' : 'text-gray-400'
                )}>
                  {wordCount} words
                </span>
              </div>
            )
          })}
        </div>
        {!isAllAnswered() && (
          <p className="text-xs text-coral mt-3">
            Please write at least 20 words for each question before submitting.
          </p>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="card border-l-4 border-l-coral">
          <p className="text-coral text-sm">{error}</p>
        </div>
      )}

      {/* Grading info */}
      {submitting && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card text-center p-8">
            <div className="animate-pulse mb-4">
              <div className="w-16 h-16 mx-auto border-4 border-black rounded-full flex items-center justify-center">
                <span className="text-2xl">AI</span>
              </div>
            </div>
            <h2 className="heading-accent mb-2">Grading Your Responses</h2>
            <p className="text-sm text-gray-600">
              Our harsh senior-level AI is reviewing your answers...
            </p>
            <p className="text-xs text-gray-400 mt-2">
              This may take a few seconds
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
