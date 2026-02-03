'use client'

import { clsx } from 'clsx'
import type { QuestionGrade } from '@/lib/api'

interface RubricBreakdownProps {
  questionGrades: QuestionGrade[]
  questions: { id: number; text: string; focus_area: string }[]
}

export function RubricBreakdown({ questionGrades, questions }: RubricBreakdownProps) {
  const getScoreColor = (score: number, max: number = 10) => {
    const normalized = score / max
    if (normalized >= 0.7) return 'bg-green-500'
    if (normalized >= 0.5) return 'bg-yellow-500'
    return 'bg-coral'
  }

  const getRubricScoreDisplay = (score: number) => {
    // Score is 1-3
    return (
      <div className="flex gap-1">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className={clsx(
              'w-4 h-4 border border-black',
              n <= score ? 'bg-black' : 'bg-white'
            )}
          />
        ))}
      </div>
    )
  }

  const rubricLabels: Record<string, string> = {
    depth: 'Depth',
    tradeoffs: 'Tradeoffs',
    clarity: 'Clarity',
    scalability: 'Scalability',
  }

  return (
    <div className="space-y-6">
      <h2 className="section-title">Question Breakdown</h2>

      {questionGrades.map((qg, index) => {
        const question = questions.find(q => q.id === qg.question_id)

        return (
          <div key={qg.question_id} className="card">
            {/* Question Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="tag">Q{index + 1}</span>
                <span className="text-xs text-gray-500 font-mono uppercase">
                  {question?.focus_area || 'General'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={clsx(
                  'text-2xl font-bold',
                  qg.score >= 7 ? 'text-green-600' :
                  qg.score >= 5 ? 'text-yellow-600' : 'text-coral'
                )}>
                  {qg.score.toFixed(1)}
                </span>
                <span className="text-gray-400">/10</span>
              </div>
            </div>

            {/* Question Text (collapsed) */}
            {question && (
              <details className="mb-4">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-black">
                  View question
                </summary>
                <p className="text-sm text-gray-600 mt-2 p-3 bg-gray-50 border-l-2 border-gray-300">
                  {question.text}
                </p>
              </details>
            )}

            {/* Feedback */}
            <div className="mb-4 p-3 bg-gray-50">
              <p className="text-sm text-gray-700 leading-relaxed">
                {qg.feedback}
              </p>
            </div>

            {/* Rubric Scores */}
            {qg.rubric_scores.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3">
                  Rubric Scores
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  {qg.rubric_scores.map((rs) => (
                    <div key={rs.dimension} className="flex items-center justify-between p-2 bg-gray-50">
                      <div>
                        <span className="text-sm font-medium">
                          {rubricLabels[rs.dimension] || rs.dimension}
                        </span>
                        {rs.feedback && (
                          <p className="text-xs text-gray-500 mt-1">
                            {rs.feedback}
                          </p>
                        )}
                      </div>
                      {getRubricScoreDisplay(rs.score)}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Missed Concepts */}
            {qg.missed_concepts.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-coral uppercase mb-2">
                  Missed Concepts
                </h4>
                <div className="flex flex-wrap gap-1">
                  {qg.missed_concepts.map((concept, i) => (
                    <span key={i} className="tag text-xs bg-red-50 border-coral text-coral">
                      {concept}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      })}

      {/* Rubric Legend */}
      <div className="card bg-gray-50">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
          Rubric Scoring Guide
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-600">
          <div>
            <span className="font-medium">Depth</span>
            <p>Edge cases, failure modes, implementation details</p>
          </div>
          <div>
            <span className="font-medium">Tradeoffs</span>
            <p>CAP theorem, latency/consistency, cost/performance</p>
          </div>
          <div>
            <span className="font-medium">Clarity</span>
            <p>Structure, explainability, logical flow</p>
          </div>
          <div>
            <span className="font-medium">Scalability</span>
            <p>Numbers, estimates, growth planning</p>
          </div>
        </div>
        <div className="flex items-center gap-4 mt-4 pt-3 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              <div className="w-3 h-3 border border-black bg-black" />
              <div className="w-3 h-3 border border-black bg-white" />
              <div className="w-3 h-3 border border-black bg-white" />
            </div>
            <span className="text-xs">Basic</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              <div className="w-3 h-3 border border-black bg-black" />
              <div className="w-3 h-3 border border-black bg-black" />
              <div className="w-3 h-3 border border-black bg-white" />
            </div>
            <span className="text-xs">Solid</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              <div className="w-3 h-3 border border-black bg-black" />
              <div className="w-3 h-3 border border-black bg-black" />
              <div className="w-3 h-3 border border-black bg-black" />
            </div>
            <span className="text-xs">Expert</span>
          </div>
        </div>
      </div>
    </div>
  )
}
