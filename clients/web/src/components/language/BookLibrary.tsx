'use client'

import { clsx } from 'clsx'
import type { LanguageTrackSummary } from '@/lib/api'

interface BookLibraryProps {
  tracks: LanguageTrackSummary[]
  activeTrackId: string | null
  onSelectTrack: (trackId: string) => void
  switchingTrack: string | null
  trackProgress?: Record<string, { completed: number; total: number; percentage: number }>
}

const COVER_GRADIENTS = [
  'linear-gradient(135deg, #FF8888, #993333)',
  'linear-gradient(135deg, #8899aa, #445566)',
  'linear-gradient(135deg, #aa8877, #664433)',
  'linear-gradient(135deg, #889988, #445544)',
  'linear-gradient(135deg, #9988aa, #554466)',
]

export function BookLibrary({ tracks, activeTrackId, onSelectTrack, switchingTrack, trackProgress }: BookLibraryProps) {
  if (tracks.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500 text-sm">Aucun livre disponible.</p>
        <p className="text-gray-400 text-xs mt-1">
          Importez un manuel de langue pour créer une piste.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="section-title">Bibliothèque</h2>
        <p className="text-xs text-gray-500">
          {tracks.length} livre{tracks.length > 1 ? 's' : ''} disponible{tracks.length > 1 ? 's' : ''}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {tracks.map((track, i) => {
          const isActive = track.id === activeTrackId
          const progress = trackProgress?.[track.id]
          const initials = track.name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 3).join('')

          return (
            <div
              key={track.id}
              className={clsx(
                'card-sm transition-all',
                isActive && 'ring-2 ring-[var(--accent-color)]'
              )}
            >
              {/* Cover placeholder */}
              <div
                className="h-20 mb-3 flex items-center justify-center text-white font-bold text-lg"
                style={{
                  background: COVER_GRADIENTS[i % COVER_GRADIENTS.length],
                  clipPath: 'polygon(var(--chamfer-sm) 0, 100% 0, 100% calc(100% - var(--chamfer-sm)), calc(100% - var(--chamfer-sm)) 100%, 0 100%, 0 var(--chamfer-sm))',
                }}
              >
                {initials}
              </div>

              {/* Info */}
              <h3 className="text-sm font-medium leading-tight mb-1.5">{track.name}</h3>
              {track.description && (
                <p className="text-[11px] text-gray-500 mb-2 line-clamp-2">{track.description}</p>
              )}

              {/* Metadata badges */}
              <div className="flex flex-wrap gap-1 mb-3">
                <span className="tag text-[9px]">{track.language.toUpperCase()}</span>
                <span className="tag text-[9px]">{track.level.toUpperCase()}</span>
                <span className="tag text-[9px]">{track.total_topics} chapitres</span>
                {isActive && (
                  <span className="badge badge-accent text-[9px]">Actif</span>
                )}
              </div>

              {/* Progress bar (if started) */}
              {progress && progress.completed > 0 && (
                <div className="mb-3">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${progress.percentage}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-500 mt-1">
                    {progress.completed}/{progress.total} chapitres &middot; {progress.percentage.toFixed(0)}%
                  </p>
                </div>
              )}

              {/* Action button */}
              <button
                onClick={() => onSelectTrack(track.id)}
                disabled={switchingTrack !== null}
                className={clsx(
                  'btn-primary w-full text-center text-xs py-2',
                  switchingTrack === track.id && 'opacity-50'
                )}
              >
                <span className="relative z-10">
                  {switchingTrack === track.id
                    ? 'Changement...'
                    : isActive
                      ? 'Continuer'
                      : progress && progress.completed > 0
                        ? 'Continuer'
                        : 'Commencer'}
                </span>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
