'use client'

import { ProgressTrend } from '@/lib/api'
import { useMemo } from 'react'

interface ActivityHeatmapProps {
  trends: ProgressTrend[]
}

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function ActivityHeatmap({ trends }: ActivityHeatmapProps) {
  const { weeks, monthLabels, maxCount } = useMemo(() => {
    const dateMap = new Map<string, number>()
    let maxCount = 0
    for (const t of trends) {
      dateMap.set(t.date, t.submissions)
      if (t.submissions > maxCount) maxCount = t.submissions
    }

    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStr = formatDate(today)

    // Go back ~13 weeks, aligned to start on a Sunday
    const totalWeeks = 13
    const start = new Date(today)
    start.setDate(start.getDate() - (totalWeeks * 7) + 1)
    start.setDate(start.getDate() - start.getDay()) // align to Sunday

    const weeks: { date: string; count: number; isToday: boolean; isFuture: boolean }[][] = []
    const monthLabels: { label: string; weekIndex: number }[] = []
    let lastMonth = -1

    const cursor = new Date(start)

    while (true) {
      if (cursor.getDay() === 0) {
        if (cursor > today && weeks.length > 0) break
        weeks.push([])

        if (cursor.getMonth() !== lastMonth) {
          monthLabels.push({
            label: cursor.toLocaleString('en-US', { month: 'short' }),
            weekIndex: weeks.length - 1,
          })
          lastMonth = cursor.getMonth()
        }
      }

      const dateStr = formatDate(cursor)
      const isFuture = dateStr > todayStr

      weeks[weeks.length - 1].push({
        date: dateStr,
        count: isFuture ? 0 : (dateMap.get(dateStr) || 0),
        isToday: dateStr === todayStr,
        isFuture,
      })

      cursor.setDate(cursor.getDate() + 1)

      // Stop after completing the week that contains today
      if (cursor.getDay() === 0 && cursor > today) break
    }

    return { weeks, monthLabels, maxCount }
  }, [trends])

  const getColor = (count: number, isFuture: boolean) => {
    if (isFuture) return 'transparent'
    if (count === 0) return '#e5e7eb'
    if (maxCount <= 1) return 'var(--accent-color)'
    const ratio = count / maxCount
    if (ratio <= 0.25) return '#ffcccc'
    if (ratio <= 0.5) return '#FFB8B8'
    if (ratio <= 0.75) return '#FF8888'
    return '#d05050'
  }

  const cellSize = 11
  const gap = 2
  const dayLabelWidth = 16
  const dayLabels = ['', 'M', '', 'W', '', 'F', '']

  return (
    <div>
      {/* Month labels */}
      <div className="flex" style={{ paddingLeft: dayLabelWidth, marginBottom: 2, height: 14 }}>
        {weeks.map((_, wi) => {
          const ml = monthLabels.find(m => m.weekIndex === wi)
          return (
            <div
              key={wi}
              className="text-[9px] text-gray-400 uppercase tracking-wide"
              style={{ width: cellSize + gap, flexShrink: 0 }}
            >
              {ml?.label || ''}
            </div>
          )
        })}
      </div>

      {/* Grid */}
      <div className="flex">
        {/* Day-of-week labels */}
        <div className="flex flex-col" style={{ width: dayLabelWidth }}>
          {dayLabels.map((label, i) => (
            <div
              key={i}
              className="text-[9px] text-gray-400 flex items-center"
              style={{ height: cellSize + gap }}
            >
              {label}
            </div>
          ))}
        </div>

        {/* Week columns */}
        <div className="flex" style={{ gap }}>
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col" style={{ gap }}>
              {week.map((day, di) => (
                <div
                  key={di}
                  title={day.isFuture ? '' : `${day.date}: ${day.count} submissions`}
                  style={{
                    width: cellSize,
                    height: cellSize,
                    backgroundColor: getColor(day.count, day.isFuture),
                    outline: day.isToday ? '2px solid black' : undefined,
                    outlineOffset: -1,
                    borderRadius: 1,
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
