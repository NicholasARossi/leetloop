'use client'

import { clsx } from 'clsx'
import type { MissionProblem } from '@/lib/api'

interface MissionProblemCardProps {
  problem: MissionProblem
  index: number
}

const sourceLabels: Record<string, { label: string; color: string }> = {
  path: { label: 'PATH', color: 'bg-blue-100 text-blue-700' },
  gap_fill: { label: 'GAP FILL', color: 'bg-orange-100 text-orange-700' },
  review: { label: 'REVIEW', color: 'bg-purple-100 text-purple-700' },
  reinforcement: { label: 'REINFORCE', color: 'bg-green-100 text-green-700' },
}

const difficultyColors: Record<string, string> = {
  Easy: 'text-green-600',
  easy: 'text-green-600',
  Medium: 'text-yellow-600',
  medium: 'text-yellow-600',
  Hard: 'text-red-600',
  hard: 'text-red-600',
}

export function MissionProblemCard({ problem, index }: MissionProblemCardProps) {
  const leetcodeUrl = `https://leetcode.com/problems/${problem.problem_id}/`
  const sourceInfo = sourceLabels[problem.source] || { label: problem.source.toUpperCase(), color: 'bg-gray-100 text-gray-700' }
  const difficultyClass = difficultyColors[problem.difficulty || problem.estimated_difficulty || ''] || 'text-gray-500'

  return (
    <div
      className={clsx(
        'list-item transition-all',
        problem.completed && 'opacity-60'
      )}
    >
      <div className="flex items-start gap-4">
        {/* Priority number / completion status */}
        <div
          className={clsx(
            'w-8 h-8 flex items-center justify-center border-[2px] border-black font-bold text-sm flex-shrink-0',
            problem.completed ? 'bg-accent text-white' : 'bg-white'
          )}
        >
          {problem.completed ? (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            index + 1
          )}
        </div>

        {/* Problem info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={leetcodeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={clsx(
                'font-medium text-sm hover:text-accent hover:underline',
                problem.completed ? 'line-through text-gray-400' : 'text-black'
              )}
            >
              {problem.problem_title || problem.problem_id.replace(/-/g, ' ')}
            </a>

            {/* Difficulty */}
            {(problem.difficulty || problem.estimated_difficulty) && (
              <span className={clsx('text-xs uppercase font-medium', difficultyClass)}>
                {problem.difficulty || problem.estimated_difficulty}
              </span>
            )}

            {/* Source badge */}
            <span className={clsx('text-[10px] px-1.5 py-0.5 font-bold uppercase', sourceInfo.color)}>
              {sourceInfo.label}
            </span>
          </div>

          {/* Reasoning - always visible */}
          <p className="text-gray-600 text-xs mt-1 leading-relaxed">
            {problem.reasoning}
          </p>

          {/* Skills */}
          {problem.skills && problem.skills.length > 0 && (
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {problem.skills.map((skill) => (
                <span key={skill} className="tag text-[10px]">
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action */}
        {!problem.completed && (
          <a
            href={leetcodeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-xs flex-shrink-0"
          >
            Solve
          </a>
        )}
      </div>
    </div>
  )
}
