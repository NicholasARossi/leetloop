'use client'

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo,
  ReactNode,
} from 'react'
import { User, Session } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/client'

// Storage keys for extension bridge
const STORAGE_KEYS = {
  SESSION_BRIDGE: 'leetloop_session_bridge',
  GUEST_ID: 'leetloop_user_id',
  MIGRATION_COMPLETE: 'leetloop_migration_complete',
}

// Custom events for extension bridge
const CUSTOM_EVENTS = {
  AUTH_CHANGE: 'leetloop:auth-change',
  SIGNED_OUT: 'leetloop:signed-out',
  GUEST_ID: 'leetloop:guest-id',
}

// Get the singleton client
function getSupabase() {
  return createClient()
}

/**
 * Store session tokens in localStorage for extension bridge
 */
function storeSessionBridge(session: Session | null): void {
  if (typeof window === 'undefined') return

  console.log('[LeetLoop Web] storeSessionBridge called, hasSession:', !!session)

  if (session?.access_token && session?.refresh_token) {
    const bridgeData = {
      access_token: session.access_token,
      refresh_token: session.refresh_token,
    }
    localStorage.setItem(STORAGE_KEYS.SESSION_BRIDGE, JSON.stringify(bridgeData))
    console.log('[LeetLoop Web] Session bridge stored in localStorage')

    // Dispatch custom event for extension bridge
    window.dispatchEvent(
      new CustomEvent(CUSTOM_EVENTS.AUTH_CHANGE, { detail: bridgeData })
    )
    console.log('[LeetLoop Web] Dispatched auth-change event')
  } else {
    localStorage.removeItem(STORAGE_KEYS.SESSION_BRIDGE)
  }
}

/**
 * Dispatch guest ID to extension bridge
 */
function dispatchGuestId(guestId: string): void {
  if (typeof window === 'undefined') return

  window.dispatchEvent(
    new CustomEvent(CUSTOM_EVENTS.GUEST_ID, { detail: guestId })
  )
}

/**
 * Notify extension of sign out
 */
function notifySignOut(): void {
  if (typeof window === 'undefined') return

  localStorage.removeItem(STORAGE_KEYS.SESSION_BRIDGE)
  window.dispatchEvent(new CustomEvent(CUSTOM_EVENTS.SIGNED_OUT))
}

interface AuthContextType {
  user: User | null
  session: Session | null
  userId: string | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const supabase = useMemo(() => getSupabase(), [])

  // Get the effective user ID (from auth or localStorage for anon users)
  const userId = user?.id || getAnonUserId()

  useEffect(() => {
    let mounted = true
    let subscription: { unsubscribe: () => void } | null = null

    const initAuth = async () => {
      try {
        // Get initial session
        const { data: { session } } = await supabase.auth.getSession()
        if (mounted) {
          setSession(session)
          setUser(session?.user ?? null)
          setLoading(false)

          // Store session for extension bridge
          storeSessionBridge(session)
        }
      } catch (error) {
        // Ignore AbortError from locks in dev mode
        if (error instanceof Error && error.name === 'AbortError') {
          console.log('[LeetLoop] Ignoring AbortError in dev mode')
        } else {
          console.error('[LeetLoop] Error getting session:', error)
        }
        if (mounted) {
          setLoading(false)
        }
      }
    }

    initAuth()

    // Dispatch guest ID for extension bridge on mount
    const guestId = getAnonUserId()
    if (guestId) {
      dispatchGuestId(guestId)
    }

    // Listen for auth changes
    try {
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (mounted) {
          setSession(session)
          setUser(session?.user ?? null)
          setLoading(false)

          // Store session for extension bridge
          storeSessionBridge(session)

          // Handle migration when user signs in
          if (event === 'SIGNED_IN' && session?.user) {
            await migrateGuestDataIfNeeded(supabase, session.user.id)
          }

          // Notify extension of sign out
          if (event === 'SIGNED_OUT') {
            notifySignOut()
          }
        }
      })
      subscription = data.subscription
    } catch (error) {
      console.error('[LeetLoop] Error setting up auth listener:', error)
    }

    return () => {
      mounted = false
      subscription?.unsubscribe()
    }
  }, [supabase])

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    if (error) throw error
  }

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
    })
    if (error) throw error
  }

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    if (error) throw error
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    // Explicitly notify extension (also handled in onAuthStateChange but being explicit)
    notifySignOut()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        userId,
        loading,
        signIn,
        signUp,
        signInWithGoogle,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Helper to get anonymous user ID from localStorage
