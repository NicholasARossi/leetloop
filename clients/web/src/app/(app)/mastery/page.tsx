'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type MasteryResponse,
  type DomainDetailResponse,
} from '@/lib/api'
import { ReadinessScore } from '@/components/mastery/ReadinessScore'
import { DomainCard } from '@/components/mastery/DomainCard'
import { DomainDetail } from '@/components/mastery/DomainDetail'

export default function MasteryPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<MasteryResponse | null>(null)
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [domainDetail, setDomainDetail] = useState<DomainDetailResponse | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    async function loadData() {
      if (!userId) return

      setLoading(true)
      setError(null)

      try {
        const masteryData = await leetloopApi.getMastery(userId)
        setData(masteryData)
      } catch (err) {
        console.error('Failed to load mastery data:', err)
        setError('Failed to load data. Make sure the backend is running.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [userId])

  async function handleDomainClick(domainName: string) {
    if (!userId) return

    setSelectedDomain(domainName)
    setLoadingDetail(true)

    try {
      const detail = await leetloopApi.getDomainDetail(userId, domainName)
      setDomainDetail(detail)
    } catch (err) {
      console.error('Failed to load domain detail:', err)
      // Still show the modal with basic info
      const domain = data?.domains.find(d => d.name === domainName)
      if (domain) {
        setDomainDetail({
          domain,
          failure_analysis: undefined,
          recommended_path: [],
          recent_submissions: [],
        })
      }
    } finally {
      setLoadingDetail(false)
    }
  }

  function handleCloseDetail() {
    setSelectedDomain(null)
    setDomainDetail(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading mastery data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-coral mb-4">{error}</p>
        <p className="text-sm text-gray-500">
          Make sure the backend API is running.
        </p>
      </div>
    )
  }

  if (!data) {
    return null
  }

  // Group domains by status for better visualization
  const weakDomains = data.domains.filter(d => d.status === 'WEAK')
  const fairDomains = data.domains.filter(d => d.status === 'FAIR')
  const goodDomains = data.domains.filter(d => d.status === 'GOOD')
  const strongDomains = data.domains.filter(d => d.status === 'STRONG')

  return (
    <div className="space-y-6">
      {/* Readiness Score Header */}
      <ReadinessScore
        score={data.readiness_score}
        summary={data.readiness_summary}
      />

      {/* Focus Areas */}
      {data.weak_areas.length > 0 && (
        <div className="card border-l-4 border-l-coral">
          <h3 className="font-semibold text-black mb-2">
            Focus Areas
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.weak_areas.map(area => (
              <span
                key={area}
                className="tag"
              >
                {area}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Domain Grid */}
      <div className="space-y-6">
        {/* Weak domains first */}
        {weakDomains.length > 0 && (
          <div>
            <h2 className="section-title text-coral">
              Needs Work ({weakDomains.length})
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {weakDomains.map(domain => (
                <DomainCard
                  key={domain.name}
                  domain={domain}
                  onClick={() => handleDomainClick(domain.name)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Fair domains */}
        {fairDomains.length > 0 && (
          <div>
            <h2 className="section-title">
              Developing ({fairDomains.length})
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {fairDomains.map(domain => (
                <DomainCard
                  key={domain.name}
                  domain={domain}
                  onClick={() => handleDomainClick(domain.name)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Good domains */}
        {goodDomains.length > 0 && (
          <div>
            <h2 className="section-title">
              Proficient ({goodDomains.length})
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {goodDomains.map(domain => (
                <DomainCard
                  key={domain.name}
                  domain={domain}
                  onClick={() => handleDomainClick(domain.name)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Strong domains */}
        {strongDomains.length > 0 && (
          <div>
            <h2 className="section-title">
              Mastered ({strongDomains.length})
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {strongDomains.map(domain => (
                <DomainCard
                  key={domain.name}
                  domain={domain}
                  onClick={() => handleDomainClick(domain.name)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Domain Detail Modal */}
      {selectedDomain && domainDetail && !loadingDetail && (
        <DomainDetail
          data={domainDetail}
          onClose={handleCloseDetail}
        />
      )}

      {/* Loading detail overlay */}
      {loadingDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="text-white">Loading domain details...</div>
        </div>
      )}
    </div>
  )
}
