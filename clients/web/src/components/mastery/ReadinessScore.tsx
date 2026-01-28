'use client'

interface ReadinessScoreProps {
  score: number
  summary: string
}

export function ReadinessScore({ score, summary }: ReadinessScoreProps) {
  return (
    <div className="card reg-corners">
      {/* Section ID header */}
      <div className="flex items-center justify-between mb-4">
        <div className="section-id">RDNS-01</div>
        <div className="coord-display">L{score.toFixed(0)}</div>
      </div>

      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* Score display with schematic frame */}
        <div className="flex-shrink-0 text-center schematic-frame">
          <div className="stat-value text-5xl">
            {score.toFixed(0)}%
          </div>
          <div className="stat-label">Google Readiness</div>
        </div>

        {/* Progress bar and summary */}
        <div className="flex-1 w-full">
          {/* Dimension line label */}
          <div className="dimension-line text-xs text-gray-400 uppercase tracking-wide mb-2">
            <span>{score.toFixed(0)}%</span>
          </div>
          <div className="progress-bar mb-3">
            <div
              className="progress-fill transition-all duration-1000"
              style={{ width: `${Math.min(score, 100)}%` }}
            />
          </div>
          <p className="text-gray-700">{summary}</p>
        </div>

        {/* Target badge with bracket corners */}
        <div className="flex-shrink-0">
          <div className="card-sm bracket-corners">
            <div className="text-xs text-gray-500 uppercase tracking-wide">Target</div>
            <div className="stat-value text-lg">80%+</div>
            <div className="status-light status-light-active mt-2 mx-auto" />
          </div>
        </div>
      </div>
    </div>
  )
}
