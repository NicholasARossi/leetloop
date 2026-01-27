'use client'

import { useEffect } from 'react'

const accentColors = [
  '#FF8888', // Coral
  '#88AAFF', // Blue
  '#88DDAA', // Green
  '#FFAA88', // Peach
  '#AA88FF', // Purple
  '#FF88BB', // Pink
  '#88DDDD', // Teal
  '#DDDD88', // Yellow
]

export function DailyAccent() {
  useEffect(() => {
    const dayOfYear = Math.floor(
      (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000
    )
    const colorIndex = dayOfYear % accentColors.length
    const accent = accentColors[colorIndex]

    document.documentElement.style.setProperty('--accent-color', accent)
    document.documentElement.style.setProperty('--accent-color-light', accent + '30')
  }, [])

  return null
}
