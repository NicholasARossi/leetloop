'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type MetaObjectiveResponse,
  ApiError,
} from '@/lib/api'
import { ObjectiveSetupWizard } from '@/components/objective/ObjectiveSetupWizard'
import { ObjectiveStatus } from '@/components/objective/ObjectiveStatus'

export default function ObjectivePage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<MetaObjectiveResponse | null>(null)
  const [showWizard, setShowWizard] = useState(false)

  async function loadObjective() {
    if (!userId) return

    setLoading(true)
    setError(null)

    try {
      const objectiveData = await leetloopApi.getObjective(userId)
      setData(objectiveData)
      setShowWizard(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // No active objective - show wizard
        setData(null)
        setShowWizard(true)
      } else {
        console.error('Failed to load objective:', err)
        setError('Failed to load objective data. Make sure the backend is running.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadObjective()
  }, [userId])

  function handleWizardComplete() {
    loadObjective()
  }

  function handleEdit() {
    setShowWizard(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading objective...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error}</p>
        <p className="text-sm text-gray-500">
          Make sure the backend API is running.
        </p>
      </div>
    )
  }

  // Show wizard if no objective or user wants to edit
  if (showWizard || !data) {
    return (
      <div className="py-6">
        <div className="text-center mb-8">
          <h1 className="heading-accent text-3xl mb-2">Set Your Objective</h1>
          <p className="text-gray-600">
            Define your career goal and let LeetLoop drive you to success.
          </p>
        </div>
        {userId && (
          <ObjectiveSetupWizard
            userId={userId}
            onComplete={handleWizardComplete}
          />
        )}
      </div>
    )
  }

  // Show current objective status
  return (
    <div className="space-y-6">
      <ObjectiveStatus data={data} onEdit={handleEdit} />
    </div>
  )
}
