'use client'

import { SideQuest, ProgressTrend, UserStats } from '@/lib/api'
import { SideQuestCard } from './SideQuestCard'
import { ActivityHeatmap } from '@/components/charts/ActivityHeatmap'

interface SideQuestColumnProps {
  quests: SideQuest[]
  streak: number
  trends?: ProgressTrend[]
  stats?: UserStats | null
}

export function SideQuestColumn({ quests, streak, trends, stats }: SideQuestColumnProps) {
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

      {/* Stats summary — heatmap + even data grid */}
      <div className="card-sm mt-6">
        <h4 className="section-id mb-3">Quick Stats</h4>

        {/* Heatmap */}
        {trends && trends.length > 0 && (
          <div className="mb-3">
            <ActivityHeatmap trends={trends} />
          </div>
        )}

        {/* Dimension line separator */}
        <div className="dimension-line mb-3">
          <span className="text-[9px] uppercase tracking-widest text-gray-400 px-2 whitespace-nowrap">Performance</span>
        </div>

        {/* Even 3-column data grid */}
        <div className="grid grid-cols-3 gap-px bg-black border-2 border-black">
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">{streak}</p>
            <p className="stat-label mt-1">Streak</p>
          </div>
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">{stats?.problems_solved ?? '—'}</p>
            <p className="stat-label mt-1">Solved</p>
          </div>
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">{stats ? `${Math.round(stats.success_rate * 100)}%` : '—'}</p>
            <p className="stat-label mt-1">Success</p>
          </div>
        </div>
      </div>
    </div>
  )
}
