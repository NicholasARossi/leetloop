/**
 * Popup UI script
 */

import type { StoredSubmission } from '../types';
import { signInWithGoogle, signOut, getCurrentUser, onAuthStateChange } from '../auth';
import type { User } from '@supabase/supabase-js';

/**
 * Format relative time
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

/**
 * Render submission list item
 */
function renderSubmissionItem(submission: StoredSubmission): HTMLElement {
  const li = document.createElement('li');
  li.className = 'submission-item';

  const isAccepted = submission.status === 'Accepted';

  li.innerHTML = `
    <span class="status-dot ${isAccepted ? 'accepted' : 'failed'}"></span>
    <div class="submission-info">
      <div class="submission-problem">${submission.problem_title || submission.problem_slug}</div>
      <div class="submission-meta">${submission.status} · ${formatRelativeTime(new Date(submission.submitted_at))}</div>
    </div>
  `;

  return li;
}

/**
 * Update auth UI based on user state
 */
function updateAuthUI(user: User | null, loading: boolean = false) {
  const loadingEl = document.getElementById('auth-loading');
  const signedOutEl = document.getElementById('auth-signed-out');
  const signedInEl = document.getElementById('auth-signed-in');
  const userEmailEl = document.getElementById('user-email');

  if (loading) {
    loadingEl!.style.display = 'block';
    signedOutEl!.style.display = 'none';
    signedInEl!.style.display = 'none';
    return;
  }

  loadingEl!.style.display = 'none';

  if (user) {
    signedOutEl!.style.display = 'none';
    signedInEl!.style.display = 'flex';
    userEmailEl!.textContent = user.email || 'Signed in';
  } else {
    signedOutEl!.style.display = 'flex';
    signedInEl!.style.display = 'none';
  }
}

/**
 * Handle sign in button click
 * Opens the web app login page in a new tab
 */
async function handleSignIn() {
  const signInBtn = document.getElementById('sign-in-btn') as HTMLButtonElement;
  signInBtn.disabled = true;

  // Remove any existing error or info messages
  const existingError = document.querySelector('.auth-error');
  if (existingError) existingError.remove();
  const existingInfo = document.querySelector('.auth-info');
  if (existingInfo) existingInfo.remove();

  try {
    const { redirected, error } = await signInWithGoogle();

    if (error) {
      throw error;
    }

    if (redirected) {
      // Show message that user should complete sign-in in browser
      const authSection = document.getElementById('auth-section');
      const infoEl = document.createElement('p');
      infoEl.className = 'auth-info';
      infoEl.textContent = 'Complete sign-in in the browser tab that just opened';
      authSection!.appendChild(infoEl);

      // Update button to show waiting state
      signInBtn.innerHTML = `
        <svg class="spinner" viewBox="0 0 24 24" width="18" height="18">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/>
          <path fill="currentColor" d="M12 2a10 10 0 0 1 10 10h-2a8 8 0 0 0-8-8V2z"/>
        </svg>
        Waiting for sign-in...
      `;

      // Re-enable after a delay (user might cancel)
      setTimeout(() => {
        signInBtn.disabled = false;
        signInBtn.innerHTML = `
          <svg class="google-icon" viewBox="0 0 24 24" width="18" height="18">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Sign in with Google
        `;
      }, 30000); // Reset after 30 seconds
    }
  } catch (error) {
    console.error('[LeetLoop] Sign in error:', error);
    // Show error message
    const authSection = document.getElementById('auth-section');
    const errorEl = document.createElement('p');
    errorEl.className = 'auth-error';
    errorEl.textContent = (error as Error).message || 'Sign in failed';
    authSection!.appendChild(errorEl);

    signInBtn.disabled = false;
    signInBtn.innerHTML = `
      <svg class="google-icon" viewBox="0 0 24 24" width="18" height="18">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
      Sign in with Google
    `;
  }
}

/**
 * Handle sign out button click
 */
async function handleSignOut() {
  const signOutBtn = document.getElementById('sign-out-btn') as HTMLButtonElement;
  signOutBtn.disabled = true;
  signOutBtn.textContent = 'Signing out...';

  try {
    const { error } = await signOut();
    if (error) {
      console.error('[LeetLoop] Sign out error:', error);
    }
    updateAuthUI(null);
  } catch (error) {
    console.error('[LeetLoop] Sign out error:', error);
  } finally {
    signOutBtn.disabled = false;
    signOutBtn.textContent = 'Sign out';
  }
}

