/**
 * Background service worker
 *
 * Handles storage and Supabase sync for captured submissions.
 */

import type { BackgroundMessage, StoredSubmission, SubmissionPayload } from './types';
import { loadConfig } from './config';
import { syncSubmission, syncPendingSubmissions } from './supabase';
import { checkAndMigrateGuestData } from './migration';
import { onAuthStateChange } from './auth';

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
 * Store submission locally
 */
async function storeSubmission(submission: StoredSubmission): Promise<void> {
  const result = await chrome.storage.local.get('submissions');
  const submissions: StoredSubmission[] = result.submissions ?? [];

  // Check if this submission already exists (by id)
  const existingIndex = submissions.findIndex((s) => s.id === submission.id);
  if (existingIndex >= 0) {
    submissions[existingIndex] = submission;
  } else {
    // Add new submission at the beginning
    submissions.unshift(submission);
    // Keep last 100 submissions locally
    if (submissions.length > 100) {
      submissions.pop();
    }
  }

  await chrome.storage.local.set({ submissions });
}

/**
 * Handle submission capture
 */
async function handleSubmission(payload: SubmissionPayload): Promise<StoredSubmission> {
  const config = await loadConfig();

  const submission: StoredSubmission = {
    id: generateUUID(),
    ...payload,
    synced: false,
  };

  // Store locally first
  await storeSubmission(submission);
  console.log('[LeetLoop] Submission stored:', submission.status, submission.problem_slug);

  // Try to sync to Supabase
  const synced = await syncSubmission(config, submission);
  if (synced) {
    submission.synced = true;
    await storeSubmission(submission);
  }

  return submission;
}

/**
 * Handle incoming messages from content script
 */
chrome.runtime.onMessage.addListener((message: BackgroundMessage, _sender, sendResponse) => {
  if (message.type === 'SUBMISSION_CAPTURED') {
    handleSubmission(message.payload as SubmissionPayload)
      .then((submission) => {
        sendResponse({ success: true, submission });
      })
      .catch((error) => {
        console.error('[LeetLoop] Error handling submission:', error);
        sendResponse({ success: false, error: String(error) });
      });

    return true; // Keep channel open for async response
  }

  if (message.type === 'SYNC_PENDING') {
    loadConfig()
      .then((config) => syncPendingSubmissions(config))
      .then((count) => {
        sendResponse({ success: true, synced: count });
      })
      .catch((error) => {
        sendResponse({ success: false, error: String(error) });
      });

    return true;
  }

  if (message.type === 'GET_CONFIG') {
    loadConfig()
      .then((config) => {
        sendResponse({ success: true, config });
      })
      .catch((error) => {
        sendResponse({ success: false, error: String(error) });
      });

    return true;
  }

  if (message.type === 'CHECK_MIGRATION') {
    checkAndMigrateGuestData()
      .then((result) => {
        sendResponse({ success: true, result });
        // Re-sync pending submissions after migration
        if (result.success) {
          loadConfig().then((config) => syncPendingSubmissions(config));
        }
      })
      .catch((error) => {
        sendResponse({ success: false, error: String(error) });
      });

    return true;
  }
});

/**
 * Handle extension installation
 */
chrome.runtime.onInstalled.addListener(async () => {
  console.log('[LeetLoop] Extension installed');

  // Initialize config
  await loadConfig();

  // Set up auth state listener
  setupAuthListener();
});

/**
 * Set up auth state change listener for automatic migration
 */
async function setupAuthListener() {
  try {
    await onAuthStateChange(async (event, session) => {
      console.log('[LeetLoop] Auth state changed:', event);

      if (event === 'SIGNED_IN' && session?.user) {
        // User just signed in, check for migration
        console.log('[LeetLoop] User signed in, checking migration');
        const result = await checkAndMigrateGuestData();
        console.log('[LeetLoop] Migration result:', result);

        if (result.success) {
          // Re-sync any pending submissions
          const config = await loadConfig();
          await syncPendingSubmissions(config);
        }
      }
    });
  } catch (error) {
    console.error('[LeetLoop] Failed to set up auth listener:', error);
  }
}

/**
 * Periodically sync pending submissions
 */
chrome.alarms.create('sync-pending', { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'sync-pending') {
    const config = await loadConfig();
    const count = await syncPendingSubmissions(config);
    if (count > 0) {
      console.log(`[LeetLoop] Synced ${count} pending submissions`);
    }
  }
});

console.log('[LeetLoop] Background service worker started');
