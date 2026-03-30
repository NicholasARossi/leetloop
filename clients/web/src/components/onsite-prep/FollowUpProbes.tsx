'use client'

import { useState, useCallback } from 'react'
import { AudioRecorder } from '@/components/system-design/AudioRecorder'
import { leetloopApi, type OnsitePrepFollowUp, type ConversationalFollowUpResult } from '@/lib/api'

interface FollowUpProbesProps {
  attemptId: string
  followUps: OnsitePrepFollowUp[]
  category: string
  onDone: () => void
}

function getScoreBadge(score: number | undefined): string {
  if (score === undefined) return 'badge-default'
  if (score >= 4) return 'badge-pass'
  if (score >= 3) return 'badge-warn'
  return 'badge-fail'
}

export function FollowUpProbes({ attemptId, followUps: initialFollowUps, category, onDone }: FollowUpProbesProps) {
  const [followUps, setFollowUps] = useState(initialFollowUps)
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversationComplete, setConversationComplete] = useState(false)
  const [expandedIdeal, setExpandedIdeal] = useState<Set<number>>(new Set())

  const completedCount = followUps.filter(fu => fu.score !== undefined && fu.score !== null).length
  const allAnswered = completedCount === followUps.length && followUps.length > 0
  const avgScore = completedCount > 0
    ? followUps.filter(fu => fu.score != null).reduce((sum, fu) => sum + (fu.score || 0), 0) / completedCount
    : null

  const suggestedMinutes = category === 'design' ? 1.5 : 1

  const handleSubmit = useCallback(async (blob: Blob, followUpId: string, index: number) => {
    setIsUploading(true)
    setError(null)
    try {
      const result: ConversationalFollowUpResult = await leetloopApi.submitOnsitePrepFollowUpAudio(followUpId, blob)

      // Update the graded follow-up
      setFollowUps(prev => {
        const updated = prev.map((fu, i) =>
          i === index ? { ...fu, transcript: result.transcript, score: result.score, feedback: result.feedback, addressed_gap: result.addressed_gap, ideal_answer: result.ideal_answer } : fu
        )

        // Append next follow-up if generated
        if (result.next_follow_up) {
          updated.push(result.next_follow_up)
        }

        return updated
      })

      setActiveIndex(null)
      setIsUploading(false)

      // Mark conversation complete if no next probe
      if (!result.next_follow_up) {
        setConversationComplete(true)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to grade follow-up')
      setIsUploading(false)
    }
  }, [])

  return (
    <div>
      <div className="mb-6">
        <div className="text-sm text-gray-400 mb-2">&larr; Grade Result</div>
        <h1 className="text-xl font-semibold">Follow-up Probes</h1>
        <p className="text-sm text-gray-500 mt-1">
          Generated from your answer &bull; New probes appear as you answer
        </p>
      </div>

      {/* Probe queue */}
      <div className="card">
        <div className="section-title">Probe Queue &mdash; {followUps.length} follow-ups</div>

        {followUps.map((fu, i) => {
          const isGraded = fu.score != null
          const isActive = activeIndex === i
          const isChained = !!fu.parent_follow_up_id

          return (
            <div key={fu.id}>
              {isChained && (
                <div className="flex items-center gap-2 px-4 py-1">
                  <div className="h-4 w-px bg-blue-300 ml-3" />
                  <span className="text-[10px] text-blue-500 uppercase tracking-wide">Generated from your previous answer</span>
                </div>
              )}
              <div
                className={`flex items-start gap-3 px-4 py-3 border-l-4 transition-all ${
                  isGraded ? 'border-l-green-500 text-gray-500' :
                  isActive ? 'border-l-coral bg-coral/5' :
                  'border-transparent'
                }`}
              >
                <span className={`badge ${isGraded ? getScoreBadge(fu.score) : isActive ? 'badge-accent' : 'badge-default'} flex-shrink-0 mt-0.5`}>
                  {isGraded ? fu.score?.toFixed(1) : isActive ? 'REC' : i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm">&ldquo;{fu.question_text}&rdquo;</div>
                  {isGraded && fu.feedback && (
                    <div className="text-xs text-gray-400 mt-1">{fu.feedback}</div>
                  )}
                  {isGraded && fu.ideal_answer && (
                    <div className="mt-2">
                      <button
                        onClick={() => setExpandedIdeal(prev => {
                          const next = new Set(prev)
                          if (next.has(i)) next.delete(i)
                          else next.add(i)
                          return next
                        })}
                        className="text-[10px] text-blue-600 hover:text-blue-800 uppercase tracking-wide"
                      >
                        {expandedIdeal.has(i) ? 'Hide' : 'Show'} Ideal Answer {expandedIdeal.has(i) ? '\u25B2' : '\u25BC'}
                      </button>
                      {expandedIdeal.has(i) && (
                        <div className="bg-blue-50 border-l-[3px] border-blue-400 p-3 text-xs leading-relaxed text-blue-900 mt-1">
                          {fu.ideal_answer}
                        </div>
                      )}
                    </div>
                  )}
                  {!isGraded && !isActive && (
                    <button
                      onClick={() => setActiveIndex(i)}
                      className="text-xs text-coral hover:text-coral/80 mt-1 uppercase tracking-wide"
                    >
                      Record answer
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}

        {/* Conversation complete message */}
        {conversationComplete && allAnswered && (
          <div className="px-4 py-3 bg-green-50 border-l-4 border-green-500 text-sm text-green-800">
            Conversation complete &mdash; all gaps have been probed.
          </div>
        )}
      </div>

      {/* Inline recorder for active probe */}
      {activeIndex !== null && (
        <div className="card mt-4">
          <div className="text-center py-4">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-3">
              Follow-up #{activeIndex + 1} of {followUps.length}
            </div>
            <div className="text-sm font-medium px-6 mb-4">
              &ldquo;{followUps[activeIndex].question_text}&rdquo;
            </div>

            <AudioRecorder
              suggestedDuration={suggestedMinutes}
              onSubmit={(blob) => handleSubmit(blob, followUps[activeIndex].id, activeIndex)}
              isUploading={isUploading}
            />

            {error && (
              <div className="card-sm bg-red-50 text-red-700 text-sm mt-3">{error}</div>
            )}
          </div>
        </div>
      )}

      {/* Session summary */}
      <div className="card-sm bg-gray-50 mt-4">
        <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-2">Session Summary</div>
        <div className="flex gap-6">
          <div>
            <div className="text-xs text-gray-400">Completed</div>
            <div className="text-lg font-semibold">{completedCount} / {followUps.length}</div>
          </div>
          {avgScore !== null && (
            <div>
              <div className="text-xs text-gray-400">Avg Score</div>
              <div className="text-lg font-semibold">{avgScore.toFixed(1)}</div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4">
        <button onClick={onDone} className="btn-primary px-6 py-2 text-sm">
          Back to Questions
        </button>
      </div>
    </div>
  )
}
