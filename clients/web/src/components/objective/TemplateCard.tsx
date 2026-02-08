'use client'

import { clsx } from 'clsx'
import type { ObjectiveTemplateSummary } from '@/lib/api'

interface TemplateCardProps {
  template: ObjectiveTemplateSummary
  selected: boolean
  onClick: () => void
}

export function TemplateCard({ template, selected, onClick }: TemplateCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'card text-left w-full transition-all border-l-4',
        'border-l-gray-400',
        selected && 'ring-2 ring-accent ring-offset-2',
        !selected && 'hover:translate-y-[-2px]'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-bold text-black">{template.company}</h3>
          <p className="text-sm text-gray-600">
            {template.role} {template.level && `(${template.level})`}
          </p>
        </div>
        {selected && (
          <div className="w-6 h-6 bg-accent rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      {template.description && (
        <p className="text-sm text-gray-500 mb-3 line-clamp-2">
          {template.description}
        </p>
      )}

      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="font-mono">{template.estimated_weeks} weeks</span>
      </div>
    </button>
  )
}
