'use client'

import { useState } from 'react'
import type { ChapterProgressItem } from '@/lib/api'

interface ChapterSectionProps {
  chapter: ChapterProgressItem
}

const difficultyBadgeClass: Record<string, string> = {
  easy: 'badge-easy',
  medium: 'badge-medium',
  hard: 'badge-hard',
}

export function ChapterSection({ chapter }: ChapterSectionProps) {
  const [expanded, setExpanded] = useState(false)

  const hasSections = chapter.book_sections.length > 0
  const hasSummary = !!chapter.book_summary
  const expandable = hasSections || hasSummary || chapter.key_concepts.length > 0

  return (
    <div className="card-sm">
      {/* Collapsed row */}
      <button
        onClick={() => expandable && setExpanded(!expanded)}
        className="w-full text-left flex items-center gap-3"
        disabled={!expandable}
      >
        {/* Chapter number */}
        <span className="font-mono text-xs text-gray-400 w-6 flex-shrink-0 text-right">
          {String(chapter.order).padStart(2, '0')}
        </span>

        {/* Chapter name */}
        <span className="flex-1 text-sm font-medium truncate">{chapter.name}</span>

        {/* Difficulty */}
        <span className={difficultyBadgeClass[chapter.difficulty] || 'badge-easy'}>
          {chapter.difficulty}
        </span>

        {/* Status */}
        {chapter.is_completed ? (
          <span className="badge badge-accent text-[10px]">Done</span>
        ) : chapter.is_current ? (
          <span className="badge badge-accent text-[10px]">Current</span>
        ) : (
          <span className="w-12" />
        )}

        {/* Review due */}
        {chapter.has_review_due && (
          <span className="badge badge-accent text-[10px]">Review</span>
        )}

        {/* Chevron */}
        {expandable && (
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 pt-3 border-t border-gray-200 space-y-3">
          {/* Book summary */}
          {hasSummary && (
            <div>
              <h4 className="section-id mb-1">Summary</h4>
              <p className="text-xs text-gray-600 leading-relaxed">{chapter.book_summary}</p>
            </div>
          )}

          {/* Sections */}
          {hasSections && (
            <div>
              <h4 className="section-id mb-2">Sections</h4>
              <div className="space-y-2">
                {chapter.book_sections.map((section, i) => (
                  <div key={i} className="pl-3 border-l-2 border-gray-200">
                    <p className="text-xs font-medium">{section.title}</p>
                    {section.summary && (
                      <p className="text-xs text-gray-500 mt-0.5">{section.summary}</p>
                    )}
                    {section.key_points.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {section.key_points.map((point, j) => (
                          <li key={j} className="text-xs text-gray-500 pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[7px] before:w-1.5 before:h-1.5 before:bg-gray-300 before:clip-path-[polygon(50%_0%,100%_50%,50%_100%,0%_50%)]">
                            {point}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key concepts */}
          {chapter.key_concepts.length > 0 && (
            <div>
              <h4 className="section-id mb-2">Key Concepts</h4>
              <div className="flex flex-wrap gap-1.5">
                {chapter.key_concepts.map((concept, i) => (
                  <span key={i} className="tag text-[10px]">{concept}</span>
                ))}
              </div>
            </div>
          )}

          {/* Review reason */}
          {chapter.has_review_due && chapter.review_reason && (
            <div className="bg-gray-50 p-2 border-l-2 border-[var(--accent-color)]">
              <p className="text-xs text-gray-600">
                <span className="font-medium">Review needed:</span> {chapter.review_reason}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
