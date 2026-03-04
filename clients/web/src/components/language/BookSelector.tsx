'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import type { LanguageTrackSummary } from '@/lib/api'

/**
 * Book selector dropdown for the language sidebar.
 * Parent calls setActiveLanguageTrack via onSelectTrack callback.
 */
interface BookSelectorProps {
  tracks: LanguageTrackSummary[]
  activeTrackId: string | null
  onSelectTrack: (trackId: string) => void
  switchingTrack: string | null
}

export function BookSelector({ tracks, activeTrackId, onSelectTrack, switchingTrack }: BookSelectorProps) {
  const [open, setOpen] = useState(false)

  const activeTrack = tracks.find(t => t.id === activeTrackId)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors flex items-center gap-3"
      >
        {/* Book icon placeholder */}
        <div
          className="w-8 h-10 flex-shrink-0 flex items-center justify-center text-[10px] font-bold text-white"
          style={{
            background: 'linear-gradient(135deg, var(--accent-color), var(--accent-color-dark))',
            clipPath: 'polygon(var(--chamfer-sm) 0, 100% 0, 100% calc(100% - var(--chamfer-sm)), calc(100% - var(--chamfer-sm)) 100%, 0 100%, 0 var(--chamfer-sm))',
          }}
        >
          {activeTrack ? activeTrack.name.split(' ').map(w => w[0]).slice(0, 2).join('') : '?'}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium truncate">
            {activeTrack?.name || 'Aucun livre sélectionné'}
          </p>
          {activeTrack && (
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] text-gray-500 uppercase">{activeTrack.language}</span>
              <span className="text-[10px] text-gray-400">&middot;</span>
              <span className="text-[10px] text-gray-500 uppercase">{activeTrack.level}</span>
            </div>
          )}
        </div>
        <svg
          className={clsx('w-3.5 h-3.5 text-gray-400 transition-transform flex-shrink-0', open && 'rotate-180')}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full bg-white border-t border-gray-200 shadow-lg z-20">
          {tracks.map((track) => {
            const isActive = track.id === activeTrackId
            return (
              <button
                key={track.id}
                onClick={() => {
                  if (!isActive && !switchingTrack) {
                    onSelectTrack(track.id)
                    setOpen(false)
                  }
                }}
                disabled={isActive || switchingTrack !== null}
                className={clsx(
                  'w-full text-left px-4 py-2.5 border-b border-gray-100 last:border-0 transition-colors flex items-center gap-3',
                  isActive
                    ? 'bg-gray-50'
                    : switchingTrack
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:bg-gray-50 cursor-pointer'
                )}
              >
                <div
                  className="w-6 h-8 flex-shrink-0 flex items-center justify-center text-[8px] font-bold text-white"
                  style={{
                    background: isActive
                      ? 'linear-gradient(135deg, var(--accent-color), var(--accent-color-dark))'
                      : 'linear-gradient(135deg, #999, #666)',
                    clipPath: 'polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px)',
                  }}
                >
                  {track.name.split(' ').map(w => w[0]).slice(0, 2).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{track.name}</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="text-[9px] text-gray-500 uppercase">{track.language}</span>
                    <span className="text-[9px] text-gray-400">&middot;</span>
                    <span className="text-[9px] text-gray-500 uppercase">{track.level}</span>
                    <span className="text-[9px] text-gray-400">&middot;</span>
                    <span className="text-[9px] text-gray-500">{track.total_topics} chapitres</span>
                  </div>
                </div>
                {isActive && (
                  <span className="text-[9px] font-semibold uppercase" style={{ color: 'var(--accent-color-dark)' }}>Actif</span>
                )}
                {switchingTrack === track.id && (
                  <span className="text-[9px] text-gray-400">Changement...</span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
