/**
 * Guest to Auth Migration Module
 * Handles migrating data from guest UUID to authenticated user
 */

import { getSession } from './auth';
import { apiRequest } from './lib/api-client';

interface MigrationResult {
  success: boolean;
  migrated?: {
    submissions: number;
    skill_scores: number;
    review_queue: number;
    user_settings: number;
    submission_notes: number;
  };
  error?: string;
}

/**
 * Check if migration is needed and perform it
 * Called when user signs in for the first time
 */
export async function checkAndMigrateGuestData(): Promise<MigrationResult> {
  const session = await getSession();
  if (!session?.user?.id) {
    console.log('[LeetLoop] No authenticated user, cannot migrate');
    return { success: false, error: 'No authenticated user' };
  }

  const authUserId = session.user.id;

  // Get guest user ID from storage
  const result = await chrome.storage.local.get(['guestUserId', 'migrationComplete']);

  // Skip if already migrated
  if (result.migrationComplete) {
    console.log('[LeetLoop] Migration already marked complete, skipping');
    console.log('[LeetLoop] To retry: chrome.storage.local.remove(["migrationComplete"])');
    return { success: true, migrated: { submissions: 0, skill_scores: 0, review_queue: 0, user_settings: 0, submission_notes: 0 } };
  }

  const guestUserId = result.guestUserId;
  if (!guestUserId) {
    console.log('[LeetLoop] No guest user ID found, nothing to migrate');
    await chrome.storage.local.set({ migrationComplete: true });
    return { success: true, migrated: { submissions: 0, skill_scores: 0, review_queue: 0, user_settings: 0, submission_notes: 0 } };
  }

  // Don't migrate if guest ID is same as auth ID
  if (guestUserId === authUserId) {
    console.log('[LeetLoop] Guest ID matches auth ID, no migration needed');
    await chrome.storage.local.set({ migrationComplete: true });
    return { success: true, migrated: { submissions: 0, skill_scores: 0, review_queue: 0, user_settings: 0, submission_notes: 0 } };
  }

  // Perform migration via API
  console.log('[LeetLoop] Starting migration...');
  console.log('[LeetLoop] Guest UUID:', guestUserId);
  console.log('[LeetLoop] Auth User ID:', authUserId);

  try {
    const response = await apiRequest('/api/auth/migrate', {
      method: 'POST',
      body: JSON.stringify({ guest_id: guestUserId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[LeetLoop] Migration API error:', response.status, errorText);
      console.error('[LeetLoop] Migration NOT marked complete due to error');
      console.error('[LeetLoop] Guest UUID for manual migration:', guestUserId);
      console.error('[LeetLoop] Auth User ID for manual migration:', authUserId);
      return { success: false, error: `API error: ${response.status} ${errorText}` };
    }

    const data = await response.json();

    if (!data || typeof data !== 'object') {
      console.error('[LeetLoop] Migration returned unexpected data:', data);
      console.error('[LeetLoop] Migration NOT marked complete due to unexpected response');
      return { success: false, error: 'Unexpected response from migration API' };
    }

    if (data.success !== true) {
      console.error('[LeetLoop] Migration returned success=false:', data);
      console.error('[LeetLoop] Migration NOT marked complete');
      return { success: false, error: data.error || 'Migration failed' };
    }

    console.log('[LeetLoop] Migration successful!');
    console.log('[LeetLoop] Migrated counts:', data.migrated);

    // Mark migration as complete ONLY after confirmed success
    await chrome.storage.local.set({ migrationComplete: true });

    // Update guest ID to auth ID for future operations
    await chrome.storage.local.set({ guestUserId: authUserId });
    console.log('[LeetLoop] Updated stored user ID to auth ID');

    // Mark local submissions for re-sync with new user ID
    await updateLocalSubmissionsForResync();

    return data as MigrationResult;
  } catch (error) {
    console.error('[LeetLoop] Migration exception:', error);
    console.error('[LeetLoop] Migration NOT marked complete due to exception');
    console.error('[LeetLoop] Guest UUID for manual migration:', guestUserId);
    console.error('[LeetLoop] Auth User ID for manual migration:', authUserId);
    return { success: false, error: (error as Error).message };
  }
}

/**
 * Update local cached submissions to mark them for re-sync
 * After migration, they need to be re-synced with the correct user_id
 */
async function updateLocalSubmissionsForResync(): Promise<void> {
  const result = await chrome.storage.local.get('submissions');
  const submissions = result.submissions ?? [];

  if (submissions.length > 0) {
    for (const submission of submissions) {
      submission.synced = false;
    }
    await chrome.storage.local.set({ submissions });
    console.log('[LeetLoop] Marked', submissions.length, 'local submissions for re-sync');
  }
}

/**
 * Reset migration state (for testing/debugging)
 */
export async function resetMigration(): Promise<void> {
  await chrome.storage.local.remove(['migrationComplete']);
  console.log('[LeetLoop] Migration state reset');
}
