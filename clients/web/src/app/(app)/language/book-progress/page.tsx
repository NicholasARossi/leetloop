'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguageTrack } from '@/contexts/LanguageTrackContext'
import { leetloopApi, type BookProgressResponse } from '@/lib/api'
import { BookProgressView } from '@/components/language'

export default function BookProgressPage() {
  const { userId } = useAuth()
  const { activeTrackId } = useLanguageTrack()

  const [data, setData] = useState<BookProgressResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const loadProgress = useCallback(async () => {
    if (!userId || !activeTrackId) return

    setLoading(true)
    try {
      const result = await leetloopApi.getBookProgress(activeTrackId, userId)
      setData(result)
    } catch (err) {
      console.error('[BookProgress] Failed to load:', err)
    } finally {
      setLoading(false)
    }
  }, [userId, activeTrackId])

  useEffect(() => {
    loadProgress()
  }, [loadProgress])

  return <BookProgressView data={data} loading={loading} />
}
