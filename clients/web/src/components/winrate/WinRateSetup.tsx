'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import { leetloopApi, type SetWinRateTargetsRequest } from '@/lib/api'

interface WinRateSetupProps {
  userId: string
  initialTargets?: {
    easy_target?: number
    medium_target?: number
    hard_target?: number
    optimality_threshold?: number
  }
  onComplete?: () => void
}

export function WinRateSetup({ userId, initialTargets, onComplete }: WinRateSetupProps) {
  const [easyTarget, setEasyTarget] = useState(Math.round((initialTargets?.easy_target ?? 0.9) * 100))
  const [mediumTarget, setMediumTarget] = useState(Math.round((initialTargets?.medium_target ?? 0.7) * 100))
  const [hardTarget, setHardTarget] = useState(Math.round((initialTargets?.hard_target ?? 0.5) * 100))
  const [threshold, setThreshold] = useState(initialTargets?.optimality_threshold ?? 70)
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    setSaving(true)
    try {
      const request: SetWinRateTargetsRequest = {
        easy_target: easyTarget / 100,
        medium_target: mediumTarget / 100,
        hard_target: hardTarget / 100,
        optimality_threshold: threshold,
      }
      await leetloopApi.setWinRateTargets(userId, request)
      onComplete?.()
    } catch (err) {
      console.error('Failed to set targets:', err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="space-y-6 max-w-md">
        <div>
          <label className="block text-sm font-bold mb-2">
            Easy Target: <span className="text-accent">{easyTarget}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={easyTarget}
            onChange={(e) => setEasyTarget(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-bold mb-2">
            Medium Target: <span className="text-accent">{mediumTarget}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={mediumTarget}
            onChange={(e) => setMediumTarget(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-bold mb-2">
            Hard Target: <span className="text-accent">{hardTarget}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={hardTarget}
            onChange={(e) => setHardTarget(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-bold mb-2">
            Optimality Threshold: <span className="text-accent">{threshold}th percentile</span>
          </label>
          <input
            type="range"
            min={50}
            max={100}
            value={threshold}
            onChange={(e) => setThreshold(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>50th</span>
            <span>75th</span>
            <span>100th</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Solutions at or above this runtime percentile are considered &quot;optimal&quot;.
          </p>
        </div>
      </div>

      <div className="flex justify-end mt-6">
        <button
          onClick={handleSubmit}
          disabled={saving}
          className={clsx('btn-primary', saving && 'opacity-50 cursor-not-allowed')}
        >
          {saving ? 'Saving...' : 'Set Targets'}
        </button>
      </div>
    </div>
  )
}
