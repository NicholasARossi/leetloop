'use client'

import type { OralSubQuestion } from '@/lib/api'

interface SessionProgressProps {
  questions: OralSubQuestion[]
  currentIndex: number
}

export function SessionProgress({ questions, currentIndex }: SessionProgressProps) {
  return (
    <div className="flex items-center gap-2 w-full">
      {questions.map((q, i) => {
        const isCompleted = q.status === 'graded'
        const isCurrent = i === currentIndex
        const isUpcoming = !isCompleted && !isCurrent

        return (
          <div key={q.id} className="flex items-center gap-2 flex-1">
            {/* Step indicator */}
            <div className="flex flex-col items-center flex-1">
              <div className="flex items-center w-full">
                {/* Connector line (before) */}
                {i > 0 && (
                  <div className={`h-0.5 flex-1 ${
                    i <= currentIndex ? 'bg-coral' : 'bg-gray-200'
                  }`} />
                )}

                {/* Step circle */}
                <div className={`
                  w-8 h-8 flex items-center justify-center text-xs font-mono font-bold flex-shrink-0
                  border-2
                  ${isCompleted
                    ? 'bg-coral border-black text-black'
                    : isCurrent
                      ? 'bg-white border-coral text-coral'
                      : 'bg-gray-100 border-gray-300 text-gray-400'
                  }
                `} style={{ clipPath: 'polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px)' }}>
                  {isCompleted ? (
                    <span>{q.overall_score ? Math.round(q.overall_score) : '✓'}</span>
                  ) : (
                    <span>{i + 1}</span>
                  )}
                </div>

                {/* Connector line (after) */}
                {i < questions.length - 1 && (
                  <div className={`h-0.5 flex-1 ${
                    i < currentIndex ? 'bg-coral' : 'bg-gray-200'
                  }`} />
                )}
              </div>

              {/* Label */}
              <span className={`
                text-[10px] font-mono uppercase mt-1 text-center truncate w-full
                ${isCurrent ? 'text-coral' : isCompleted ? 'text-gray-600' : 'text-gray-400'}
              `}>
                {q.focus_area}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
