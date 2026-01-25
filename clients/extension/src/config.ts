/**
 * Extension configuration
 */

export interface Config {
  supabaseUrl: string;
  supabaseAnonKey: string;
  userId: string;
  enabled: boolean;
}

const DEFAULT_CONFIG: Config = {
  supabaseUrl: '',
  supabaseAnonKey: '',
  userId: '',
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
  const result = await chrome.storage.local.get(['config', 'userId']);

  // Ensure we have a user ID
  let userId = result.userId;
  if (!userId) {
    userId = generateUUID();
    await chrome.storage.local.set({ userId });
  }

  return {
    ...DEFAULT_CONFIG,
    ...result.config,
    userId,
  };
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
