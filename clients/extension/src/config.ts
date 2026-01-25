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
  const result = await chrome.storage.local.get(['config', 'userId', 'guestUserId', 'webGuestUserId']);

  // Prefer webGuestUserId (synced from web app) over local guestUserId for consistency
  let guestUserId = result.webGuestUserId || result.guestUserId || result.userId;
  if (!guestUserId) {
    guestUserId = generateUUID();
    await chrome.storage.local.set({ guestUserId });
  }

  // If we got a web guest ID, also store it as guestUserId for consistency
  if (result.webGuestUserId && result.webGuestUserId !== result.guestUserId) {
    await chrome.storage.local.set({ guestUserId: result.webGuestUserId });
  }

  return {
    ...DEFAULT_CONFIG,
    ...result.config,
    userId: result.userId || guestUserId,
    guestUserId,
  };
}

/**
 * Sync guest UUID from web app
 * Called when the web-bridge detects a guest ID in localStorage
 */
export async function syncWebGuestId(webGuestId: string): Promise<void> {
  const result = await chrome.storage.local.get(['guestUserId']);

  // Only update if we don't have a local guest ID yet, or it matches
  // This prevents overwriting local data if the web has a different UUID
  if (!result.guestUserId) {
    await chrome.storage.local.set({
      guestUserId: webGuestId,
      webGuestUserId: webGuestId,
    });
    console.log('[LeetLoop] Synced guest ID from web:', webGuestId);
  } else {
    // Store web guest ID separately so we know they might be different
    await chrome.storage.local.set({ webGuestUserId: webGuestId });
  }
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
