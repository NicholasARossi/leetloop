/**
 * Supabase sync operations for the extension
 */

import type { Config } from './config';
import { loadConfig } from './config';
import type { StoredSubmission } from './types';
import { getSupabaseClient } from './lib/supabase';

// Build-time environment variables
declare const __SUPABASE_URL__: string;
declare const __SUPABASE_ANON_KEY__: string;
declare const __API_URL__: string;

const SUPABASE_URL = typeof __SUPABASE_URL__ !== 'undefined' ? __SUPABASE_URL__ : '';
const SUPABASE_ANON_KEY = typeof __SUPABASE_ANON_KEY__ !== 'undefined' ? __SUPABASE_ANON_KEY__ : '';
const API_URL = typeof __API_URL__ !== 'undefined' ? __API_URL__ : '';

/**
 * Get user ID directly from storage without using Supabase client
 * This avoids potential deadlocks with concurrent getSession calls
 */
async function getUserIdFromStorage(): Promise<string> {
  const storageKey = 'sb-ewezpbczwioxyflyffyy-auth-token';
  const result = await chrome.storage.local.get([storageKey, 'guestUserId']);

  // Try to get auth user ID from stored session
  const sessionData = result[storageKey];
  if (sessionData) {
    try {
      const parsed = JSON.parse(sessionData);
      if (parsed?.user?.id) {
        console.log('[LeetLoop] Using auth user ID from storage:', parsed.user.id);
        return parsed.user.id;
      }
    } catch (e) {
      console.log('[LeetLoop] Could not parse session data:', e);
    }
  }

  // Fall back to guest ID
  const config = await loadConfig();
  console.log('[LeetLoop] Using guest user ID:', config.guestUserId);
  return config.guestUserId;
}

/**
 * Sync a submission - routes through API if available, otherwise direct to Supabase
 */
export async function syncSubmission(
  config: Config,
  submission: StoredSubmission
): Promise<boolean> {
  console.log('[LeetLoop] syncSubmission starting for:', submission.problem_slug);

  const userId = await getUserIdFromStorage();
  console.log('[LeetLoop] Attempting sync with userId:', userId);

  // Use build-time API URL, fall back to config
  const apiUrl = API_URL || config.apiUrl;

  // Prefer API route if configured
  if (apiUrl) {
    console.log('[LeetLoop] Using API route:', apiUrl.substring(0, 30) + '...');
    return syncSubmissionViaApi(apiUrl, submission, userId);
  }

  // Fall back to direct Supabase
  console.log('[LeetLoop] Using direct Supabase route');
  return syncSubmissionFetch(config, submission, userId);
}

/**
 * Sync submission through the LeetLoop API backend
 */
