'use client'

import { MainQuest } from '@/lib/api'
import { QuestItem } from './QuestItem'

interface MainQuestColumnProps {
  quests: MainQuest[]
}

export function MainQuestColumn({ quests }: MainQuestColumnProps) {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 bg-sky-500 rounded-full" />
        <h3 className="font-semibold text-slate-900 dark:text-white">Main Quest</h3>
        <span className="text-slate-500 dark:text-slate-400 text-sm">NeetCode 150 Path</span>
      </div>

      {/* Quest list */}
      {quests.length === 0 ? (
        <div className="bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700/30 rounded-xl p-8 text-center">
          <p className="text-slate-500 dark:text-slate-400">
            No quests available. Select a learning path to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {quests.map((quest, index) => (
            <QuestItem key={quest.slug} quest={quest} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}
