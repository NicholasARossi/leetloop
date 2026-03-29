'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { leetloopApi, type OnsitePrepQuestion, type OnsitePrepGradeResult, type OnsitePrepFollowUp } from '@/lib/api'
import { RecordingView, GradeResult, FollowUpProbes } from '@/components/onsite-prep'

type FlowState = 'loading' | 'record' | 'grading' | 'follow-ups'

const CATEGORY_ROUTES: Record<string, string> = {
  lp: '/onsite-prep/lp',
  breadth: '/onsite-prep/breadth',
  depth: '/onsite-prep/depth',
  design: '/onsite-prep/design',
}

export default function PracticePage() {
  const params = useParams()
  const router = useRouter()
  const questionId = params.questionId as string

  const [state, setState] = useState<FlowState>('loading')
  const [question, setQuestion] = useState<OnsitePrepQuestion | null>(null)
  const [gradeResult, setGradeResult] = useState<OnsitePrepGradeResult | null>(null)
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [followUps, setFollowUps] = useState<OnsitePrepFollowUp[]>([])
  const [generatingFollowUps, setGeneratingFollowUps] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const q = await leetloopApi.getOnsitePrepQuestion(questionId)
        setQuestion(q)
        setState('record')
      } catch (e) {
        console.error('Failed to load question:', e)
      }
    }
    load()
  }, [questionId])

  const handleGraded = (result: OnsitePrepGradeResult) => {
    setGradeResult(result)
    setState('grading')
  }

  const handleReRecord = () => {
    setGradeResult(null)
    setAttemptId(null)
    setState('record')
  }

  const handleFollowUps = async () => {
    if (!gradeResult) return

    setGeneratingFollowUps(true)
    try {
      // First we need to find the attempt ID — get the most recent attempt for this question
      // The attempt was created in submit-audio, so we need the history
      const history = await leetloopApi.getOnsitePrepHistory('00000000-0000-0000-0000-000000000001', 1)
      if (history.length === 0) return

      const latestAttemptId = history[0].id
      setAttemptId(latestAttemptId)

      // Generate follow-ups
      const fus = await leetloopApi.generateOnsitePrepFollowUps(latestAttemptId)
      setFollowUps(fus)
      setState('follow-ups')
    } catch (e) {
      console.error('Failed to generate follow-ups:', e)
    } finally {
      setGeneratingFollowUps(false)
    }
  }

  const handleDone = () => {
    if (question) {
      router.push(CATEGORY_ROUTES[question.category] || '/onsite-prep')
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
            &larr; {question.category === 'lp' ? 'LP Stories' : question.category === 'breadth' ? 'ML Breadth' : question.category === 'depth' ? 'ML Depth' : 'System Design'}
          </Link>
          {question.subcategory && (
            <span className="badge badge-accent">{question.subcategory}</span>
          )}
        </div>
      </div>

      {state === 'record' && (
        <RecordingView question={question} onGraded={handleGraded} />
      )}

      {state === 'grading' && gradeResult && (
        <>
          <GradeResult
            result={gradeResult}
            question={question}
            onReRecord={handleReRecord}
            onFollowUps={handleFollowUps}
          />
          {generatingFollowUps && (
            <div className="flex items-center gap-2 mt-4 text-sm text-gray-500">
              <div className="w-4 h-4 border-2 border-coral border-t-transparent rounded-full animate-spin" />
              Generating follow-up probes...
            </div>
          )}
        </>
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
