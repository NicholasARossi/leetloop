'use client'

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from 'react'
import { useAuth } from './AuthContext'
import {
  leetloopApi,
  type LanguageTrackSummary,
} from '@/lib/api'

interface LanguageTrackContextType {
  tracks: LanguageTrackSummary[]
  activeTrackId: string | null
  switchingTrack: string | null
  loading: boolean
  selectTrack: (trackId: string) => Promise<void>
  refreshTracks: () => Promise<void>
}

const LanguageTrackContext = createContext<LanguageTrackContextType | undefined>(undefined)

export function LanguageTrackProvider({ children }: { children: ReactNode }) {
  const { userId } = useAuth()

  const [tracks, setTracks] = useState<LanguageTrackSummary[]>([])
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null)
  const [switchingTrack, setSwitchingTrack] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    if (!userId) {
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const [tracksData, dashboard] = await Promise.all([
        leetloopApi.getLanguageTracks(),
        leetloopApi.getLanguageDashboard(userId),
      ])
      setTracks(tracksData)
      setActiveTrackId(dashboard.active_track?.id ?? null)
    } catch (err) {
      console.error('[LanguageTrack] Failed to load:', err)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const selectTrack = useCallback(async (trackId: string) => {
    if (!userId) return

    setSwitchingTrack(trackId)
    try {
      await leetloopApi.setActiveLanguageTrack(userId, trackId)
      setActiveTrackId(trackId)
    } catch (err) {
      console.error('[LanguageTrack] Failed to switch track:', err)
    } finally {
      setSwitchingTrack(null)
    }
  }, [userId])

  return (
    <LanguageTrackContext.Provider
      value={{
        tracks,
        activeTrackId,
        switchingTrack,
        loading,
        selectTrack,
        refreshTracks: loadData,
      }}
    >
      {children}
    </LanguageTrackContext.Provider>
  )
}

export function useLanguageTrack() {
  const context = useContext(LanguageTrackContext)
  if (context === undefined) {
    throw new Error('useLanguageTrack must be used within a LanguageTrackProvider')
  }
  return context
}
