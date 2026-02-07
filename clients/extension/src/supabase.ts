/**
 * Sync operations for the extension
 * All operations route through the FastAPI backend
 */

import type { Config } from './config';
import { loadConfig } from './config';
import type { StoredSubmission } from './types';
import { apiRequest } from './lib/api-client';
import { getAuthUser } from './lib/auth-store';

/**
 * Get the effective user ID for submissions
 */
async function getEffectiveUserId(): Promise<string> {
  // Check auth first
  const user = await getAuthUser();
  if (user?.id) {
    return user.id;
  }

  // Fall back to guest ID
  const config = await loadConfig();
  return config.guestUserId;
}

/**
 * Sync a submission through the API
 */
export async function syncSubmission(
  _config: Config,
  submission: StoredSubmission
): Promise<boolean> {
  console.log('[LeetLoop] syncSubmission starting for:', submission.problem_slug);

  const userId = await getEffectiveUserId();
  console.log('[LeetLoop] Attempting sync with userId:', userId);

  try {
    const response = await apiRequest('/api/submissions', {
      method: 'POST',
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
 * Get user statistics from the API
 */
export async function getUserStats(_config: Config): Promise<{
  total: number;
  accepted: number;
  failed: number;
} | null> {
  try {
    const user = await getAuthUser();

    let response: Response;
    if (user?.id) {
      // Authenticated: use /me/stats
      response = await apiRequest('/api/progress/me/stats');
    } else {
      // Guest: use /{guestId}/stats
      const config = await loadConfig();
      response = await apiRequest(`/api/progress/${config.guestUserId}/stats`);
    }

    if (!response.ok) {
      console.error('[LeetLoop] Stats fetch failed:', response.status);
      return null;
    }

    const data = await response.json();
    return {
      total: data.total_submissions ?? 0,
      accepted: data.accepted_count ?? 0,
      failed: data.failed_count ?? 0,
    };
  } catch (error) {
    console.error('[LeetLoop] Stats error:', error);
    return null;
  }
}

/**
 * Sync all unsynced local submissions
 */
export async function syncPendingSubmissions(config: Config): Promise<number> {
  console.log('[LeetLoop] syncPendingSubmissions called');

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
