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

// Create a single client instance outside the component
let supabaseInstance: ReturnType<typeof createClient> | null = null
function getSupabase() {
  if (!supabaseInstance) {
    supabaseInstance = createClient()
  }
  return supabaseInstance
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

    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (mounted) {
        setSession(session)
        setUser(session?.user ?? null)
        setLoading(false)
      }
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (mounted) {
        setSession(session)
        setUser(session?.user ?? null)
        setLoading(false)

        // Handle migration when user signs in
        if (event === 'SIGNED_IN' && session?.user) {
          await migrateGuestDataIfNeeded(supabase, session.user.id)
        }
      }
    })

    return () => {
      mounted = false
      subscription.unsubscribe()
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
    return
  }

  // Get guest user ID
  const guestUserId = localStorage.getItem('leetloop_user_id')
  if (!guestUserId || guestUserId === authUserId) {
    localStorage.setItem('leetloop_migration_complete', 'true')
    return
  }

  console.log('[LeetLoop] Migrating guest data from', guestUserId, 'to', authUserId)

  try {
    const { data, error } = await supabase.rpc('migrate_guest_to_auth', {
      p_guest_id: guestUserId,
      p_auth_id: authUserId,
    })

    if (error) {
      console.error('[LeetLoop] Migration error:', error)
      return
    }

    console.log('[LeetLoop] Migration complete:', data)
    localStorage.setItem('leetloop_migration_complete', 'true')
  } catch (error) {
    console.error('[LeetLoop] Migration exception:', error)
  }
}
