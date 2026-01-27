'use client'

import { MainQuest } from '@/lib/api'
import { QuestItem } from './QuestItem'

interface MainQuestColumnProps {
  quests: MainQuest[]
}

export function MainQuestColumn({ quests }: MainQuestColumnProps) {
  return (
    <div>
      <h3 className="section-title">Main Quests</h3>

      {quests.length === 0 ? (
        <div className="card text-center">
          <p className="text-gray-500">
            No quests available. Select a learning path to get started.
          </p>
        </div>
      ) : (
        <div>
          {quests.map((quest, index) => (
            <QuestItem key={quest.slug} quest={quest} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}
