'use client'

import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export function Header() {
  const { user, signOut, loading } = useAuth()

  return (
    <header className="h-16 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
          Welcome back
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {loading ? (
          <span className="text-sm text-slate-500">Loading...</span>
        ) : user ? (
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600 dark:text-slate-400">
              {user.email}
            </span>
            <button
              onClick={() => signOut()}
              className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-500">Guest mode</span>
            <Link
              href="/login"
              className="text-sm text-brand-600 hover:text-brand-700 font-medium"
            >
              Sign in
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}
