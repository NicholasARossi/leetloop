'use client'

import { clsx } from 'clsx'

interface StatsCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  icon?: React.ReactNode
  className?: string
  sectionId?: string
}

export function StatsCard({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  icon,
  className,
  sectionId,
}: StatsCardProps) {
  return (
    <div className={clsx('card p-6 bracket-corners', className)}>
      {sectionId && (
        <div className="section-id mb-2">{sectionId}</div>
      )}
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="stat-value mt-1">
            {value}
          </p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">
              {subtitle}
            </p>
          )}
          {trend && trendValue && (
            <div
              className={clsx(
                'flex items-center gap-1 mt-2 text-sm font-medium',
                trend === 'up' && 'text-coral',
                trend === 'down' && 'text-black',
                trend === 'neutral' && 'text-gray-500'
              )}
            >
              {trend === 'up' && (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
              )}
              {trend === 'down' && (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              )}
              {trendValue}
            </div>
          )}
        </div>
        {icon && (
          <div className="text-gray-400">{icon}</div>
        )}
      </div>
    </div>
  )
}
