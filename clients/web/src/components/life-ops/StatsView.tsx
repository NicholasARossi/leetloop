'use client'

import { StreakDisplay } from './StreakDisplay'
import { CompletionChart } from './CompletionChart'
import type { LifeOpsStatsResponse } from '@/lib/api'

interface StatsViewProps {
  stats: LifeOpsStatsResponse
}

export function StatsView({ stats }: StatsViewProps) {
  return (
    <div>
      <StreakDisplay streak={stats.streak} />
      <CompletionChart title="Weekly Completion" rates={stats.weekly_rates} />
      <CompletionChart title="Monthly Completion" rates={stats.monthly_rates} />
    </div>
  )
}
