/**
 * Supabase client for the extension
 */

import type { Config } from './config';
import type { StoredSubmission } from './types';

/**
 * Sync a submission to Supabase
 */
export async function syncSubmission(
  config: Config,
  submission: StoredSubmission
): Promise<boolean> {
  console.log('[LeetLoop] Attempting sync with config:', {
    url: config.supabaseUrl,
    hasKey: !!config.supabaseAnonKey,
    userId: config.userId,
  });

  if (!config.supabaseUrl || !config.supabaseAnonKey) {
    console.log('[LeetLoop] Supabase not configured, skipping sync');
    return false;
  }

  try {
    const response = await fetch(`${config.supabaseUrl}/rest/v1/submissions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': config.supabaseAnonKey,
        'Authorization': `Bearer ${config.supabaseAnonKey}`,
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify({
        id: submission.id,
        user_id: config.userId,
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
        body: JSON.stringify({ p_user_id: config.userId }),
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

  if (!config.supabaseUrl || !config.supabaseAnonKey) {
    console.log('[LeetLoop] Supabase not configured for pending sync');
    return 0;
  }

  const result = await chrome.storage.local.get('submissions');
  const submissions: StoredSubmission[] = result.submissions ?? [];
  const unsynced = submissions.filter((s) => !s.synced);

  console.log('[LeetLoop] Found submissions:', submissions.length, 'unsynced:', unsynced.length);

  let syncedCount = 0;

  for (const submission of unsynced) {
    const success = await syncSubmission(config, submission);
    if (success) {
      submission.synced = true;
      syncedCount++;
    }
  }

  if (syncedCount > 0) {
    await chrome.storage.local.set({ submissions });
  }

  return syncedCount;
}
