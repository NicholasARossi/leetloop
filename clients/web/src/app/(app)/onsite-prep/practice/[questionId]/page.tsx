'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  leetloopApi,
  type OnsitePrepQuestion,
  type OnsitePrepGradeResult,
  type OnsitePrepFollowUp,
  type OnsitePrepAttempt,
  type OnsitePrepAttemptHistory,
  type IdealResponse,
  type SubmitAudioResponse,
} from '@/lib/api'
import { RecordingView, GradeResult, FollowUpProbes, ModeSelector, BreakdownView, BreakdownSummary } from '@/components/onsite-prep'

type FlowState = 'loading' | 'attempts' | 'record' | 'grading' | 'follow-ups' | 'breakdown' | 'breakdown-summary'

const CATEGORY_ROUTES: Record<string, string> = {
  lp: '/onsite-prep/lp',
  breadth: '/onsite-prep/breadth',
  depth: '/onsite-prep/depth',
  design: '/onsite-prep/design',
}

const CATEGORY_LABELS: Record<string, string> = {
  lp: 'LP Stories',
  breadth: 'ML Breadth',
  depth: 'ML Depth',
  design: 'System Design',
}

function getVerdictBadge(verdict: string | undefined): string {
  switch (verdict) {
    case 'pass': return 'badge-pass'
    case 'borderline': return 'badge-warn'
    case 'fail': return 'badge-fail'
    default: return 'badge-default'
  }
}

function getVerdictLabel(verdict: string | undefined): string {
  switch (verdict) {
    case 'pass': return 'Strong'
    case 'borderline': return 'Needs Polish'
    case 'fail': return 'Needs Work'
    default: return '\u2014'
  }
}

function getModeBadge(mode: string): string {
  return mode === 'breakdown' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'
}

function getModeLabel(mode: string): string {
  return mode === 'breakdown' ? 'Breakdown' : 'S&D'
}

