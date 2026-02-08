'use client'

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { SkillScore } from '@/lib/api'
import { useAccentColors } from '@/hooks/useAccentColors'

interface SkillRadarProps {
  skills: SkillScore[]
  className?: string
}

export function SkillRadar({ skills, className }: SkillRadarProps) {
  const { accent } = useAccentColors()

  // Take top 8 skills for the radar chart
  const chartData = skills
    .sort((a, b) => b.total_attempts - a.total_attempts)
    .slice(0, 8)
    .map((skill) => ({
      tag: skill.tag.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
      score: Math.round(skill.score),
      fullMark: 100,
    }))

  if (chartData.length === 0) {
    return (
      <div className={className}>
        <div className="flex items-center justify-center h-64 text-gray-500">
          No skill data yet. Start solving problems!
        </div>
      </div>
    )
  }

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
          <PolarGrid stroke="#e5e5e5" />
          <PolarAngleAxis
            dataKey="tag"
            tick={{ fill: '#737373', fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fill: '#a3a3a3', fontSize: 10 }}
          />
          <Radar
            name="Skill Score"
            dataKey="score"
            stroke={accent}
            fill={accent}
            fillOpacity={0.3}
          />
          <Tooltip
            formatter={(value: number) => [`${value}/100`, 'Score']}
            contentStyle={{
              backgroundColor: '#262626',
              border: 'none',
              borderRadius: '8px',
              color: '#fafafa',
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