async function syncSubmissionViaApi(
  apiUrl: string,
  submission: StoredSubmission,
  userId: string
): Promise<boolean> {
  try {
    const response = await fetch(`${apiUrl}/api/submissions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: submission.id,
        user_id: userId,
        problem_slug: submission.problem_slug,
        problem_title: submission.problem_title,
        problem_id: submission.problem_id,
        difficulty: submission.difficulty,
        tags: submission.tags,
        status: submission.status,
        runtime_ms: submission.runtime_ms,
        runtime_percentile: submission.runtime_percentile,
        memory_mb: submission.memory_mb,
        memory_percentile: submission.memory_percentile,
        attempt_number: submission.attempt_number,
        time_elapsed_seconds: submission.time_elapsed_seconds,
        language: submission.language,
        code: submission.code,
        code_length: submission.code_length,
        session_id: submission.session_id,
        submitted_at: submission.submitted_at,
      }),
    });

    if (response.ok) {
      const result = await response.json();
      console.log('[LeetLoop] Synced via API:', submission.id, result);
      return true;
    }

    const errorText = await response.text();
    console.error('[LeetLoop] API sync failed:', response.status, errorText);
    return false;
  } catch (error) {
    console.error('[LeetLoop] API sync error:', error);
    return false;
  }
}

/**
 * Fallback: Sync using raw fetch (when Supabase client not configured)
 */
async function syncSubmissionFetch(
  config: Config,
  submission: StoredSubmission,
  userId: string
): Promise<boolean> {
  // Use build-time values, fall back to config
  const supabaseUrl = SUPABASE_URL || config.supabaseUrl;
  const supabaseKey = SUPABASE_ANON_KEY || config.supabaseAnonKey;

  if (!supabaseUrl || !supabaseKey) {
    console.log('[LeetLoop] Supabase not configured, skipping sync');
    return false;
  }

  console.log('[LeetLoop] Using Supabase URL:', supabaseUrl.substring(0, 30) + '...');

  try {
    const response = await fetch(`${supabaseUrl}/rest/v1/submissions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`,
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify({
        id: submission.id,
        user_id: userId,
        problem_slug: submission.problem_slug,
        problem_title: submission.problem_title,
        problem_id: submission.problem_id,
        difficulty: submission.difficulty,
        tags: submission.tags,
        status: submission.status,
        runtime_ms: submission.runtime_ms,
        runtime_percentile: submission.runtime_percentile,
        memory_mb: submission.memory_mb,
        memory_percentile: submission.memory_percentile,
        attempt_number: submission.attempt_number,
        time_elapsed_seconds: submission.time_elapsed_seconds,
        language: submission.language,
        code: submission.code,
        code_length: submission.code_length,
        session_id: submission.session_id,
        submitted_at: submission.submitted_at,
      }),
    });

    if (response.ok) {
      console.log('[LeetLoop] Synced to Supabase:', submission.id);
      return true;
    }

    const errorText = await response.text();
    console.error('[LeetLoop] Supabase sync failed:', response.status, errorText);
    return false;
  } catch (error) {
    console.error('[LeetLoop] Supabase sync error:', error);
    return false;
  }
}

/**
 * Get user statistics from Supabase
 */
export async function getUserStats(config: Config): Promise<{
  total: number;
  accepted: number;
  failed: number;
} | null> {
  const client = await getSupabaseClient();
  const userId = await getUserIdFromStorage();

  if (client) {
    try {
      const { data, error } = await client.rpc('get_user_stats', {
        p_user_id: userId,
      });

      if (error) {
        console.error('[LeetLoop] Stats error:', error);
        return null;
      }

      return {
        total: data?.[0]?.total_submissions ?? 0,
        accepted: data?.[0]?.accepted_count ?? 0,
        failed: data?.[0]?.failed_count ?? 0,
      };
    } catch {
      return null;
    }
  }

  // Fallback to fetch
  if (!config.supabaseUrl || !config.supabaseAnonKey) {
    return null;
  }

  try {
    const response = await fetch(
      `${config.supabaseUrl}/rest/v1/rpc/get_user_stats`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': config.supabaseAnonKey,
          'Authorization': `Bearer ${config.supabaseAnonKey}`,
        },
        body: JSON.stringify({ p_user_id: userId }),
      }
    );

    if (response.ok) {
      const data = await response.json();
      return {
        total: data[0]?.total_submissions ?? 0,
        accepted: data[0]?.accepted_count ?? 0,
        failed: data[0]?.failed_count ?? 0,
      };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Sync all unsynced local submissions to Supabase
 */
export async function syncPendingSubmissions(config: Config): Promise<number> {
  console.log('[LeetLoop] syncPendingSubmissions called');

  const client = await getSupabaseClient();
  if (!client && (!config.supabaseUrl || !config.supabaseAnonKey)) {
    console.log('[LeetLoop] Supabase not configured for pending sync');
    return 0;
  }

  const result = await chrome.storage.local.get('submissions');
  const submissions: StoredSubmission[] = result.submissions ?? [];
  const unsynced = submissions.filter((s) => !s.synced);

  console.log('[LeetLoop] Found submissions:', submissions.length, 'unsynced:', unsynced.length);

  if (unsynced.length === 0) {
    console.log('[LeetLoop] No unsynced submissions to process');
    return 0;
  }

  let syncedCount = 0;

  for (const [i, submission] of unsynced.entries()) {
    console.log(`[LeetLoop] Processing submission ${i + 1}/${unsynced.length}:`, submission.problem_slug);
    try {
      const success = await syncSubmission(config, submission);
      console.log(`[LeetLoop] Sync result for ${submission.problem_slug}:`, success);
      if (success) {
        submission.synced = true;
        syncedCount++;
      }
    } catch (err) {
      console.error(`[LeetLoop] Sync threw error for ${submission.problem_slug}:`, err);
    }
  }

  if (syncedCount > 0) {
    await chrome.storage.local.set({ submissions });
  }

  return syncedCount;
}
