'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguageTrack } from '@/contexts/LanguageTrackContext'
import {
  leetloopApi,
  type DailyExerciseBatch,
  type DailyExerciseGrade,
} from '@/lib/api'
import {
  ExerciseDashboard,
} from '@/components/language'

export default function LanguagePage() {
  const { userId } = useAuth()
  const { activeTrackId } = useLanguageTrack()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batch, setBatch] = useState<DailyExerciseBatch | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const loadExercises = useCallback(async () => {
    if (!userId || !activeTrackId) return

    setLoading(true)
    setError(null)

    try {
      const data = await leetloopApi.getDailyExercises(userId)
      setBatch(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Échec du chargement des exercices.')
    } finally {
      setLoading(false)
    }
  }, [userId, activeTrackId])

  useEffect(() => {
    loadExercises()
  }, [loadExercises])

  async function handleSubmitExercise(exerciseId: string, responseText: string): Promise<void> {
    const grade: DailyExerciseGrade = await leetloopApi.submitDailyExercise(exerciseId, responseText)

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

  }

  async function handleRegenerate(): Promise<void> {
    if (!userId) return

    setIsRegenerating(true)
    try {
      const data = await leetloopApi.regenerateDailyExercises(userId)
      setBatch(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message || 'Échec de la régénération.')
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
                <span className="text-lg font-bold">AI</span>
              </div>
            </div>
            <p className="text-gray-500 text-sm">Chargement des exercices...</p>
            <p className="text-gray-400 text-xs mt-1">Le premier chargement peut prendre un moment.</p>
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
            <span className="relative z-10">Réessayer</span>
          </button>
        </div>
      )}

      {!loading && !error && batch && (
        <div className="animate-fadeIn">
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
      )}
    </>
  )
}
