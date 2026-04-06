'use client'

interface ModeSelectorProps {
  mode: 'stand_and_deliver' | 'breakdown'
  onModeChange: (mode: 'stand_and_deliver' | 'breakdown') => void
}

export function ModeSelector({ mode, onModeChange }: ModeSelectorProps) {
  return (
    <div className="flex gap-2 mb-4">
      <button
        onClick={() => onModeChange('stand_and_deliver')}
        className={`flex-1 px-4 py-3 rounded-lg border-2 text-left transition-all ${
          mode === 'stand_and_deliver'
            ? 'border-coral bg-coral/5'
            : 'border-gray-200 hover:border-gray-300'
        }`}
      >
        <div className="text-xs font-semibold uppercase tracking-wide mb-1">
          Stand & Deliver
        </div>
        <div className="text-[10px] text-gray-500">
          Single 25-min recording, graded on 6 dimensions
        </div>
      </button>
      <button
        onClick={() => onModeChange('breakdown')}
        className={`flex-1 px-4 py-3 rounded-lg border-2 text-left transition-all ${
          mode === 'breakdown'
            ? 'border-coral bg-coral/5'
            : 'border-gray-200 hover:border-gray-300'
        }`}
      >
        <div className="text-xs font-semibold uppercase tracking-wide mb-1">
          Breakdown
        </div>
        <div className="text-[10px] text-gray-500">
          7 phases, graded individually, gate at 3.0 to proceed
        </div>
      </button>
    </div>
  )
}
