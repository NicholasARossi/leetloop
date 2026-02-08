'use client'

import { useState, useEffect } from 'react'

interface AccentColors {
  accent: string
  accentDark: string
}

export function useAccentColors(): AccentColors {
  const [colors, setColors] = useState<AccentColors>({
    accent: '#FF8888',
    accentDark: '#993333',
  })

  useEffect(() => {
    const style = getComputedStyle(document.documentElement)
    const accent = style.getPropertyValue('--accent-color').trim() || '#FF8888'
    const accentDark = style.getPropertyValue('--accent-color-dark').trim() || '#993333'
    setColors({ accent, accentDark })
  }, [])

  return colors
}