export default function PracticePage() {
  const params = useParams()
  const router = useRouter()
  const questionId = params.questionId as string

  const [state, setState] = useState<FlowState>('loading')
  const [question, setQuestion] = useState<OnsitePrepQuestion | null>(null)
  const [attempts, setAttempts] = useState<OnsitePrepAttemptHistory[]>([])
  const [gradeResult, setGradeResult] = useState<OnsitePrepGradeResult | null>(null)
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [followUps, setFollowUps] = useState<OnsitePrepFollowUp[]>([])
  const [followUpsReady, setFollowUpsReady] = useState(false)
  const [idealResponse, setIdealResponse] = useState<IdealResponse | null>(null)
  const [idealLoading, setIdealLoading] = useState(false)
  const [attemptLoading, setAttemptLoading] = useState(false)
  const [mode, setMode] = useState<'stand_and_deliver' | 'breakdown'>('stand_and_deliver')
  const [viewingAttempt, setViewingAttempt] = useState<OnsitePrepAttempt | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [q, history] = await Promise.all([
          leetloopApi.getOnsitePrepQuestion(questionId),
          leetloopApi.getOnsitePrepHistory('00000000-0000-0000-0000-000000000001', 100),
        ])
        setQuestion(q)
        setAttempts(history.filter(a => a.question_id === questionId))
        setState('attempts')
      } catch (e) {
        console.error('Failed to load question:', e)
      }
    }
    load()
  }, [questionId])

  const handleViewAttempt = async (id: string) => {
    setAttemptLoading(true)
    try {
      const attempt = await leetloopApi.getOnsitePrepAttempt(id)
      setViewingAttempt(attempt)

      // If this is a breakdown attempt, show breakdown summary
      if (attempt.mode === 'breakdown') {
        setAttemptId(id)
        setState('breakdown-summary')
        return
      }

      // Stand & Deliver attempt
      setAttemptId(id)

      // Build grade result from attempt data
      setGradeResult({
        transcript: attempt.transcript || '',
        dimensions: attempt.dimensions || [],
        overall_score: attempt.overall_score || 0,
        verdict: attempt.verdict || 'fail',
        feedback: attempt.feedback || '',
        strongest_moment: attempt.strongest_moment || '',
        weakest_moment: attempt.weakest_moment || '',
        follow_up_questions: attempt.follow_up_questions || [],
      })

      setIdealResponse(attempt.ideal_response || question?.ideal_answer || null)
      setFollowUps(attempt.follow_ups || [])

      if (attempt.follow_ups.length > 0) {
        setFollowUpsReady(true)
      } else {
        // No follow-ups yet — generate them on demand
        setFollowUpsReady(false)
        leetloopApi.generateOnsitePrepFollowUps(id)
          .then(fus => {
            setFollowUps(fus)
            setFollowUpsReady(true)
          })
          .catch(e => {
            console.error('Failed to generate follow-ups:', e)
            // Still mark ready so button is clickable (will show 0 follow-ups)
            setFollowUpsReady(true)
          })
      }
      setState('grading')
    } catch (e) {
      console.error('Failed to load attempt:', e)
    } finally {
      setAttemptLoading(false)
    }
  }

  const handleGraded = (response: SubmitAudioResponse) => {
    setGradeResult(response.grade)
    setAttemptId(response.attempt_id)
    setState('grading')

    // If question has a pre-stored ideal answer (LP stories), use it directly
    if (question?.ideal_answer) {
      setIdealResponse(question.ideal_answer)
      setIdealLoading(false)
    } else {
      // Fire Gemini generation for non-LP categories
      setIdealLoading(true)
      leetloopApi.generateOnsitePrepIdealResponse(response.attempt_id)
        .then(ideal => setIdealResponse(ideal))
        .catch(e => console.error('Failed to generate ideal response:', e))
        .finally(() => setIdealLoading(false))
    }

    // Fire follow-ups generation
    setFollowUpsReady(false)
    leetloopApi.generateOnsitePrepFollowUps(response.attempt_id)
      .then(fus => {
        setFollowUps(fus)
        setFollowUpsReady(true)
      })
      .catch(e => console.error('Failed to generate follow-ups:', e))
  }

  const handleBackToAttempts = () => {
    setGradeResult(null)
    setAttemptId(null)
    setIdealResponse(null)
    setFollowUps([])
    setFollowUpsReady(false)
    setViewingAttempt(null)
    // Refresh attempts list
    leetloopApi.getOnsitePrepHistory('00000000-0000-0000-0000-000000000001', 100)
      .then(history => setAttempts(history.filter(a => a.question_id === questionId)))
    setState('attempts')
  }

  const handleFollowUps = () => {
    if (!followUpsReady || followUps.length === 0) {
      // Generate follow-ups if we're viewing a past attempt that doesn't have them yet
      if (attemptId) {
        setFollowUpsReady(false)
        leetloopApi.generateOnsitePrepFollowUps(attemptId)
          .then(fus => {
            setFollowUps(fus)
            setFollowUpsReady(true)
            setState('follow-ups')
          })
          .catch(e => console.error('Failed to generate follow-ups:', e))
      }
      return
    }
    setState('follow-ups')
  }

  const handleDone = () => {
    handleBackToAttempts()
  }

  const handleRecordNew = () => {
    if (question?.category === 'design' && mode === 'breakdown') {
      setState('breakdown')
    } else {
      setState('record')
    }
  }

  if (state === 'loading' || !question) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-coral border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const backLink = CATEGORY_ROUTES[question.category] || '/onsite-prep'

  return (
    <div>
      <div className="mb-4">
        <div className="flex items-center gap-2">
          <Link href={backLink} className="text-sm text-gray-400 hover:text-gray-600">
            &larr; {CATEGORY_LABELS[question.category] || question.category}
          </Link>
          {question.subcategory && (
            <span className="badge badge-accent">{question.subcategory}</span>
          )}
        </div>
      </div>

      {/* Attempts list — landing view */}
      {state === 'attempts' && (
        <div>
          <div className="card mb-4">
            <div className="text-xs text-gray-600 italic mb-4">
              &ldquo;{question.prompt_text}&rdquo;
            </div>
            {question.category !== 'design' && question.context_hint && (
              <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 text-xs text-gray-500">
                {question.category === 'lp' ? 'Mapped Story: ' : 'Context: '}
                {question.context_hint}
              </div>
            )}
            {question.category === 'design' && (
              <div className="bg-gray-50 border-l-[3px] border-gray-300 p-3 text-xs text-gray-500">
                Cold interview mode: answer from first principles first. Coaching structure and adaptive follow-ups unlock after grading.
              </div>
            )}
          </div>

          {/* Mode selector for design questions */}
          {question.category === 'design' && question.breakdown_phases.length > 0 && (
            <ModeSelector mode={mode} onModeChange={setMode} />
          )}

          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] uppercase tracking-widest text-gray-500">
              {attempts.length} Attempt{attempts.length !== 1 ? 's' : ''}
            </div>
            <button
              onClick={handleRecordNew}
              className="btn-primary px-4 py-2 text-sm"
            >
              {mode === 'breakdown' && question.category === 'design' ? 'Start Breakdown' : 'Record New Attempt'}
            </button>
          </div>

          {attempts.length === 0 ? (
            <div className="card text-center py-8">
              <p className="text-sm text-gray-500 mb-1">No attempts yet</p>
              <p className="text-xs text-gray-400">Record your first answer to get graded</p>
            </div>
          ) : (
            <div className="card">
              {attempts.map((a) => (
                <button
                  key={a.id}
                  onClick={() => handleViewAttempt(a.id)}
                  disabled={attemptLoading}
                  className="w-full flex items-center gap-4 px-4 py-3 border-l-4 border-transparent hover:border-coral hover:bg-gray-50 transition-all text-left"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium">
                        {a.created_at ? new Date(a.created_at).toLocaleDateString('en-US', {
                          month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                        }) : 'Unknown date'}
                      </div>
                      {a.mode && (
                        <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${getModeBadge(a.mode)}`}>
                          {getModeLabel(a.mode)}
                        </span>
                      )}
                    </div>
                    {a.overall_score != null && (
                      <div className="text-xs text-gray-400 mt-0.5">
                        Score: {a.overall_score.toFixed(1)} / 5
                        {a.mode === 'breakdown' && a.phases_completed > 0 && (
                          <span className="ml-2">({a.phases_completed}/7 phases)</span>
                        )}
                      </div>
                    )}
                  </div>
                  <span className={`badge ${getVerdictBadge(a.verdict ?? undefined)}`}>
                    {getVerdictLabel(a.verdict ?? undefined)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {state === 'record' && (
        <div>
          <button
            onClick={handleBackToAttempts}
            className="text-sm text-gray-400 hover:text-gray-600 mb-4"
          >
            &larr; Back to attempts
          </button>
          <RecordingView question={question} onGraded={handleGraded} />
        </div>
      )}

      {state === 'breakdown' && (
        <div>
          <button
            onClick={handleBackToAttempts}
            className="text-sm text-gray-400 hover:text-gray-600 mb-4"
          >
            &larr; Back to attempts
          </button>
          <BreakdownView question={question} onDone={handleBackToAttempts} />
        </div>
      )}

      {state === 'grading' && gradeResult && (
        <div>
          <button
            onClick={handleBackToAttempts}
            className="text-sm text-gray-400 hover:text-gray-600 mb-4"
          >
            &larr; Back to attempts
          </button>
          <GradeResult
            result={gradeResult}
            question={question}
            onReRecord={() => setState('record')}
            onFollowUps={handleFollowUps}
            idealResponse={idealResponse}
            idealLoading={idealLoading}
            followUpsReady={followUpsReady}
          />
        </div>
      )}

      {state === 'breakdown-summary' && viewingAttempt && viewingAttempt.mode === 'breakdown' && (
        <div>
          <button
            onClick={handleBackToAttempts}
            className="text-sm text-gray-400 hover:text-gray-600 mb-4"
          >
            &larr; Back to attempts
          </button>
          <BreakdownSummary
            phases={question.breakdown_phases}
            submissions={viewingAttempt.phase_submissions}
            overallScore={viewingAttempt.overall_score ?? 0}
            overallVerdict={viewingAttempt.verdict ?? 'fail'}
            onBack={handleBackToAttempts}
          />
        </div>
      )}

      {state === 'follow-ups' && attemptId && (
        <FollowUpProbes
          attemptId={attemptId}
          followUps={followUps}
          category={question.category}
          onDone={handleDone}
        />
      )}
    </div>
  )
}
