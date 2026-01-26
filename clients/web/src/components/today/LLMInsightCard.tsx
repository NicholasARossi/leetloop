'use client'

interface LLMInsightCardProps {
  insight: string | null | undefined
}

export function LLMInsightCard({ insight }: LLMInsightCardProps) {
  if (!insight) {
    return null
  }

  return (
    <div className="card p-4 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 border-purple-200 dark:border-purple-800">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <span className="text-2xl">💡</span>
        </div>
        <div>
          <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-1">
            AI Insight
          </h3>
          <p className="text-sm text-purple-800 dark:text-purple-200">
            {insight}
          </p>
        </div>
      </div>
    </div>
  )
}
