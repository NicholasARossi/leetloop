'use client'

import { createBrowserClient } from '@supabase/ssr'

// Singleton to prevent multiple clients in dev mode
let client: ReturnType<typeof createBrowserClient> | null = null

// No-op lock function to prevent AbortError in Next.js dev mode
// The navigator.locks API causes issues with HMR
const noopLock = async <R>(
  _name: string,
  _acquireTimeout: number,
  fn: () => Promise<R>
): Promise<R> => {
  return await fn()
}

export function createClient() {
  if (client) return client

  client = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      auth: {
        flowType: 'pkce',
        detectSessionInUrl: true,
        persistSession: true,
        debug: false,
        lock: noopLock,
      },
    }
  )

  return client
}