function getAnonUserId(): string | null {
  if (typeof window === 'undefined') return null

  let userId = localStorage.getItem('leetloop_user_id')
  if (!userId) {
    userId = crypto.randomUUID()
    localStorage.setItem('leetloop_user_id', userId)
  }
  return userId
}

// Migrate guest data to authenticated user
async function migrateGuestDataIfNeeded(
  supabase: ReturnType<typeof createClient>,
  authUserId: string
) {
  if (typeof window === 'undefined') return

  // Check if migration already done
  const migrationDone = localStorage.getItem('leetloop_migration_complete')
  if (migrationDone === 'true') {
    console.log('[LeetLoop] Migration already marked complete, skipping')
    console.log('[LeetLoop] To retry migration, run: localStorage.removeItem("leetloop_migration_complete")')
    return
  }

  // Get guest user ID
  const guestUserId = localStorage.getItem('leetloop_user_id')
  if (!guestUserId) {
    console.log('[LeetLoop] No guest user ID found, nothing to migrate')
    localStorage.setItem('leetloop_migration_complete', 'true')
    return
  }

  if (guestUserId === authUserId) {
    console.log('[LeetLoop] Guest ID matches auth ID, no migration needed')
    localStorage.setItem('leetloop_migration_complete', 'true')
    return
  }

  console.log('[LeetLoop] Starting migration...')
  console.log('[LeetLoop] Guest UUID:', guestUserId)
  console.log('[LeetLoop] Auth User ID:', authUserId)

  try {
    const { data, error } = await supabase.rpc('migrate_guest_to_auth', {
      p_guest_id: guestUserId,
      p_auth_id: authUserId,
    })

    if (error) {
      console.error('[LeetLoop] Migration RPC error:', error)
      console.error('[LeetLoop] Error code:', error.code)
      console.error('[LeetLoop] Error message:', error.message)
      console.error('[LeetLoop] Error details:', error.details)
      console.error('[LeetLoop] Migration NOT marked complete due to error')
      console.error('[LeetLoop] You can manually migrate by running SQL in Supabase:')
      console.error(`UPDATE submissions SET user_id = '${authUserId}' WHERE user_id = '${guestUserId}';`)
      console.error(`UPDATE skill_scores SET user_id = '${authUserId}' WHERE user_id = '${guestUserId}';`)
      console.error(`UPDATE review_queue SET user_id = '${authUserId}' WHERE user_id = '${guestUserId}';`)
      return
    }

    // Verify response structure
    if (!data || typeof data !== 'object') {
      console.error('[LeetLoop] Migration returned unexpected data:', data)
      console.error('[LeetLoop] Migration NOT marked complete due to unexpected response')
      return
    }

    // Check if migration actually succeeded
    if (data.success !== true) {
      console.error('[LeetLoop] Migration returned success=false:', data)
      console.error('[LeetLoop] Migration NOT marked complete')
      return
    }

    console.log('[LeetLoop] Migration successful!')
    console.log('[LeetLoop] Migrated counts:', data.migrated)
    localStorage.setItem('leetloop_migration_complete', 'true')

    // Update guest ID to auth ID so future local operations use correct ID
    localStorage.setItem('leetloop_user_id', authUserId)
    console.log('[LeetLoop] Updated local user ID to auth ID')
  } catch (error) {
    console.error('[LeetLoop] Migration exception:', error)
    console.error('[LeetLoop] Migration NOT marked complete due to exception')
    console.error('[LeetLoop] Guest UUID for manual migration:', guestUserId)
    console.error('[LeetLoop] Auth User ID for manual migration:', authUserId)
  }
}

// Export helper for debugging - call from browser console: window.resetLeetLoopMigration()
if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).resetLeetLoopMigration = () => {
    localStorage.removeItem('leetloop_migration_complete')
    console.log('[LeetLoop] Migration flag cleared. Sign out and back in to retry migration.')
  }

  (window as unknown as Record<string, unknown>).getLeetLoopMigrationInfo = () => {
    console.log('[LeetLoop] Migration complete:', localStorage.getItem('leetloop_migration_complete'))
    console.log('[LeetLoop] Guest user ID:', localStorage.getItem('leetloop_user_id'))
  }
}
