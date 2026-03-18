'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'
import { useAuth } from '@/contexts/AuthContext'

export type Megaview = 'leetcode' | 'languages'

const megaviews: { id: Megaview; label: string; href: string; icon: React.ReactNode }[] = [
  {
    id: 'leetcode',
    label: 'LeetCode',
    href: '/dashboard',
    icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  },
  {
    id: 'languages',
    label: 'Languages',
    href: '/language',
    icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" /></svg>,
  },
]

const routeToMegaview: Record<string, Megaview> = {
  '/dashboard': 'leetcode',
  '/objective': 'leetcode',
  '/path': 'leetcode',
  '/mastery': 'leetcode',
  '/reviews': 'leetcode',
  '/submissions': 'leetcode',
  '/coach': 'leetcode',
  '/language': 'languages',
  '/system-design': 'leetcode',
  '/ml-coding': 'leetcode',
}

export function getMegaviewFromPath(pathname: string): Megaview {
  for (const [route, mv] of Object.entries(routeToMegaview)) {
    if (pathname === route || pathname.startsWith(`${route}/`)) {
      return mv
    }
  }
  return 'leetcode'
}

export function MegaviewTabs() {
  const pathname = usePathname()
  const activeMegaview = getMegaviewFromPath(pathname)
  const { user, signOut, loading } = useAuth()

  return (
    <div className="flex items-stretch bg-gray-500 h-11 border-b-[3px] border-black">
      <Link href="/dashboard" className="px-5 flex items-center border-r border-gray-400">
        <span className="heading-accent text-sm">LEETLOOP</span>
      </Link>

      <nav className="flex flex-1">
        {megaviews.map((mv) => {
          const isActive = activeMegaview === mv.id
          return (
            <Link
              key={mv.id}
              href={mv.href}
              className={clsx(
                'flex items-center gap-2 px-6 text-xs font-semibold tracking-wide uppercase transition-all border-b-[3px]',
                isActive
                  ? 'text-white border-[var(--accent-color)] bg-gray-600'
                  : 'text-gray-300 border-transparent hover:text-white hover:bg-gray-600'
              )}
            >
              {mv.icon}
              {mv.label}
            </Link>
          )
        })}
      </nav>

      <div className="flex items-center px-5 text-xs">
        {loading ? (
          <span className="text-gray-300">Loading...</span>
        ) : user ? (
          <div className="flex items-center gap-3">
            <span className="text-gray-300">{user.email}</span>
            <button
              onClick={() => signOut()}
              className="text-gray-400 hover:text-white transition-colors"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-gray-400">Guest</span>
            <Link href="/login" className="text-white hover:text-gray-200 font-semibold">
              Sign in
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
