'use client'

import { WinRateSetup } from '@/components/winrate/WinRateSetup'

interface WinRateStepProps {
  userId: string
  onComplete: () => Promise<void>
}

export function WinRateStep({ userId, onComplete }: WinRateStepProps) {
  return (
    <div>
      <h2 className="section-title mb-2">Set your win rate targets</h2>
      <p className="text-gray-600 mb-6">
        Set your target solve rates per difficulty. We&apos;ll measure your progress
        on unseen problems and track how you improve over time.
      </p>

      <WinRateSetup userId={userId} onComplete={onComplete} />
    </div>
  )
}
