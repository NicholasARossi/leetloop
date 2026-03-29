'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { leetloopApi, type OnsitePrepDashboard, type OnsitePrepAttemptHistory } from '@/lib/api'

const DEFAULT_USER = '00000000-0000-0000-0000-000000000001'

const CATEGORY_BADGES: Record<string, string> = {
  lp: 'Behavioral',
  breadth: 'General ML',
  depth: 'Your Projects',
  design: 'Application',
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  lp: 'STAR stories for leadership principles',
  breadth: 'NLP, search, reco, production systems',
  depth: 'Your tech stack: RL, LLM-as-judge, two-tower, cross-encoder, FAISS',
  design: 'Alexa trust & safety \u2022 PV search & reco',
}

function getVerdictBadge(verdict?: string): string {
  switch (verdict) {
    case 'pass': return 'badge-pass'
    case 'borderline': return 'badge-warn'
    case 'fail': return 'badge-fail'
    default: return 'badge-default'
  }
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatTimeAgo(dateStr?: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffHours < 1) return 'just now'
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

export default function OnsitePrepDashboardPage() {
  const [dashboard, setDashboard] = useState<OnsitePrepDashboard | null>(null)
  const [history, setHistory] = useState<OnsitePrepAttemptHistory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [dash, hist] = await Promise.all([
          leetloopApi.getOnsitePrepDashboard(DEFAULT_USER),
          leetloopApi.getOnsitePrepHistory(DEFAULT_USER, 5),
        ])
        setDashboard(dash)
        setHistory(hist)
      } catch (e) {
        console.error('Failed to load dashboard:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-coral border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const daysUntil = Math.max(0, Math.ceil((new Date('2026-04-08').getTime() - Date.now()) / (1000 * 60 * 60 * 24)))

  return (
    <div>
      <div className="mb-6">
        <div className="text-sm text-gray-400">
          {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          {' '}&mdash; {daysUntil} days until onsite
        </div>
        <h1 className="text-xl font-semibold">Amazon Onsite Prep</h1>
      </div>

      {/* Loop info */}
      <div className="card-sm bg-coral/10 mb-5">
        <div className="text-xs text-gray-700 leading-relaxed">
          <strong>5-slot split loop:</strong> 2 Alexa ASCI &bull; 2 Prime Video Search &bull; 1 Bar Raiser (external org)
        </div>
      </div>

      {/* Summary stats */}
      {dashboard && (
        <div className="card mb-6">
          <div className="flex justify-around">
            <div className="text-center">
              <div className="text-3xl font-semibold">{dashboard.practiced_count}</div>
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Practiced</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-semibold text-coral">{dashboard.total_questions - dashboard.practiced_count}</div>
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Remaining</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-semibold">{dashboard.avg_score?.toFixed(1) || '--'}</div>
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Avg Score</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-semibold">{formatDuration(dashboard.avg_duration ?? undefined)}</div>
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Avg Time</div>
            </div>
          </div>
          {dashboard.total_questions > 0 && (
            <div className="h-1.5 bg-gray-200 mt-4" style={{ clipPath: 'polygon(3px 0, 100% 0, calc(100% - 3px) 100%, 0 100%)' }}>
              <div
                className="h-full bg-coral transition-all"
                style={{ width: `${(dashboard.practiced_count / dashboard.total_questions) * 100}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Category cards */}
      <div className="section-title">Pick a Category</div>
      <div className="grid grid-cols-2 gap-3 mb-6">
        {dashboard?.categories.map((cat) => (
          <Link
            key={cat.category}
            href={cat.category === 'design' ? '/onsite-prep/design' : `/onsite-prep/${cat.category}`}
            className="card-sm hover:shadow-lg transition-all"
          >
            <div className={`badge ${cat.category === 'lp' ? 'badge-accent' : 'badge-default'} mb-3`}>
              {CATEGORY_BADGES[cat.category]}
            </div>
            <div className="text-2xl font-semibold -tracking-wide">{cat.total}</div>
            <div className="text-xs uppercase tracking-widest text-gray-500 mt-0.5">{cat.label}</div>
            <div className="text-xs text-gray-400 mt-2">{CATEGORY_DESCRIPTIONS[cat.category]}</div>
            <div className="text-xs text-gray-400 mt-1">
              {cat.practiced} of {cat.total} practiced
            </div>
            {cat.total > 0 && (
              <div className="h-1.5 bg-gray-200 mt-2" style={{ clipPath: 'polygon(3px 0, 100% 0, calc(100% - 3px) 100%, 0 100%)' }}>
                <div
                  className="h-full bg-coral transition-all"
                  style={{ width: `${(cat.practiced / cat.total) * 100}%` }}
                />
              </div>
            )}
          </Link>
        ))}
      </div>

      {/* Recent practice */}
      {history.length > 0 && (
        <>
          <div className="section-title">Recent Practice</div>
          <div className="card-sm">
            {history.map((h) => (
              <div key={h.id} className="flex items-center gap-3 px-4 py-3 border-l-4 border-gray-200 text-gray-500">
                <span className={`badge ${getVerdictBadge(h.verdict)} flex-shrink-0`}>
                  {h.overall_score?.toFixed(1) || '--'}
                </span>
                <span className="text-sm flex-1 truncate">{h.prompt_text}</span>
                <span className="text-[10px] uppercase tracking-wide text-gray-400">
                  {h.category} &bull; {formatDuration(h.duration_seconds ?? undefined)} &bull; {formatTimeAgo(h.created_at ?? undefined)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
