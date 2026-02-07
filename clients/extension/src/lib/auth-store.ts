/**
 * Auth token store for Chrome Extension
 * Replaces @supabase/supabase-js session management with direct token storage
 */

declare const __API_URL__: string;
const API_URL = typeof __API_URL__ !== 'undefined' ? __API_URL__ : '';

const STORAGE_KEY = 'leetloop_auth_tokens';
const LEGACY_STORAGE_KEY = 'sb-ewezpbczwioxyflyffyy-auth-token';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_at?: number; // unix seconds
}

export interface AuthUser {
  id: string;
  email?: string;
}

/**
 * Store auth tokens in chrome.storage.local
 */
export async function setTokens(tokens: AuthTokens): Promise<void> {
  // Parse expiry from JWT if not provided
  if (!tokens.expires_at) {
    try {
      const parts = tokens.access_token.split('.');
      const payload = JSON.parse(atob(parts[1] ?? ''));
      tokens.expires_at = payload.exp;
    } catch {
      // If we can't parse, set a 1-hour default
      tokens.expires_at = Math.floor(Date.now() / 1000) + 3600;
    }
  }
  await chrome.storage.local.set({ [STORAGE_KEY]: tokens });
}

/**
 * Get stored auth tokens
 */
export async function getTokens(): Promise<AuthTokens | null> {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  return result[STORAGE_KEY] ?? null;
}

/**
 * Clear auth tokens (sign out)
 */
export async function clearTokens(): Promise<void> {
  await chrome.storage.local.remove([STORAGE_KEY, LEGACY_STORAGE_KEY]);
}

/**
 * Parse the JWT to extract user info (client-side decode, no verification)
 */
export async function getAuthUser(): Promise<AuthUser | null> {
  const tokens = await getTokens();
  if (!tokens?.access_token) return null;

  try {
    const parts = tokens.access_token.split('.');
    const payload = JSON.parse(atob(parts[1] ?? ''));
    const sub = payload.sub;
    if (!sub) return null;
    return { id: sub, email: payload.email };
  } catch {
    return null;
  }
}

/**
 * Get a valid access token, auto-refreshing if expired (with 60s buffer)
 */
export async function getValidAccessToken(): Promise<string | null> {
  const tokens = await getTokens();
  if (!tokens) return null;

  const now = Math.floor(Date.now() / 1000);
  const isExpired = tokens.expires_at ? tokens.expires_at - now < 60 : false;

  if (!isExpired) {
    return tokens.access_token;
  }

  // Token expired or about to expire, refresh it
  if (!tokens.refresh_token) return null;

  const apiUrl = API_URL || (await getApiUrlFromConfig());
  if (!apiUrl) return null;

  try {
    const resp = await fetch(`${apiUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });

    if (!resp.ok) {
      console.error('[LeetLoop] Token refresh failed:', resp.status);
      // Clear tokens on auth failure
      if (resp.status === 401) {
        await clearTokens();
      }
      return null;
    }

    const data = await resp.json();
    const newTokens: AuthTokens = {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      expires_at: Math.floor(Date.now() / 1000) + (data.expires_in || 3600),
    };
    await setTokens(newTokens);
    return newTokens.access_token;
  } catch (error) {
    console.error('[LeetLoop] Token refresh error:', error);
    return null;
  }
}

/**
 * Listen for auth token changes in storage
 */
export function onAuthStateChange(
  callback: (user: AuthUser | null) => void
): { unsubscribe: () => void } {
  const listener = (
    changes: { [key: string]: chrome.storage.StorageChange },
    areaName: string
  ) => {
    if (areaName !== 'local' || !(STORAGE_KEY in changes)) return;

    const newTokens: AuthTokens | undefined = changes[STORAGE_KEY].newValue;
    if (!newTokens?.access_token) {
      callback(null);
      return;
    }

    try {
      const parts = newTokens.access_token.split('.');
      const payload = JSON.parse(atob(parts[1] ?? ''));
      callback({ id: payload.sub, email: payload.email });
    } catch {
      callback(null);
    }
  };

  chrome.storage.onChanged.addListener(listener);
  return { unsubscribe: () => chrome.storage.onChanged.removeListener(listener) };
}

async function getApiUrlFromConfig(): Promise<string> {
  const result = await chrome.storage.local.get('config');
  return result.config?.apiUrl || '';
}
