/**
 * Authentication module for Chrome Extension
 * Handles Google OAuth via chrome.identity.launchWebAuthFlow
 */

import { Session, User, AuthChangeEvent } from '@supabase/supabase-js';
import { getSupabaseClient, getSession } from './lib/supabase';

// OAuth configuration (set via manifest.json oauth2.client_id)
// const GOOGLE_CLIENT_ID = '__GOOGLE_CLIENT_ID__';

/**
 * Get the redirect URL for OAuth
 */
function getRedirectUrl(): string {
  return chrome.identity.getRedirectURL('oauth');
}

/**
 * Sign in with Google using chrome.identity
 */
export async function signInWithGoogle(): Promise<{ user: User | null; error: Error | null }> {
  const client = await getSupabaseClient();
  if (!client) {
    return { user: null, error: new Error('Supabase not configured') };
  }

  try {
    // Get the Supabase project URL from client
    const supabaseUrl = (client as any).supabaseUrl;
    const redirectUrl = getRedirectUrl();

    // Build the OAuth URL for Supabase
    const authUrl = new URL(`${supabaseUrl}/auth/v1/authorize`);
    authUrl.searchParams.set('provider', 'google');
    authUrl.searchParams.set('redirect_to', redirectUrl);
    authUrl.searchParams.set('skip_http_redirect', 'true');

    // Launch the OAuth flow
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

    // Parse the callback URL for tokens
    const url = new URL(responseUrl);
    const hashParams = new URLSearchParams(url.hash.substring(1));
    const accessToken = hashParams.get('access_token');
    const refreshToken = hashParams.get('refresh_token');

    if (!accessToken) {
      // Check for error
      const error = hashParams.get('error_description') || hashParams.get('error');
      return { user: null, error: new Error(error || 'No access token received') };
    }

    // Set the session in Supabase
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
