'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

export default function Home() {
  const { user, loading } = useAuth()

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-5xl font-bold text-slate-900 dark:text-white mb-4">
          LeetLoop
        </h1>
        <p className="text-xl text-slate-600 dark:text-slate-400 mb-2">
          Systematic LeetCode Coach
        </p>
        <p className="text-slate-500 dark:text-slate-500 mb-8">
          Most tools celebrate wins. <span className="text-brand-600 font-semibold">LeetLoop learns from struggle.</span>
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
          {loading ? (
            <div className="btn-primary opacity-50 cursor-wait">Loading...</div>
          ) : user ? (
            <Link href="/today" className="btn-primary">
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className="btn-primary">
                Get Started
              </Link>
              <Link href="/today" className="btn-secondary">
                Continue as Guest
              </Link>
            </>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-6 text-left">
          <div className="card p-6">
            <div className="text-3xl mb-3">1</div>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-2">
              Install Extension
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Add the Chrome extension to passively capture your LeetCode submissions.
            </p>
          </div>

          <div className="card p-6">
            <div className="text-3xl mb-3">2</div>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-2">
              Practice Normally
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Solve problems on LeetCode. Every submission is tracked automatically.
            </p>
          </div>

          <div className="card p-6">
            <div className="text-3xl mb-3">3</div>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-2">
              Review & Improve
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Get AI-powered insights and spaced repetition for problems you struggled with.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
