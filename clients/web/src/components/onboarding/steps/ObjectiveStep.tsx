'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import {
  leetloopApi,
  type ObjectiveTemplateSummary,
  type ObjectiveTemplate,
  type CreateObjectiveRequest,
} from '@/lib/api'

interface ObjectiveStepProps {
  templates: ObjectiveTemplateSummary[]
  onComplete: (data: CreateObjectiveRequest) => Promise<void>
}

type SubStep = 'template' | 'deadline' | 'pace'

export function ObjectiveStep({ templates, onComplete }: ObjectiveStepProps) {
  const [subStep, setSubStep] = useState<SubStep>('template')
  const [saving, setSaving] = useState(false)

  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<ObjectiveTemplate | null>(null)
  const [title, setTitle] = useState('')
  const [targetDeadline, setTargetDeadline] = useState('')
  const [weeklyTarget, setWeeklyTarget] = useState(25)
  const [dailyMinimum, setDailyMinimum] = useState(4)

  async function handleTemplateSelect(templateId: string) {
    setSelectedTemplateId(templateId)
    try {
      const template = await leetloopApi.getObjectiveTemplate(templateId)
      setSelectedTemplate(template)
      setTitle(`${template.company} ${template.role} ${template.level || ''}`.trim())

      const deadline = new Date()
      deadline.setDate(deadline.getDate() + template.estimated_weeks * 7)
      setTargetDeadline(deadline.toISOString().split('T')[0])
    } catch (err) {
      console.error('Failed to load template:', err)
    }
  }

  async function handleSubmit() {
    if (!selectedTemplate || !targetDeadline) return

    setSaving(true)
    try {
      await onComplete({
        template_id: selectedTemplateId || undefined,
        title,
        target_company: selectedTemplate.company,
        target_role: selectedTemplate.role,
        target_level: selectedTemplate.level,
        target_deadline: targetDeadline,
        weekly_problem_target: weeklyTarget,
        daily_problem_minimum: dailyMinimum,
        required_skills: selectedTemplate.required_skills,
      })
    } finally {
      setSaving(false)
    }
  }

  function goNext() {
    if (subStep === 'template') setSubStep('deadline')
    else if (subStep === 'deadline') setSubStep('pace')
  }

  function goBack() {
    if (subStep === 'pace') setSubStep('deadline')
    else if (subStep === 'deadline') setSubStep('template')
  }

  return (
    <div>
      {subStep === 'template' && (
        <>
          <h2 className="section-title mb-2">What are you preparing for?</h2>
          <p className="text-gray-600 mb-6">
            Select your target company and role. This helps Gemini tailor your daily missions.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {templates.map(template => (
              <button
                key={template.id}
                onClick={() => handleTemplateSelect(template.id)}
                className={clsx(
                  'p-4 text-left border-[2px] transition-all',
                  selectedTemplateId === template.id
                    ? 'border-accent bg-accent/10'
                    : 'border-black bg-white hover:bg-gray-50'
                )}
              >
                <div className="font-bold">{template.company}</div>
                <div className="text-sm text-gray-600">
                  {template.role} {template.level && `(${template.level})`}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  ~{template.estimated_weeks} weeks prep
                </div>
              </button>
            ))}
          </div>

          <div className="flex justify-end mt-6">
            <button
              onClick={goNext}
              disabled={!selectedTemplateId}
              className={clsx(
                'btn-primary',
                !selectedTemplateId && 'opacity-50 cursor-not-allowed'
              )}
            >
              Continue
            </button>
          </div>
        </>
      )}

      {subStep === 'deadline' && (
        <>
          <h2 className="section-title mb-2">When is your deadline?</h2>
          <p className="text-gray-600 mb-6">
            Set your target interview date. Gemini will pace your practice accordingly.
          </p>

          <div className="max-w-sm space-y-4">
            <div>
              <label className="block text-sm font-bold mb-2">Goal Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-2 border-[2px] border-black"
                placeholder="e.g., Google L5 SWE"
              />
            </div>

            <div>
              <label className="block text-sm font-bold mb-2">Target Date</label>
              <input
                type="date"
                value={targetDeadline}
                onChange={(e) => setTargetDeadline(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="w-full px-4 py-2 border-[2px] border-black font-mono"
              />
              {targetDeadline && (
                <p className="mt-1 text-sm text-gray-500">
                  {Math.ceil((new Date(targetDeadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24))} days from now
                </p>
              )}
            </div>
          </div>

          <div className="flex justify-between mt-6">
            <button onClick={goBack} className="btn-secondary">
              Back
            </button>
            <button
              onClick={goNext}
              disabled={!targetDeadline}
              className={clsx(
                'btn-primary',
                !targetDeadline && 'opacity-50 cursor-not-allowed'
              )}
            >
              Continue
            </button>
          </div>
        </>
      )}

      {subStep === 'pace' && (
        <>
          <h2 className="section-title mb-2">Set your weekly commitment</h2>
          <p className="text-gray-600 mb-6">
            How many problems per week? Be realistic - consistency beats intensity.
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
                <span>10</span>
                <span>25</span>
                <span>50</span>
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
                At this pace, you&apos;ll complete approximately{' '}
                <strong className="text-accent">
                  {Math.round(weeklyTarget * Math.ceil((new Date(targetDeadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24 * 7)))}
                </strong>{' '}
                problems before your deadline.
              </p>
            </div>
          )}

          <div className="flex justify-between mt-6">
            <button onClick={goBack} className="btn-secondary">
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={saving}
              className={clsx(
                'btn-primary',
                saving && 'opacity-50 cursor-not-allowed'
              )}
            >
              {saving ? 'Creating...' : 'Set Goal'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
