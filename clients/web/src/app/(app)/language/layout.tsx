'use client'

import { LanguageTrackProvider, useLanguageTrack } from '@/contexts/LanguageTrackContext'
import { BookSelector, BookLibrary } from '@/components/language'

function LanguageLayoutInner({ children }: { children: React.ReactNode }) {
  const { tracks, activeTrackId, switchingTrack, loading, selectTrack } = useLanguageTrack()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-pulse mb-3">
            <div className="w-12 h-12 mx-auto border-3 border-black rounded-full flex items-center justify-center">
              <span className="text-lg font-bold">AI</span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">Chargement...</p>
        </div>
      </div>
    )
  }

  if (tracks.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500 text-sm">Aucun livre disponible.</p>
        <p className="text-gray-400 text-xs mt-1">
          Importez un manuel de langue pour commencer.
        </p>
      </div>
    )
  }

  if (!activeTrackId) {
    return (
      <BookLibrary
        tracks={tracks}
        activeTrackId={activeTrackId}
        onSelectTrack={selectTrack}
        switchingTrack={switchingTrack}
      />
    )
  }

  return (
    <div>
      <div className="mb-6 border border-gray-200 relative z-30">
        <BookSelector
          tracks={tracks}
          activeTrackId={activeTrackId}
          onSelectTrack={selectTrack}
          switchingTrack={switchingTrack}
        />
      </div>
      {children}
    </div>
  )
}

export default function LanguageLayout({ children }: { children: React.ReactNode }) {
  return (
    <LanguageTrackProvider>
      <LanguageLayoutInner>{children}</LanguageLayoutInner>
    </LanguageTrackProvider>
  )
}
