'use client'

import { SideQuest } from '@/lib/api'
import { SideQuestCard } from './SideQuestCard'

interface SideQuestColumnProps {
  quests: SideQuest[]
  streak: number
  weeklySuccessRate?: number
}

export function SideQuestColumn({ quests, streak, weeklySuccessRate }: SideQuestColumnProps) {
  return (
    <div>
      <h3 className="section-title">Side Quests</h3>

      {quests.length === 0 ? (
        <div className="card text-center">
          <p className="text-gray-500 text-sm">
            No side quests today. Complete your main quest!
          </p>
        </div>
      ) : (
        <div>
          {quests.map((quest) => (
            <SideQuestCard key={quest.slug} quest={quest} />
          ))}
        </div>
      )}

      {/* Stats summary */}
      <div className="card-sm mt-6">
        <h4 className="text-xs text-gray-500 uppercase tracking-wide mb-4">Quick Stats</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="stat-value">{streak}</p>
            <p className="stat-label">Day streak</p>
          </div>
          {weeklySuccessRate !== undefined && (
            <div>
              <p className="stat-value">
                {Math.round(weeklySuccessRate * 100)}%
              </p>
              <p className="stat-label">This week</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