/**
 * Update UI with current data
 */
async function updateUI() {
  const result = await chrome.storage.local.get(['submissions', 'enabled']);
  const submissions: StoredSubmission[] = result.submissions ?? [];
  const enabled = result.enabled !== false; // Default to true

  // Filter today's submissions
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todaySubmissions = submissions.filter(
    (s) => new Date(s.submitted_at) >= today
  );

  const accepted = todaySubmissions.filter((s) => s.status === 'Accepted').length;
  const failed = todaySubmissions.length - accepted;

  // Update stats
  document.getElementById('today-total')!.textContent = todaySubmissions.length.toString();
  document.getElementById('today-accepted')!.textContent = accepted.toString();
  document.getElementById('today-failed')!.textContent = failed.toString();

  // Update submission list (show last 5)
  const list = document.getElementById('submission-list')!;
  list.innerHTML = '';

  if (submissions.length === 0) {
    list.innerHTML = '<li class="empty-state">No submissions captured yet</li>';
  } else {
    submissions.slice(0, 5).forEach((submission) => {
      list.appendChild(renderSubmissionItem(submission));
    });
  }

  // Update toggle
  const toggle = document.getElementById('enabled-toggle') as HTMLInputElement;
  toggle.checked = enabled;
}

/**
 * Handle toggle change
 */
function handleToggle(event: Event) {
  const target = event.target as HTMLInputElement;
  chrome.storage.local.set({ enabled: target.checked });
}

/**
 * Handle sync button click
 */
async function handleSync() {
  const syncBtn = document.getElementById('sync-btn') as HTMLButtonElement;
  const syncText = document.getElementById('sync-text') as HTMLSpanElement;

  syncBtn.disabled = true;
  syncText.textContent = 'Syncing...';

  try {
    const response = await chrome.runtime.sendMessage({ type: 'SYNC_PENDING' });
    console.log('[LeetLoop Popup] Sync response:', response);

    if (response?.success) {
      syncText.textContent = `Synced ${response.synced || 0}`;
      setTimeout(() => {
        syncText.textContent = 'Sync';
        syncBtn.disabled = false;
      }, 2000);
    } else {
      syncText.textContent = 'Error';
      setTimeout(() => {
        syncText.textContent = 'Sync';
        syncBtn.disabled = false;
      }, 2000);
    }
  } catch (error) {
    console.error('[LeetLoop Popup] Sync error:', error);
    syncText.textContent = 'Error';
    setTimeout(() => {
      syncText.textContent = 'Sync';
      syncBtn.disabled = false;
    }, 2000);
  }
}

/**
 * Initialize auth state
 */
async function initAuth() {
  updateAuthUI(null, true); // Show loading

  try {
    console.log('[LeetLoop Popup] Checking current user...');
    const user = await getCurrentUser();
    console.log('[LeetLoop Popup] Current user:', user?.email || 'null');
    updateAuthUI(user);

    // Listen for auth state changes
    await onAuthStateChange((_event, session) => {
      console.log('[LeetLoop Popup] Auth state changed:', _event, session?.user?.email);
      updateAuthUI(session?.user ?? null);
    });
  } catch (error) {
    console.error('[LeetLoop Popup] Auth init error:', error);
    updateAuthUI(null);
  }
}

/**
 * Set daily accent color
 */
function setDailyAccent() {
  const accentColors = [
    '#FF8888', // Coral
    '#88AAFF', // Blue
    '#88DDAA', // Green
    '#FFAA88', // Peach
    '#AA88FF', // Purple
    '#FF88BB', // Pink
    '#88DDDD', // Teal
    '#DDDD88', // Yellow
  ];

  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000
  );
  const colorIndex = dayOfYear % accentColors.length;
  const accent = accentColors[colorIndex];

  document.documentElement.style.setProperty('--accent', accent);
  document.documentElement.style.setProperty('--accent-light', accent + '30');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setDailyAccent();
  initAuth();
  updateUI();

  const toggle = document.getElementById('enabled-toggle');
  toggle?.addEventListener('change', handleToggle);

  const signInBtn = document.getElementById('sign-in-btn');
  signInBtn?.addEventListener('click', handleSignIn);

  const signOutBtn = document.getElementById('sign-out-btn');
  signOutBtn?.addEventListener('click', handleSignOut);

  const syncBtn = document.getElementById('sync-btn');
  syncBtn?.addEventListener('click', handleSync);
});
