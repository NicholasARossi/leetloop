/**
 * Authentication module for Chrome Extension
 * Handles Google OAuth by redirecting to the web app
 */

import {
  type AuthUser,
  getAuthUser,
  getTokens,
  clearTokens,
  onAuthStateChange as onTokenChange,
} from './lib/auth-store';

// Web app URL for authentication - injected at build time via WEB_APP_URL env var
declare const __WEB_APP_URL__: string;
const WEB_APP_URL = __WEB_APP_URL__;

/**
 * Sign in with Google by opening the web app login page
 * The web app handles OAuth and the web-bridge content script
 * syncs the session back to the extension
 */
export async function signInWithGoogle(): Promise<{ user: AuthUser | null; error: Error | null; redirected: boolean }> {
  try {
    const loginUrl = `${WEB_APP_URL}/login?source=extension`;
    await chrome.tabs.create({ url: loginUrl });
    return { user: null, error: null, redirected: true };
  } catch (error) {
    console.error('[LeetLoop] Failed to open login page:', error);
    return { user: null, error: error as Error, redirected: false };
  }
}

/**
 * Sign out the current user
 */
export async function signOut(): Promise<{ error: Error | null }> {
  try {
    await clearTokens();

    // Clear any cached identity tokens
    try {
      await chrome.identity.clearAllCachedAuthTokens();
    } catch {
      // Ignore errors from clearing tokens
    }

    return { error: null };
  } catch (error) {
    return { error: error as Error };
  }
}

/**
 * Get the current user
 */
export async function getCurrentUser(): Promise<AuthUser | null> {
  return getAuthUser();
}

/**
 * Get the current session (tokens + user)
 */
export async function getSession(): Promise<{
  access_token: string;
  refresh_token: string;
  user: AuthUser | null;
} | null> {
  const tokens = await getTokens();
  if (!tokens) return null;

  const user = await getAuthUser();
  return {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    user,
  };
}

/**
 * Subscribe to auth state changes via chrome.storage.onChanged
 */
export function onAuthStateChange(
  callback: (user: AuthUser | null) => void
): { unsubscribe: () => void } {
  return onTokenChange(callback);
}

/**
 * Get the auth user ID if authenticated, null otherwise
 */
export async function getAuthUserId(): Promise<string | null> {
  const user = await getAuthUser();
  return user?.id ?? null;
}

// Re-export for convenience
export { setTokens, clearTokens } from './lib/auth-store';
export type { AuthUser } from './lib/auth-store';
