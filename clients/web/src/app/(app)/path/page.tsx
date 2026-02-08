'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type LearningPathSummary,
  type PathProgressResponse,
} from '@/lib/api'
import { PathSelector } from '@/components/path/PathSelector'
import { CategorySection } from '@/components/path/CategorySection'

export default function PathPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [paths, setPaths] = useState<LearningPathSummary[]>([])
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null)
  const [pathProgress, setPathProgress] = useState<PathProgressResponse | null>(null)

  // Load available paths
  useEffect(() => {
    async function loadPaths() {
      try {
        const pathsList = await leetloopApi.getPaths()
        setPaths(pathsList)

        // If no path selected, try to load current path
        if (!selectedPathId && userId) {
          try {
            const current = await leetloopApi.getCurrentPath(userId)
            setSelectedPathId(current.path.id)
            setPathProgress(current)
          } catch {
            // No current path, default to first available
            if (pathsList.length > 0) {
              setSelectedPathId(pathsList[0].id)
            }
          }
        }
      } catch (err) {
        console.error('Failed to load paths:', err)
        setError('Failed to load learning paths.')
      } finally {
        setLoading(false)
      }
    }

    loadPaths()
  }, [userId, selectedPathId])

  // Load path progress when selection changes
  useEffect(() => {
    async function loadPathProgress() {
      if (!userId || !selectedPathId) return

      setLoading(true)
      try {
        const progress = await leetloopApi.getPathProgress(selectedPathId, userId)
        setPathProgress(progress)

        // Set this as current path
        await leetloopApi.setCurrentPath(userId, selectedPathId)
      } catch (err) {
        console.error('Failed to load path progress:', err)
        setError('Failed to load path progress.')
      } finally {
        setLoading(false)
      }
    }

    if (selectedPathId && pathProgress?.path.id !== selectedPathId) {
      loadPathProgress()
    }
  }, [userId, selectedPathId, pathProgress?.path.id])

  if (loading && !pathProgress) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading path...</div>
      </div>
    )
  }

  if (error && !pathProgress) {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error}</p>
        <p className="text-sm text-gray-500">
          Make sure the backend API is running.
        </p>
      </div>
    )
  }

  const progress = pathProgress?.completion_percentage || 0
  const completedCount = pathProgress?.completed_count || 0
  const totalProblems = pathProgress?.path.total_problems || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <PathSelector
              paths={paths}
              selectedPathId={selectedPathId}
              onSelect={setSelectedPathId}
              loading={loading}
            />
          </div>

          {pathProgress && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="stat-value text-2xl">
                  {completedCount}/{totalProblems}
                </div>
                <div className="stat-label">
                  {progress.toFixed(1)}% complete
                </div>
              </div>

              {/* Circular progress */}
              <div className="relative w-16 h-16">
                <svg className="w-full h-full -rotate-90">
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="6"
                    className="text-gray-200"
                  />
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="6"
                    strokeLinecap="square"
                    strokeDasharray={2 * Math.PI * 28}
                    strokeDashoffset={2 * Math.PI * 28 * (1 - progress / 100)}
                    className="text-coral transition-all duration-500"
                  />
                </svg>
              </div>
            </div>
          )}
        </div>

        {pathProgress?.path.description && (
          <p className="mt-4 text-sm text-gray-600">
            {pathProgress.path.description}
          </p>
        )}
      </div>

      {/* Categories */}
      {pathProgress && (
        <div className="space-y-3">
          {pathProgress.path.categories
            .sort((a, b) => a.order - b.order)
            .map((category, idx) => {
              const catProgress = pathProgress.categories_progress[category.name]
              return (
                <CategorySection
                  key={category.name}
                  name={category.name}
                  total={catProgress?.total || category.problems.length}
                  completed={catProgress?.completed || 0}
                  problems={catProgress?.problems || category.problems.map(p => ({
                    ...p,
                    completed: false,
                  }))}
                  defaultOpen={idx === 0 && catProgress?.completed < catProgress?.total}
                />
              )
            })}
        </div>
      )}
    </div>
  )
}
