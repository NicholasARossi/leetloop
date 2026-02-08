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

function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255

  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2

  if (max === min) return [0, 0, l * 100]

  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max - min)

  let h = 0
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6
  else if (max === g) h = ((b - r) / d + 2) / 6
  else h = ((r - g) / d + 4) / 6

  return [h * 360, s * 100, l * 100]
}

function hslToHex(h: number, s: number, l: number): string {
  s /= 100
  l /= 100
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => {
    const k = (n + h / 30) % 12
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)
    return Math.round(255 * color).toString(16).padStart(2, '0')
  }
  return `#${f(0)}${f(8)}${f(4)}`
}

export function DailyAccent() {
  useEffect(() => {
    const dayOfYear = Math.floor(
      (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000
    )
    const colorIndex = dayOfYear % accentColors.length
    const accent = accentColors[colorIndex]

    // Generate dark shade (reduce lightness by ~25%)
    const [h, s, l] = hexToHsl(accent)
    const darkHex = hslToHex(h, s, Math.max(l - 25, 10))

    // Parse RGB channels for Tailwind's <alpha-value> support
    const accentR = parseInt(accent.slice(1, 3), 16)
    const accentG = parseInt(accent.slice(3, 5), 16)
    const accentB = parseInt(accent.slice(5, 7), 16)
    const darkR = parseInt(darkHex.slice(1, 3), 16)
    const darkG = parseInt(darkHex.slice(3, 5), 16)
    const darkB = parseInt(darkHex.slice(5, 7), 16)

    document.documentElement.style.setProperty('--accent-color', accent)
    document.documentElement.style.setProperty('--accent-rgb', `${accentR} ${accentG} ${accentB}`)
    document.documentElement.style.setProperty('--accent-color-dark', darkHex)
    document.documentElement.style.setProperty('--accent-dark-rgb', `${darkR} ${darkG} ${darkB}`)

    // Opacity variants for heatmap
    document.documentElement.style.setProperty('--accent-color-20', accent + '33')
    document.documentElement.style.setProperty('--accent-color-40', accent + '66')
    document.documentElement.style.setProperty('--accent-color-60', accent + '99')
  }, [])

  return null
}
