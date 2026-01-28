'use client'

import type { MetaObjectiveResponse, SkillGap } from '@/lib/api'
import { PaceIndicator } from './PaceIndicator'

interface ObjectiveStatusProps {
  data: MetaObjectiveResponse
  onEdit: () => void
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function SkillGapBar({ gap }: { gap: SkillGap }) {
  const percentageFilled = (gap.current_score / gap.target_score) * 100

  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium">{gap.domain}</span>
        <span className="font-mono text-gray-500">
          {gap.current_score.toFixed(0)} / {gap.target_score}
        </span>
      </div>
      <div className="h-3 bg-gray-200 border-[2px] border-black overflow-hidden">
        <div
          className="h-full bg-accent transition-all"
          style={{ width: `${Math.min(100, percentageFilled)}%` }}
        />
      </div>
    </div>
  )
}

export function ObjectiveStatus({ data, onEdit }: ObjectiveStatusProps) {
  const { objective, pace_status, skill_gaps, days_remaining, total_days, problems_solved, total_problems_target, readiness_percentage } = data

  const progressPercentage = (problems_solved / total_problems_target) * 100
  const timePercentage = ((total_days - days_remaining) / total_days) * 100

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card reg-corners">
        <div className="flex items-center justify-between mb-2">
          <div className="section-id">OBJ-01</div>
          <div className="coord-display">D{days_remaining}</div>
        </div>

        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="heading-accent text-2xl mb-1">{objective.title}</h1>
            <p className="text-gray-600">
              {objective.target_company} {objective.target_role}
              {objective.target_level && ` (${objective.target_level})`}
            </p>
          </div>
          <button
            onClick={onEdit}
            className="btn-secondary text-sm"
          >
            Edit Goal
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center bracket-corners p-4 bg-gray-50 border border-gray-200">
          <div>
            <div className="text-3xl font-mono font-bold text-coral">{days_remaining}</div>
            <div className="text-xs text-gray-500">Days Left</div>
          </div>
          <div>
            <div className="text-3xl font-mono font-bold text-black">{problems_solved}</div>
            <div className="text-xs text-gray-500">Problems Solved</div>
          </div>
          <div>
            <div className="text-3xl font-mono font-bold text-black">{total_problems_target}</div>
            <div className="text-xs text-gray-500">Target Problems</div>
          </div>
          <div>
            <div className="text-3xl font-mono font-bold text-coral">{readiness_percentage.toFixed(0)}%</div>
            <div className="text-xs text-gray-500">Readiness</div>
          </div>
        </div>

        {/* Progress bars */}
        <div className="mt-6 space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Problems Progress</span>
              <span className="font-mono">{progressPercentage.toFixed(0)}%</span>
            </div>
            <div className="h-4 bg-gray-200 border-[2px] border-black overflow-hidden">
              <div
                className="h-full bg-accent transition-all"
                style={{ width: `${Math.min(100, progressPercentage)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Time Elapsed</span>
              <span className="font-mono">{timePercentage.toFixed(0)}%</span>
            </div>
            <div className="h-4 bg-gray-200 border-[2px] border-black overflow-hidden">
              <div
                className="h-full bg-gray-400 transition-all"
                style={{ width: `${Math.min(100, timePercentage)}%` }}
              />
            </div>
          </div>
        </div>

        <div className="mt-4 text-sm text-gray-500">
          Deadline: {formatDate(objective.target_deadline)} |
          Started: {formatDate(objective.started_at)} |
          Pace: {objective.weekly_problem_target} problems/week
        </div>
      </div>

      {/* Pace Indicator */}
      <PaceIndicator pace={pace_status} />

      {/* Skill Gaps */}
      {skill_gaps.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="section-id">SKL-02</div>
            <h2 className="section-title mb-0 border-b-0 pb-0">Skill Progress</h2>
          </div>
          <div className="space-y-4">
            {skill_gaps.map(gap => (
              <SkillGapBar key={gap.domain} gap={gap} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
