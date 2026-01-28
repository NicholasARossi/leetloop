'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard'
import { leetloopApi, type OnboardingStatus } from '@/lib/api'

export default function OnboardingPage() {
  const router = useRouter()
  const { userId } = useAuth()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!userId) return

    async function checkOnboarding(uid: string) {
      try {
        const onboardingStatus = await leetloopApi.getOnboardingStatus(uid)
        setStatus(onboardingStatus)

        // If already onboarded, redirect to dashboard
        if (onboardingStatus.onboarding_complete) {
          router.push('/dashboard')
        }
      } catch (err) {
        console.error('Failed to check onboarding:', err)
        // If error, still show onboarding
      } finally {
        setLoading(false)
      }
    }

    checkOnboarding(userId)
  }, [userId, router])

  if (loading || !userId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen py-8 px-4">
      <OnboardingWizard userId={userId} initialStatus={status || undefined} />
    </div>
  )
}
