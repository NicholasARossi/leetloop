/**
 * Extension configuration
 */

import { getAuthUserId } from './auth';

export interface Config {
  supabaseUrl: string;
  supabaseAnonKey: string;
  userId: string;
  guestUserId: string;
  enabled: boolean;
}

const DEFAULT_CONFIG: Config = {
  supabaseUrl: '',
  supabaseAnonKey: '',
  userId: '',
  guestUserId: '',
  enabled: true,
};

/**
 * Generate a UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Load configuration from chrome.storage
 */
export async function loadConfig(): Promise<Config> {
  const result = await chrome.storage.local.get(['config', 'userId', 'guestUserId']);

  // Ensure we have a guest user ID (preserved for migration)
  let guestUserId = result.guestUserId || result.userId;
  if (!guestUserId) {
    guestUserId = generateUUID();
    await chrome.storage.local.set({ guestUserId });
  }

  return {
    ...DEFAULT_CONFIG,
    ...result.config,
    userId: result.userId || guestUserId,
    guestUserId,
  };
}

/**
 * Get the effective user ID (auth user ID or guest UUID)
 * This should be used for all data operations
 */
export async function getEffectiveUserId(): Promise<string> {
  // First check if user is authenticated
  const authUserId = await getAuthUserId();
  if (authUserId) {
    return authUserId;
  }

  // Fall back to guest ID
  const config = await loadConfig();
  return config.guestUserId;
}

/**
 * Save configuration to chrome.storage
 */
export async function saveConfig(config: Partial<Config>): Promise<void> {
  const current = await loadConfig();
  await chrome.storage.local.set({
    config: { ...current, ...config },
  });
}

/**
 * Check if Supabase is configured
 */
export function isSupabaseConfigured(config: Config): boolean {
  return !!(config.supabaseUrl && config.supabaseAnonKey);
}
