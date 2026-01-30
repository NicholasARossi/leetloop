'use client'

interface ActivityDay {
  date: string
  count: number // 0 = none, 1 = light, 2 = medium, 3 = high
}

interface ActivityGridProps {
  /** Activity data - array of 84 days (12 weeks) */
  data?: ActivityDay[]
  /** Number of weeks to display */
  weeks?: number
}

/**
 * GitHub-style activity grid showing daily check-ins.
 * Displays a grid of squares representing activity levels.
 */
export function ActivityGrid({ data, weeks = 12 }: ActivityGridProps) {
  // Generate mock data if none provided
  const activityData = data || generateMockData(weeks * 7)

  const totalDays = weeks * 7
  const activeDays = activityData.filter(d => d.count > 0).length

  return (
    <div className="activity-grid-container">
      <div className="activity-grid">
        {activityData.slice(0, totalDays).map((day, i) => (
          <div
            key={i}
            className={`activity-cell activity-level-${day.count}`}
            title={`${day.date}: ${day.count === 0 ? 'No activity' : `${day.count} problem${day.count > 1 ? 's' : ''}`}`}
          />
        ))}
      </div>
      <p className="activity-summary">
        {weeks} weeks · {activeDays} active days
      </p>
    </div>
  )
}

/**
 * Generate mock activity data for demo purposes.
 * Creates a pattern that shows increasing activity over time.
 */
function generateMockData(days: number): ActivityDay[] {
  const data: ActivityDay[] = []
  const today = new Date()

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)

    // Generate activity pattern - more active recently
    let count = 0
    const weekIndex = Math.floor((days - 1 - i) / 7)
    const dayOfWeek = (days - 1 - i) % 7

    // Increase probability of activity as we get closer to today
    const activityProbability = 0.3 + (weekIndex / (days / 7)) * 0.5

    if (i > 3) { // Past days
      if (Math.random() < activityProbability) {
        // Weight toward medium activity
        const rand = Math.random()
        if (rand < 0.3) count = 1
        else if (rand < 0.7) count = 2
        else count = 3
      }
      // Weekends slightly less active
      if (dayOfWeek === 5 || dayOfWeek === 6) {
        if (Math.random() < 0.3) count = 0
      }
    } else if (i === 0) {
      // Today - show as "current" (will be styled differently)
      count = -1 // Special value for "today"
    } else {
      // Future days
      count = -2 // Special value for "future"
    }

    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      count,
    })
  }

  return data
}
