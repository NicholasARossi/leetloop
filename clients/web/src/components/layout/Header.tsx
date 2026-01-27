'use client'

import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export function Header() {
  const { user, signOut, loading } = useAuth()

  return (
    <header className="h-14 bg-white border-b-[3px] border-black flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-sm text-gray-600">
          Welcome back
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {loading ? (
          <span className="text-sm text-gray-500">Loading...</span>
        ) : user ? (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user.email}
            </span>
            <button
              onClick={() => signOut()}
              className="text-sm text-gray-600 hover:text-black"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">Guest mode</span>
            <Link
              href="/login"
              className="btn-primary text-sm"
            >
              Sign in
            </Link>
          </div>
        )}
      </div>
    </header>
  )
}
