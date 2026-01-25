/**
 * Supabase client for Chrome Extension
 * Uses chrome.storage.local for session persistence (MV3 compatible)
 */

import { createClient, SupabaseClient, Session } from '@supabase/supabase-js';

// Extension environment variables (set during build or from options)
const SUPABASE_URL = '__SUPABASE_URL__';
const SUPABASE_ANON_KEY = '__SUPABASE_ANON_KEY__';

/**
 * Custom storage adapter for chrome.storage.local
 * Required for Manifest V3 service workers (no localStorage)
 */
const chromeStorageAdapter = {
  async getItem(key: string): Promise<string | null> {
    const result = await chrome.storage.local.get(key);
    return result[key] ?? null;
  },
  async setItem(key: string, value: string): Promise<void> {
    await chrome.storage.local.set({ [key]: value });
  },
  async removeItem(key: string): Promise<void> {
    await chrome.storage.local.remove(key);
  },
};

let supabaseClient: SupabaseClient | null = null;

/**
 * Get or create the Supabase client singleton
 */
export async function getSupabaseClient(): Promise<SupabaseClient | null> {
  if (supabaseClient) {
    return supabaseClient;
  }

  // Get config from storage (set via options page)
  const result = await chrome.storage.local.get('config');
  const config = result.config || {};

  const url = config.supabaseUrl || SUPABASE_URL;
  const key = config.supabaseAnonKey || SUPABASE_ANON_KEY;

  if (!url || url === '__SUPABASE_URL__' || !key || key === '__SUPABASE_ANON_KEY__') {
    console.log('[LeetLoop] Supabase not configured');
    return null;
  }

  supabaseClient = createClient(url, key, {
    auth: {
      storage: chromeStorageAdapter,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  });

  return supabaseClient;
}

/**
 * Reset the client (call after config changes)
 */
export function resetSupabaseClient(): void {
  supabaseClient = null;
}

/**
 * Get current session
 */
export async function getSession(): Promise<Session | null> {
  const client = await getSupabaseClient();
  if (!client) return null;

  const { data: { session } } = await client.auth.getSession();
  return session;
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return session !== null;
}
