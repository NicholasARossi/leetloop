'use client'

import { useState, useEffect } from 'react'

interface ExtensionStepProps {
  userId: string
  onVerified: () => Promise<void>
  onSkip: () => Promise<void>
}

export function ExtensionStep({ userId, onVerified, onSkip }: ExtensionStepProps) {
  const [checking, setChecking] = useState(false)
  const [skipping, setSkipping] = useState(false)
  const [pollingCount, setPollingCount] = useState(0)

  // Poll for extension verification
  useEffect(() => {
    const interval = setInterval(() => {
      setPollingCount(prev => prev + 1)
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  // This effect would normally check if extension is connected
  // In production, the extension would call an API to verify connection
  useEffect(() => {
    // Check if extension sent a message to the page
    const handleExtensionMessage = (event: MessageEvent) => {
      if (event.data?.type === 'LEETLOOP_EXTENSION_CONNECTED') {
        handleVerify()
      }
    }

    window.addEventListener('message', handleExtensionMessage)
    return () => window.removeEventListener('message', handleExtensionMessage)
  })

  async function handleVerify() {
    setChecking(true)
    try {
      await onVerified()
    } finally {
      setChecking(false)
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
      <h2 className="section-title mb-2">Install the Chrome Extension</h2>
      <p className="text-gray-600 mb-6">
        The extension captures your LeetCode practice sessions. This is how we learn from your struggle.
      </p>

      <div className="space-y-6">
        {/* Install Instructions */}
        <div className="p-4 bg-gray-50 border-[2px] border-black">
          <h3 className="font-bold mb-3">Installation Steps:</h3>
          <ol className="space-y-3 text-sm">
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs flex-shrink-0">1</span>
              <span>
                Click the button below to open the Chrome Web Store
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs flex-shrink-0">2</span>
              <span>
                Click &quot;Add to Chrome&quot; and confirm the installation
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs flex-shrink-0">3</span>
              <span>
                Visit <a href="https://leetcode.com" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">leetcode.com</a> and the extension will sync with your account
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center text-xs flex-shrink-0">4</span>
              <span>
                Come back here and click &quot;I&apos;ve Installed It&quot;
              </span>
            </li>
          </ol>
        </div>

        {/* Install Button */}
        <div className="text-center">
          <a
            href="https://chrome.google.com/webstore/detail/leetloop"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
              <circle cx="12" cy="12" r="4"/>
            </svg>
            Install Extension
          </a>
        </div>

        {/* Why This Matters */}
        <div className="p-4 border-[2px] border-accent bg-accent/5">
          <h4 className="font-bold text-sm mb-2">Why is this important?</h4>
          <p className="text-sm text-gray-600">
            LeetLoop&apos;s AI learns from your submissions to understand where you struggle.
            Without the extension, we can&apos;t capture your practice sessions and personalize your missions.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-between mt-8">
        <button
          onClick={handleSkip}
          disabled={skipping}
          className="btn-secondary"
        >
          {skipping ? 'Skipping...' : 'Skip for Now'}
        </button>

        <button
          onClick={handleVerify}
          disabled={checking}
          className="btn-primary"
        >
          {checking ? 'Checking...' : "I've Installed It"}
        </button>
      </div>

      {pollingCount > 0 && (
        <p className="text-center text-xs text-gray-400 mt-4">
          Checking for extension... (attempt {pollingCount})
        </p>
      )}
    </div>
  )
}
