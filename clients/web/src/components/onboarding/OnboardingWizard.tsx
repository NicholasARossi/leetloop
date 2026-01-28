'use client'

import { useState, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import { useRouter } from 'next/navigation'
import {
  leetloopApi,
  type OnboardingStatus,
  type ObjectiveTemplateSummary,
  type LearningPathSummary,
  type CreateObjectiveRequest,
} from '@/lib/api'
import { ObjectiveStep } from './steps/ObjectiveStep'
import { ExtensionStep } from './steps/ExtensionStep'
import { HistoryStep } from './steps/HistoryStep'
import { PathStep } from './steps/PathStep'

interface OnboardingWizardProps {
  userId: string
  initialStatus?: OnboardingStatus
}

type StepId = 'objective' | 'extension' | 'history' | 'path'

const steps: { id: StepId; label: string; required: boolean }[] = [
  { id: 'objective', label: 'Set Goal', required: true },
  { id: 'extension', label: 'Install Extension', required: false },
  { id: 'history', label: 'Import History', required: false },
  { id: 'path', label: 'Choose Path', required: true },
]

export function OnboardingWizard({ userId, initialStatus }: OnboardingWizardProps) {
  const router = useRouter()
  const [status, setStatus] = useState<OnboardingStatus | null>(initialStatus || null)
  const [loading, setLoading] = useState(!initialStatus)
  const [error, setError] = useState<string | null>(null)

  // Data for steps
  const [templates, setTemplates] = useState<ObjectiveTemplateSummary[]>([])
  const [paths, setPaths] = useState<LearningPathSummary[]>([])

  const currentStepIndex = status?.current_step ? status.current_step - 1 : 0
  const currentStep = steps[currentStepIndex]?.id || 'objective'

  const loadData = useCallback(async () => {
    try {
      const [statusData, templatesData, pathsData] = await Promise.all([
        initialStatus ? Promise.resolve(initialStatus) : leetloopApi.getOnboardingStatus(userId),
        leetloopApi.getObjectiveTemplates(),
        leetloopApi.getPaths(),
      ])

      setStatus(statusData)
      setTemplates(templatesData)
      setPaths(pathsData)

      // If onboarding is complete, redirect to dashboard
      if (statusData.onboarding_complete) {
        router.push('/dashboard')
      }
    } catch (err) {
      console.error('Failed to load onboarding data:', err)
      setError('Failed to load onboarding data')
    } finally {
      setLoading(false)
    }
  }, [userId, initialStatus, router])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleObjectiveComplete(data: CreateObjectiveRequest) {
    try {
      await leetloopApi.createObjective(userId, data)
      await leetloopApi.updateOnboardingStep(userId, 'objective', true)
      await refreshStatus()
    } catch (err) {
      console.error('Failed to create objective:', err)
      setError('Failed to create objective')
    }
  }

  async function handleExtensionVerified() {
    try {
      await leetloopApi.verifyExtension(userId)
      await refreshStatus()
    } catch (err) {
      console.error('Failed to verify extension:', err)
    }
  }

  async function handleExtensionSkip() {
    try {
      await leetloopApi.skipOnboardingStep(userId, 'extension')
      await refreshStatus()
    } catch (err) {
      console.error('Failed to skip step:', err)
    }
  }

  async function handleHistoryImport() {
    try {
      await leetloopApi.importHistory(userId)
      await refreshStatus()
    } catch (err) {
      console.error('Failed to import history:', err)
    }
  }

  async function handleHistorySkip() {
    try {
      await leetloopApi.skipOnboardingStep(userId, 'history')
      await refreshStatus()
    } catch (err) {
      console.error('Failed to skip step:', err)
    }
  }

  async function handlePathSelect(pathId: string) {
    try {
      await leetloopApi.setCurrentPath(userId, pathId)
      await leetloopApi.updateOnboardingStep(userId, 'path', true)
      await leetloopApi.completeOnboarding(userId)
      router.push('/dashboard')
    } catch (err) {
      console.error('Failed to select path:', err)
      setError('Failed to complete onboarding')
    }
  }

  async function refreshStatus() {
    try {
      const newStatus = await leetloopApi.getOnboardingStatus(userId)
      setStatus(newStatus)

      if (newStatus.onboarding_complete) {
        router.push('/dashboard')
      }
    } catch (err) {
      console.error('Failed to refresh status:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error && !status) {
    return (
      <div className="card p-6 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={loadData} className="btn-primary">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="page-title mb-2">Welcome to LeetLoop</h1>
        <p className="text-gray-600">
          Let&apos;s set up your personalized practice plan.
        </p>
      </div>

      {/* Progress */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {steps.map((step, idx) => (
            <div
              key={step.id}
              className={clsx(
                'flex items-center',
                idx < steps.length - 1 && 'flex-1'
              )}
            >
              <div
                className={clsx(
                  'w-10 h-10 rounded-full border-[2px] border-black flex items-center justify-center text-sm font-bold transition-colors',
                  idx < currentStepIndex && 'bg-accent text-white',
                  idx === currentStepIndex && 'bg-black text-white',
                  idx > currentStepIndex && 'bg-white text-black'
                )}
              >
                {idx < currentStepIndex ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  idx + 1
                )}
              </div>
              {idx < steps.length - 1 && (
                <div className={clsx(
                  'flex-1 h-[2px] mx-2',
                  idx < currentStepIndex ? 'bg-accent' : 'bg-gray-300'
                )} />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between text-xs text-gray-500 px-1">
          {steps.map((step, idx) => (
            <span
              key={step.id}
              className={clsx(
                'text-center',
                idx === currentStepIndex && 'font-bold text-black'
              )}
              style={{ width: '80px' }}
            >
              {step.label}
              {!step.required && <span className="block text-[10px]">(optional)</span>}
            </span>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card-sm bg-red-50 border-l-4 border-l-red-500 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Step Content */}
      <div className="card">
        {currentStep === 'objective' && (
          <ObjectiveStep
            templates={templates}
            onComplete={handleObjectiveComplete}
          />
        )}

        {currentStep === 'extension' && (
          <ExtensionStep
            userId={userId}
            onVerified={handleExtensionVerified}
            onSkip={handleExtensionSkip}
          />
        )}

        {currentStep === 'history' && (
          <HistoryStep
            status={status}
            onImport={handleHistoryImport}
            onSkip={handleHistorySkip}
          />
        )}

        {currentStep === 'path' && (
          <PathStep
            paths={paths}
            onSelect={handlePathSelect}
          />
        )}
      </div>
    </div>
  )
}
