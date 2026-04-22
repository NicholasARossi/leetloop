'use client'

import { useState } from 'react'
import type { LanguageOralSession, LanguageOralDimensionScore } from '@/lib/api'

interface OralGradingCardProps {
  session: LanguageOralSession
}

const DIMENSION_LABELS: Record<string, string> = {
  grammar: 'Grammaire',
  lexical: 'Lexique',
  discourse: 'Discours',
  task: 'Tache',
}

const DIMENSION_COLORS: Record<string, string> = {
  grammar: 'bg-blue-500',
  lexical: 'bg-amber-500',
  discourse: 'bg-purple-500',
  task: 'bg-green-500',
}

function getVerdictStyle(verdict: string) {
  switch (verdict) {
    case 'strong':
      return 'bg-green-100 text-green-800 border-green-300'
    case 'developing':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    case 'needs_work':
      return 'bg-red-100 text-red-800 border-red-300'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300'
  }
}

function getVerdictLabel(verdict: string) {
  switch (verdict) {
    case 'strong': return 'Fort'
    case 'developing': return 'En progres'
    case 'needs_work': return 'A travailler'
    default: return verdict
  }
}

function getScoreColor(score: number) {
  if (score >= 7) return 'text-green-700'
  if (score >= 5) return 'text-yellow-700'
  return 'text-red-700'
}

function DimensionBar({ name, dim }: { name: string; dim: LanguageOralDimensionScore }) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.min(dim.score * 10, 100)
  const barColor = DIMENSION_COLORS[name] || 'bg-gray-500'

  return (
    <div className="mb-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left"
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-mono uppercase text-gray-600">
            {DIMENSION_LABELS[name] || name}
          </span>
          <span className={`text-sm font-mono font-bold ${getScoreColor(dim.score)}`}>
            {dim.score.toFixed(1)}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </button>

      {expanded && (
        <div className="mt-2 pl-2 border-l-2 border-gray-200 space-y-2">
          {dim.summary && (
            <p className="text-xs text-gray-600">{dim.summary}</p>
          )}
          {dim.evidence.map((ev, i) => (
            <div key={i} className="text-xs">
              <p className="italic text-gray-500">&ldquo;{ev.quote}&rdquo;</p>
              <p className="text-gray-600 mt-0.5">{ev.analysis}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function OralGradingCard({ session }: OralGradingCardProps) {
  const [showTranscript, setShowTranscript] = useState(false)
  const grading = session.grading

  if (!grading) {
    if (session.status === 'grading') {
      return (
        <div className="card-sm">
          <div className="flex items-center gap-2 text-sm text-gray-500 font-mono">
            <div className="w-4 h-4 border-2 border-coral border-t-transparent rounded-full animate-spin" />
            En cours d&apos;evaluation...
          </div>
          {session.prompt && (
            <p className="text-xs text-gray-400 mt-2 line-clamp-2">{session.prompt.prompt_text}</p>
          )}
        </div>
      )
    }
    if (session.status === 'failed') {
      return (
        <div className="card-sm bg-red-50 border-red-200">
          <p className="text-sm text-red-700">Echec de la transcription. Veuillez reessayer.</p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="card-sm">
      {/* Header: score + verdict */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className={`stat-value text-2xl ${getScoreColor(grading.overall_score)}`}>
            {grading.overall_score.toFixed(1)}
          </span>
          <span className={`inline-block px-2 py-0.5 text-xs font-mono border rounded ${getVerdictStyle(grading.verdict)}`}>
            {getVerdictLabel(grading.verdict)}
          </span>
        </div>
        {session.prompt?.theme && (
          <span className="text-xs font-mono text-gray-400">
            {session.prompt.theme}
          </span>
        )}
      </div>

      {/* Dimension bars */}
      {['grammar', 'lexical', 'discourse', 'task'].map(dim => {
        const score = grading.scores[dim]
        if (!score) return null
        return <DimensionBar key={dim} name={dim} dim={score} />
      })}

      {/* Strongest / Weakest moments */}
      {(grading.strongest_moment || grading.weakest_moment) && (
        <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-gray-200">
          {grading.strongest_moment && (
            <div>
              <span className="text-xs font-mono text-green-600 uppercase">Point fort</span>
              <p className="text-xs text-gray-600 mt-0.5">{grading.strongest_moment}</p>
            </div>
          )}
          {grading.weakest_moment && (
            <div>
              <span className="text-xs font-mono text-red-600 uppercase">A ameliorer</span>
              <p className="text-xs text-gray-600 mt-0.5">{grading.weakest_moment}</p>
            </div>
          )}
        </div>
      )}

      {/* Feedback */}
      {grading.feedback && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-sm text-gray-700 leading-relaxed">{grading.feedback}</p>
        </div>
      )}

      {/* Transcript toggle */}
      {grading.transcript && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="text-xs font-mono text-gray-400 hover:text-gray-600"
          >
            {showTranscript ? 'Masquer la transcription' : 'Voir la transcription'}
          </button>
          {showTranscript && (
            <p className="text-xs text-gray-500 mt-2 leading-relaxed whitespace-pre-wrap">
              {grading.transcript}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
