'use client'

import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import {
  leetloopApi,
  type ObjectiveTemplateSummary,
  type ObjectiveTemplate,
  type CreateObjectiveRequest,
  type LearningPathSummary,
} from '@/lib/api'
import { TemplateCard } from './TemplateCard'
import { SkillTargetTable } from './SkillTargetTable'

interface ObjectiveSetupWizardProps {
  userId: string
  onComplete: () => void
}

type WizardStep = 'template' | 'deadline' | 'pace' | 'skills' | 'confirm'

const steps: { id: WizardStep; label: string }[] = [
  { id: 'template', label: 'Choose Target' },
  { id: 'deadline', label: 'Set Deadline' },
  { id: 'pace', label: 'Weekly Pace' },
  { id: 'skills', label: 'Skill Targets' },
  { id: 'confirm', label: 'Confirm' },
]

export function ObjectiveSetupWizard({ userId, onComplete }: ObjectiveSetupWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>('template')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Data
  const [templates, setTemplates] = useState<ObjectiveTemplateSummary[]>([])
  const [paths, setPaths] = useState<LearningPathSummary[]>([])

  // Form state
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<ObjectiveTemplate | null>(null)
  const [title, setTitle] = useState('')
  const [targetDeadline, setTargetDeadline] = useState('')
  const [weeklyTarget, setWeeklyTarget] = useState(25)
  const [dailyMinimum, setDailyMinimum] = useState(4)
  const [requiredSkills, setRequiredSkills] = useState<Record<string, number>>({})
  const [selectedPathIds, setSelectedPathIds] = useState<string[]>([])

  useEffect(() => {
    async function loadData() {
      try {
        const [templatesData, pathsData] = await Promise.all([
          leetloopApi.getObjectiveTemplates(),
          leetloopApi.getPaths(),
        ])
        setTemplates(templatesData)
        setPaths(pathsData)
      } catch (err) {
        console.error('Failed to load data:', err)
        setError('Failed to load templates')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  async function handleTemplateSelect(templateId: string) {
    setSelectedTemplateId(templateId)
    try {
      const template = await leetloopApi.getObjectiveTemplate(templateId)
      setSelectedTemplate(template)
      setTitle(`${template.company} ${template.role} ${template.level || ''}`.trim())
      setRequiredSkills(template.required_skills)

      // Set default deadline based on estimated weeks
      const deadline = new Date()
      deadline.setDate(deadline.getDate() + template.estimated_weeks * 7)
      setTargetDeadline(deadline.toISOString().split('T')[0])
    } catch (err) {
      console.error('Failed to load template:', err)
    }
  }

  async function handleSubmit() {
    if (!selectedTemplateId) return

    setSaving(true)
    setError(null)

    try {
      const request: CreateObjectiveRequest = {
        template_id: selectedTemplateId,
        title,
        target_company: selectedTemplate?.company || '',
        target_role: selectedTemplate?.role || '',
        target_level: selectedTemplate?.level,
        target_deadline: targetDeadline,
        weekly_problem_target: weeklyTarget,
        daily_problem_minimum: dailyMinimum,
        required_skills: requiredSkills,
        path_ids: selectedPathIds,
      }

      await leetloopApi.createObjective(userId, request)
      onComplete()
    } catch (err) {
      console.error('Failed to create objective:', err)
      setError('Failed to create objective. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  function goNext() {
    const idx = steps.findIndex(s => s.id === currentStep)
    if (idx < steps.length - 1) {
      setCurrentStep(steps[idx + 1].id)
    }
  }

  function goBack() {
    const idx = steps.findIndex(s => s.id === currentStep)
    if (idx > 0) {
      setCurrentStep(steps[idx - 1].id)
    }
  }

  function canProceed(): boolean {
    switch (currentStep) {
      case 'template':
        return !!selectedTemplateId
      case 'deadline':
        return !!targetDeadline
      case 'pace':
        return weeklyTarget >= 10 && weeklyTarget <= 50
      case 'skills':
        return Object.keys(requiredSkills).length > 0
      case 'confirm':
        return true
      default:
        return false
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading templates...</div>
      </div>
    )
  }

  const currentStepIndex = steps.findIndex(s => s.id === currentStep)

  return (
    <div className="max-w-3xl mx-auto">
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
                  'w-8 h-8 rounded-full border-[2px] border-black flex items-center justify-center text-sm font-bold transition-colors',
                  idx < currentStepIndex && 'bg-accent text-white',
                  idx === currentStepIndex && 'bg-black text-white',
                  idx > currentStepIndex && 'bg-white text-black'
                )}
              >
                {idx < currentStepIndex ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        <div className="text-center">
          <span className="text-sm text-gray-500">
            Step {currentStepIndex + 1} of {steps.length}:
          </span>
          <span className="text-sm font-bold ml-1">
            {steps[currentStepIndex].label}
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-l-4 border-l-coral mb-6">
          <p className="text-coral">{error}</p>
        </div>
      )}

      {/* Step Content */}
      <div className="card mb-6">
        {currentStep === 'template' && (
          <div>
            <h2 className="section-title mb-4">What are you preparing for?</h2>
            <p className="text-gray-600 mb-6">
              Select a target company and role. This will set skill targets based on typical interview patterns.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {templates.map(template => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  selected={selectedTemplateId === template.id}
                  onClick={() => handleTemplateSelect(template.id)}
                />
              ))}
            </div>
          </div>
        )}

        {currentStep === 'deadline' && (
          <div>
            <h2 className="section-title mb-4">When is your deadline?</h2>
            <p className="text-gray-600 mb-6">
              Set a target date for your interview. This drives your weekly pace calculations.
            </p>
            <div className="max-w-sm">
              <label className="block text-sm font-bold mb-2">Target Date</label>
              <input
                type="date"
                value={targetDeadline}
                onChange={(e) => setTargetDeadline(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="w-full px-4 py-2 border-[2px] border-black text-lg font-mono"
              />
              {targetDeadline && (
                <p className="mt-2 text-sm text-gray-500">
                  {Math.ceil((new Date(targetDeadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24))} days from now
                </p>
              )}
            </div>

            <div className="mt-6 max-w-sm">
              <label className="block text-sm font-bold mb-2">Goal Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Google L5 SWE"
                className="w-full px-4 py-2 border-[2px] border-black"
              />
            </div>
          </div>
        )}

        {currentStep === 'pace' && (
          <div>
            <h2 className="section-title mb-4">Set your weekly pace</h2>
            <p className="text-gray-600 mb-6">
              How many problems can you commit to solving each week? Be realistic - consistency beats intensity.
            </p>

            <div className="max-w-sm space-y-6">
              <div>
                <label className="block text-sm font-bold mb-2">
                  Weekly Target: <span className="text-accent">{weeklyTarget} problems</span>
                </label>
                <input
                  type="range"
                  min={10}
                  max={50}
                  value={weeklyTarget}
                  onChange={(e) => setWeeklyTarget(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>10 (casual)</span>
                  <span>25 (standard)</span>
                  <span>50 (intense)</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2">
                  Daily Minimum: <span className="text-accent">{dailyMinimum} problems</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={dailyMinimum}
                  onChange={(e) => setDailyMinimum(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1</span>
                  <span>5</span>
                  <span>10</span>
                </div>
              </div>
            </div>

            {targetDeadline && (
              <div className="mt-6 p-4 bg-gray-100 border-[2px] border-black">
                <p className="text-sm">
                  At {weeklyTarget} problems/week, you&apos;ll complete approximately{' '}
                  <strong className="text-accent">
                    {Math.round(weeklyTarget * Math.ceil((new Date(targetDeadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24 * 7)))} problems
                  </strong>{' '}
                  before your deadline.
                </p>
              </div>
            )}
          </div>
        )}

        {currentStep === 'skills' && (
          <div>
            <h2 className="section-title mb-4">Review skill targets</h2>
            <p className="text-gray-600 mb-6">
              These are the skill scores you need to achieve. Adjust if needed based on your current level.
            </p>
            <SkillTargetTable
              skills={requiredSkills}
              editable
              onChange={setRequiredSkills}
            />
          </div>
        )}

        {currentStep === 'confirm' && selectedTemplate && (
          <div>
            <h2 className="section-title mb-4">Confirm your objective</h2>

            <div className="space-y-4">
              <div className="p-4 bg-gray-100 border-[2px] border-black">
                <h3 className="font-bold text-lg">{title}</h3>
                <p className="text-gray-600">
                  {selectedTemplate.company} {selectedTemplate.role}
                  {selectedTemplate.level && ` (${selectedTemplate.level})`}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Deadline:</span>
                  <span className="font-bold ml-2">{new Date(targetDeadline).toLocaleDateString()}</span>
                </div>
                <div>
                  <span className="text-gray-500">Weekly Pace:</span>
                  <span className="font-bold ml-2">{weeklyTarget} problems</span>
                </div>
                <div>
                  <span className="text-gray-500">Daily Minimum:</span>
                  <span className="font-bold ml-2">{dailyMinimum} problems</span>
                </div>
                <div>
                  <span className="text-gray-500">Skill Targets:</span>
                  <span className="font-bold ml-2">{Object.keys(requiredSkills).length} domains</span>
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-bold mb-2">Required Skills</h4>
                <SkillTargetTable skills={requiredSkills} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={goBack}
          disabled={currentStepIndex === 0}
          className={clsx(
            'btn-secondary',
            currentStepIndex === 0 && 'opacity-50 cursor-not-allowed'
          )}
        >
          Back
        </button>

        {currentStep !== 'confirm' ? (
          <button
            onClick={goNext}
            disabled={!canProceed()}
            className={clsx(
              'btn-primary',
              !canProceed() && 'opacity-50 cursor-not-allowed'
            )}
          >
            Continue
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={saving || !canProceed()}
            className={clsx(
              'btn-primary',
              (saving || !canProceed()) && 'opacity-50 cursor-not-allowed'
            )}
          >
            {saving ? 'Creating...' : 'Create Objective'}
          </button>
        )}
      </div>
    </div>
  )
}
