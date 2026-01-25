/**
 * Authentication module for Chrome Extension
 * Handles Google OAuth by redirecting to the web app
 */

import { Session, User, AuthChangeEvent } from '@supabase/supabase-js';
import { getSupabaseClient, getSession } from './lib/supabase';

// Web app URL for authentication (dev default, can be overridden)
const WEB_APP_URL = 'http://localhost:3001';

/**
 * Sign in with Google by opening the web app login page
 * The web app handles OAuth and the web-bridge content script
 * syncs the session back to the extension
 */
export async function signInWithGoogle(): Promise<{ user: User | null; error: Error | null; redirected: boolean }> {
  try {
    // Open the web app login page with source=extension parameter
    const loginUrl = `${WEB_APP_URL}/login?source=extension`;

    // Open in a new tab
    await chrome.tabs.create({ url: loginUrl });

    // Return immediately - the session will be synced via web-bridge
    // when the user completes authentication
    return { user: null, error: null, redirected: true };
  } catch (error) {
    console.error('[LeetLoop] Failed to open login page:', error);
    return { user: null, error: error as Error, redirected: false };
  }
}

/**
 * Legacy sign in method using chrome.identity (kept for reference)
 * @deprecated Use signInWithGoogle() which redirects to web app
 */
export async function signInWithGoogleLegacy(): Promise<{ user: User | null; error: Error | null }> {
  const client = await getSupabaseClient();
  if (!client) {
    return { user: null, error: new Error('Supabase not configured') };
  }

  try {
    const supabaseUrl = (client as any).supabaseUrl;
    const redirectUrl = chrome.identity.getRedirectURL('oauth');

    const authUrl = new URL(`${supabaseUrl}/auth/v1/authorize`);
    authUrl.searchParams.set('provider', 'google');
    authUrl.searchParams.set('redirect_to', redirectUrl);
    authUrl.searchParams.set('skip_http_redirect', 'true');

    const responseUrl = await new Promise<string>((resolve, reject) => {
      chrome.identity.launchWebAuthFlow(
        {
          url: authUrl.toString(),
          interactive: true,
        },
        (callbackUrl) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (callbackUrl) {
            resolve(callbackUrl);
          } else {
            reject(new Error('No callback URL received'));
          }
        }
      );
    });

    const url = new URL(responseUrl);
    const hashParams = new URLSearchParams(url.hash.substring(1));
    const accessToken = hashParams.get('access_token');
    const refreshToken = hashParams.get('refresh_token');

    if (!accessToken) {
      const error = hashParams.get('error_description') || hashParams.get('error');
      return { user: null, error: new Error(error || 'No access token received') };
    }

    const { data, error } = await client.auth.setSession({
      access_token: accessToken,
      refresh_token: refreshToken || '',
    });

    if (error) {
      return { user: null, error };
    }

    return { user: data.user, error: null };
  } catch (error) {
    console.error('[LeetLoop] OAuth error:', error);
    return { user: null, error: error as Error };
  }
}

/**
 * Sign out the current user
 */
export async function signOut(): Promise<{ error: Error | null }> {
  const client = await getSupabaseClient();
  if (!client) {
    return { error: new Error('Supabase not configured') };
  }

  try {
    const { error } = await client.auth.signOut();
    if (error) {
      return { error };
    }

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
export async function getCurrentUser(): Promise<User | null> {
  const client = await getSupabaseClient();
  if (!client) return null;

  const { data: { user } } = await client.auth.getUser();
  return user;
}

/**
 * Get the current session
 */
export { getSession };

/**
 * Subscribe to auth state changes
 */
export async function onAuthStateChange(
  callback: (event: AuthChangeEvent, session: Session | null) => void
): Promise<{ unsubscribe: () => void }> {
  const client = await getSupabaseClient();
  if (!client) {
    return { unsubscribe: () => {} };
  }

  const { data: { subscription } } = client.auth.onAuthStateChange(callback);
  return { unsubscribe: () => subscription.unsubscribe() };
}

/**
 * Get the auth user ID if authenticated, null otherwise
 */
export async function getAuthUserId(): Promise<string | null> {
  const session = await getSession();
  return session?.user?.id ?? null;
}
