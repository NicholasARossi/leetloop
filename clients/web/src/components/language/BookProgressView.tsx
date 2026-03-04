'use client'

import type { BookProgressResponse } from '@/lib/api'
import { ChapterSection } from './ChapterSection'

interface BookProgressViewProps {
  data: BookProgressResponse | null
  loading: boolean
}

export function BookProgressView({ data, loading }: BookProgressViewProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <p className="text-gray-500 text-sm">Chargement de la progression...</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="card text-center">
        <p className="text-gray-500 text-sm">Aucune donnée de progression disponible.</p>
      </div>
    )
  }

  const progressPercent = data.completion_percentage

  return (
    <div>
      {/* Stats row - panel-schematic style */}
      <div className="panel-schematic mb-6">
        <div className="grid grid-cols-4" style={{ gap: '1px', background: '#e0e0e0' }}>
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">
              {data.completed_chapters}/{data.total_chapters}
            </p>
            <p className="stat-label mt-1">Chapitres</p>
          </div>
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">
              {data.completion_percentage.toFixed(0)}%
            </p>
            <p className="stat-label mt-1">Complété</p>
          </div>
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">
              {data.average_score > 0 ? data.average_score.toFixed(1) : '—'}
            </p>
            <p className="stat-label mt-1">Score moyen</p>
          </div>
          <div className="bg-white py-3 px-2 text-center">
            <p className="stat-value text-2xl leading-none">
              {data.chapters.filter(c => c.is_completed).length}
            </p>
            <p className="stat-label mt-1">Terminés</p>
          </div>
        </div>
      </div>

      {/* Source book */}
      {data.source_book && (
        <p className="text-xs text-gray-400 mb-4 truncate">
          Source : {data.source_book}
        </p>
      )}

      {/* Overall progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="section-title mb-0 pb-0 border-b-0">Progression</h2>
          <span className="font-mono text-sm text-gray-600">
            <span className="text-lg font-bold text-black">{data.completed_chapters}</span>
            /{data.total_chapters}
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Chapter list */}
      <div>
        <h3 className="section-id mb-3">Chapitres</h3>
        <div className="space-y-2">
          {data.chapters.map((chapter) => (
            <ChapterSection key={chapter.order} chapter={chapter} />
          ))}
        </div>
      </div>
    </div>
  )
}
