'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type MLCodingDailyBatch,
  type MLCodingExerciseGrade,
} from '@/lib/api'
import { MLCodingDashboard } from '@/components/ml-coding'

export default function MLCodingPage() {
  const { userId } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batch, setBatch] = useState<MLCodingDailyBatch | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const loadExercises = useCallback(async () => {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      const data = await leetloopApi.getMLCodingDailyExercises(userId)
      setBatch(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to load exercises.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadExercises()
  }, [loadExercises])

  async function handleSubmitExercise(exerciseId: string, code: string): Promise<void> {
    const grade: MLCodingExerciseGrade = await leetloopApi.submitMLCodingExercise(exerciseId, code)

    setBatch((prev) => {
      if (!prev) return prev
      const updatedExercises = prev.exercises.map((ex) => {
        if (ex.id === exerciseId) {
          return {
            ...ex,
            status: 'completed' as const,
            submitted_code: code,
            score: grade.score,
            verdict: grade.verdict,
            feedback: grade.feedback,
            correctness_score: grade.correctness_score,
            code_quality_score: grade.code_quality_score,
            math_understanding_score: grade.math_understanding_score,
            missed_concepts: grade.missed_concepts,
            suggested_improvements: grade.suggested_improvements,
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
  }

  async function handleRegenerate(): Promise<void> {
    if (!userId) return

    setIsRegenerating(true)
    try {
      const data = await leetloopApi.regenerateMLCodingExercises(userId)
      setBatch(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Failed to regenerate.')
    } finally {
      setIsRegenerating(false)
    }
  }

  return (
    <>
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-pulse mb-3">
              <div className="w-12 h-12 mx-auto border-3 border-black rounded-full flex items-center justify-center">
                <span className="text-lg font-bold">ML</span>
              </div>
            </div>
            <p className="text-gray-500 text-sm">Loading ML coding drills...</p>
            <p className="text-gray-400 text-xs mt-1">First load may take a moment to generate problems.</p>
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="card mb-4" style={{ borderLeftWidth: '4px', borderLeftColor: 'var(--accent-color)' }}>
          <p style={{ color: 'var(--accent-color-dark)' }} className="text-sm">{error}</p>
          <button
            onClick={loadExercises}
            className="btn-primary mt-2 text-xs px-3 py-1"
          >
            <span className="relative z-10">Retry</span>
          </button>
        </div>
      )}

      {!loading && !error && batch && (
        <div className="animate-fadeIn">
          <MLCodingDashboard
            exercises={batch.exercises}
            completedCount={batch.completed_count}
            totalCount={batch.total_count}
            averageScore={batch.average_score}
            onSubmitExercise={handleSubmitExercise}
            onRegenerate={handleRegenerate}
            isRegenerating={isRegenerating}
          />
        </div>
      )}
    </>
  )
}
