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
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 bg-amber-500 rounded-full" />
        <h3 className="font-semibold text-slate-900 dark:text-white">Side Quests</h3>
      </div>

      {/* Quest list */}
      {quests.length === 0 ? (
        <div className="bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/30 rounded-xl p-6 text-center">
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            No side quests today. Complete your main quest!
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {quests.map((quest) => (
            <SideQuestCard key={quest.slug} quest={quest} />
          ))}
        </div>
      )}

      {/* Stats summary */}
      <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl">
        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-3">Quick Stats</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-2xl font-semibold text-slate-900 dark:text-white">{streak}</p>
            <p className="text-slate-500 dark:text-slate-400 text-xs">Day streak</p>
          </div>
          {weeklySuccessRate !== undefined && (
            <div>
              <p className="text-2xl font-semibold text-slate-900 dark:text-white">
                {Math.round(weeklySuccessRate * 100)}%
              </p>
              <p className="text-slate-500 dark:text-slate-400 text-xs">This week</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
