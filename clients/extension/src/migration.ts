/**
 * Guest to Auth Migration Module
 * Handles migrating data from guest UUID to authenticated user
 */

import { getSupabaseClient } from './lib/supabase';
import { getSession } from './auth';

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
    return { success: false, error: 'No authenticated user' };
  }

  const authUserId = session.user.id;

  // Get guest user ID from storage
  const result = await chrome.storage.local.get(['guestUserId', 'migrationComplete']);

  // Skip if already migrated
  if (result.migrationComplete) {
    console.log('[LeetLoop] Migration already completed');
    return { success: true, migrated: { submissions: 0, skill_scores: 0, review_queue: 0, user_settings: 0, submission_notes: 0 } };
  }

  const guestUserId = result.guestUserId;
  if (!guestUserId) {
    console.log('[LeetLoop] No guest data to migrate');
    await chrome.storage.local.set({ migrationComplete: true });
    return { success: true, migrated: { submissions: 0, skill_scores: 0, review_queue: 0, user_settings: 0, submission_notes: 0 } };
  }

  // Don't migrate if guest ID is same as auth ID (shouldn't happen, but safety check)
  if (guestUserId === authUserId) {
    console.log('[LeetLoop] Guest ID matches auth ID, skipping migration');
    await chrome.storage.local.set({ migrationComplete: true });
    return { success: true, migrated: { submissions: 0, skill_scores: 0, review_queue: 0, user_settings: 0, submission_notes: 0 } };
  }

  // Perform migration
  console.log('[LeetLoop] Migrating guest data from', guestUserId, 'to', authUserId);

  try {
    const client = await getSupabaseClient();
    if (!client) {
      return { success: false, error: 'Supabase client not available' };
    }

    const { data, error } = await client.rpc('migrate_guest_to_auth', {
      p_guest_id: guestUserId,
      p_auth_id: authUserId,
    });

    if (error) {
      console.error('[LeetLoop] Migration error:', error);
      return { success: false, error: error.message };
    }

    console.log('[LeetLoop] Migration complete:', data);

    // Mark migration as complete
    await chrome.storage.local.set({ migrationComplete: true });

    // Mark local submissions for re-sync with new user ID
    await updateLocalSubmissionsForResync();

    return data as MigrationResult;
  } catch (error) {
    console.error('[LeetLoop] Migration exception:', error);
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
    // Clear sync status so they get re-synced with the correct user_id
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
