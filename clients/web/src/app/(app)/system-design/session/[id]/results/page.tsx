'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  leetloopApi,
  type SystemDesignSession,
  type SystemDesignGrade,
} from '@/lib/api'
import { GradeDisplay, RubricBreakdown } from '@/components/system-design'

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const sessionId = params.id as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<SystemDesignSession | null>(null)
  const [grade, setGrade] = useState<SystemDesignGrade | null>(null)

  useEffect(() => {
    async function loadResults() {
      if (!sessionId) return

      setLoading(true)
      setError(null)

      try {
        const [sessionData, gradeData] = await Promise.all([
          leetloopApi.getSystemDesignSession(sessionId),
          leetloopApi.getSystemDesignGrade(sessionId),
        ])

        // Redirect to session if not completed
        if (sessionData.status !== 'completed') {
          router.replace(`/system-design/session/${sessionId}`)
          return
        }

        setSession(sessionData)
        setGrade(gradeData)
      } catch (err) {
        console.error('Failed to load results:', err)
        setError('Failed to load results. The session may not be graded yet.')
      } finally {
        setLoading(false)
      }
    }

    loadResults()
  }, [sessionId, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading results...</div>
      </div>
    )
  }

  if (error || !session || !grade) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-600 mb-4">{error || 'Results not found'}</p>
        <button
          onClick={() => router.push('/system-design')}
          className="btn btn-primary"
        >
          Back to System Design
        </button>
      </div>
    )
  }

  const questions = session.questions.map(q => ({
    id: q.id,
    text: q.text,
    focus_area: q.focus_area,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="status-light status-light-active" />
            <h1 className="heading-accent text-lg">{session.topic}</h1>
          </div>
          <button
            onClick={() => router.push('/system-design')}
            className="btn"
          >
            Back to Tracks
          </button>
        </div>
        {session.completed_at && (
          <p className="text-xs text-gray-500 mt-2">
            Completed {new Date(session.completed_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* Grade Display */}
      <GradeDisplay grade={grade} />

      {/* Rubric Breakdown */}
      <RubricBreakdown
        questionGrades={grade.question_grades}
        questions={questions}
      />

      {/* Actions */}
      <div className="card flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Ready to try another topic?
        </p>
        <button
          onClick={() => router.push('/system-design')}
          className="btn btn-primary"
        >
          Start New Session
        </button>
      </div>
    </div>
  )
}
