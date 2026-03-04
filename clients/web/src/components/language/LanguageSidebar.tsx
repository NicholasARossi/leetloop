'use client'

import { clsx } from 'clsx'
import type { LanguageTrackSummary } from '@/lib/api'
import { BookSelector } from './BookSelector'

export type LanguageView = 'dashboard' | 'progress' | 'library'

interface LanguageSidebarProps {
  tracks: LanguageTrackSummary[]
  activeTrackId: string | null
  currentView: LanguageView
  onViewChange: (view: LanguageView) => void
  onSelectTrack: (trackId: string) => void
  switchingTrack: string | null
  stats?: {
    streakDays?: number
    averageScore?: number | null
    completionPercent?: number
  }
}

const NAV_ITEMS: { view: LanguageView; label: string; icon: string }[] = [
  { view: 'dashboard', label: 'Tableau de bord', icon: '◈' },
  { view: 'progress', label: 'Progression', icon: '▣' },
  { view: 'library', label: 'Bibliothèque', icon: '▤' },
]

export function LanguageSidebar({
  tracks,
  activeTrackId,
  currentView,
  onViewChange,
  onSelectTrack,
  switchingTrack,
  stats,
}: LanguageSidebarProps) {
  return (
    <div
      className="w-[260px] flex-shrink-0 bg-white flex flex-col h-full"
      style={{ borderRight: '2px solid #e0e0e0' }}
    >
      {/* Book selector */}
      <div style={{ borderBottom: '1px solid #e0e0e0' }}>
        <BookSelector
          tracks={tracks}
          activeTrackId={activeTrackId}
          onSelectTrack={onSelectTrack}
          switchingTrack={switchingTrack}
        />
      </div>

      {/* Navigation */}
      <nav className="py-2">
        {NAV_ITEMS.map((item) => {
          const isActive = currentView === item.view
          return (
            <button
              key={item.view}
              onClick={() => onViewChange(item.view)}
              className={clsx(
                'w-full text-left flex items-center gap-3 px-5 py-2.5 text-sm transition-all border-l-3',
                isActive
                  ? 'font-medium text-black bg-[var(--accent-color-20)]'
                  : 'text-gray-500 hover:text-black hover:bg-gray-50 border-l-transparent'
              )}
              style={isActive ? { borderLeftColor: 'var(--accent-color)' } : { borderLeftColor: 'transparent' }}
            >
              <span className={clsx('text-base', isActive ? 'text-[var(--accent-color)]' : 'text-gray-400')}>
                {item.icon}
              </span>
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom stats */}
      {stats && (
        <div style={{ borderTop: '1px solid #e0e0e0' }}>
          <div className="grid grid-cols-3" style={{ gap: '1px', background: '#e0e0e0' }}>
            <div className="bg-white py-2.5 px-2 text-center">
              <p className="stat-value text-lg leading-none">{stats.streakDays ?? 0}</p>
              <p className="text-[9px] uppercase tracking-wider text-gray-400 mt-0.5">Série</p>
            </div>
            <div className="bg-white py-2.5 px-2 text-center">
              <p className="stat-value text-lg leading-none">
                {stats.averageScore != null ? stats.averageScore.toFixed(1) : '—'}
              </p>
              <p className="text-[9px] uppercase tracking-wider text-gray-400 mt-0.5">Score moyen</p>
            </div>
            <div className="bg-white py-2.5 px-2 text-center">
              <p className="stat-value text-lg leading-none">
                {stats.completionPercent != null ? `${stats.completionPercent.toFixed(0)}%` : '—'}
              </p>
              <p className="text-[9px] uppercase tracking-wider text-gray-400 mt-0.5">Complété</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
