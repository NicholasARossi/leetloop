'use client'

import { useState } from 'react'
import { clsx } from 'clsx'
import type { OnboardingStatus } from '@/lib/api'

interface HistoryStepProps {
  status: OnboardingStatus | null
  onImport: () => Promise<void>
  onSkip: () => Promise<void>
}

export function HistoryStep({ status, onImport, onSkip }: HistoryStepProps) {
  const [importing, setImporting] = useState(false)
  const [skipping, setSkipping] = useState(false)
  const [imported, setImported] = useState(false)

  const hasExtension = status?.extension_installed
  const importedCount = status?.problems_imported_count || 0

  async function handleImport() {
    setImporting(true)
    try {
      await onImport()
      setImported(true)
    } finally {
      setImporting(false)
    }
  }

  async function handleSkip() {
    setSkipping(true)
    try {
      await onSkip()
    } finally {
      setSkipping(false)
    }
  }

  return (
    <div>
      <h2 className="section-title mb-2">Import Your LeetCode History</h2>
      <p className="text-gray-600 mb-6">
        Credit your completed problems and seed your skill scores from past performance.
      </p>

      <div className="space-y-6">
        {/* Status Check */}
        {!hasExtension && (
          <div className="p-4 bg-yellow-50 border-[2px] border-yellow-400">
            <p className="text-sm text-yellow-800">
              <strong>Note:</strong> Without the extension installed, we can only import history
              if you&apos;ve previously synced your LeetCode account with LeetLoop.
            </p>
          </div>
        )}

        {/* Import Info */}
        <div className="p-4 bg-gray-50 border-[2px] border-black">
          <h3 className="font-bold mb-3">What gets imported:</h3>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              All your solved problems (marked as completed)
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Submission timestamps and patterns
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Initial skill scores based on what you&apos;ve solved
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Failed problems for your review queue
            </li>
          </ul>
        </div>

        {/* Import Status */}
        {importedCount > 0 && (
          <div className={clsx(
            'p-4 border-[2px]',
            imported ? 'border-green-500 bg-green-50' : 'border-accent bg-accent/5'
          )}>
            <p className="font-bold">
              {imported ? 'Import Complete!' : 'Existing Data Found'}
            </p>
            <p className="text-sm text-gray-600 mt-1">
              We found <strong className="text-accent">{importedCount}</strong> submission records
              linked to your account.
            </p>
          </div>
        )}

        {/* No Data */}
        {importedCount === 0 && imported && (
          <div className="p-4 border-[2px] border-gray-300 bg-gray-50">
            <p className="font-bold">No Submissions Found</p>
            <p className="text-sm text-gray-600 mt-1">
              Don&apos;t worry - start practicing on LeetCode and your submissions will sync automatically
              through the extension.
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-between mt-8">
        <button
          onClick={handleSkip}
          disabled={skipping || importing}
          className="btn-secondary"
        >
          {skipping ? 'Skipping...' : 'Skip'}
        </button>

        {!imported ? (
          <button
            onClick={handleImport}
            disabled={importing || skipping}
            className={clsx(
              'btn-primary',
              (importing || skipping) && 'opacity-50 cursor-not-allowed'
            )}
          >
            {importing ? 'Importing...' : 'Import History'}
          </button>
        ) : (
          <button
            onClick={handleSkip}
            className="btn-primary"
          >
            Continue
          </button>
        )}
      </div>
    </div>
  )
}
