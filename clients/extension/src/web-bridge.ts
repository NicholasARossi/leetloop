/**
 * Web Bridge Content Script
 *
 * Runs on the LeetLoop web app domain to sync auth state between
 * the web app and Chrome extension. The web app is the source of truth.
 */

const STORAGE_KEYS = {
  SESSION_BRIDGE: 'leetloop_session_bridge',
  GUEST_ID: 'leetloop_user_id',
  MIGRATION_COMPLETE: 'leetloop_migration_complete',
};

const CUSTOM_EVENTS = {
  AUTH_CHANGE: 'leetloop:auth-change',
  SIGNED_OUT: 'leetloop:signed-out',
  GUEST_ID: 'leetloop:guest-id',
};

/**
 * Sync guest UUID from web app localStorage to extension storage
 */
async function syncGuestId(): Promise<void> {
  const guestId = localStorage.getItem(STORAGE_KEYS.GUEST_ID);
  if (guestId) {
    await chrome.storage.local.set({ webGuestUserId: guestId });
    console.log('[LeetLoop Bridge] Synced guest ID from web:', guestId);
  }
}

/**
 * Sync session from web app localStorage to extension
 */
async function syncSession(): Promise<void> {
  const sessionData = localStorage.getItem(STORAGE_KEYS.SESSION_BRIDGE);
  if (!sessionData) {
    return;
  }

  try {
    const session = JSON.parse(sessionData);
    if (session?.access_token && session?.refresh_token) {
      // Send session to background script
      chrome.runtime.sendMessage({
        type: 'WEB_SESSION_SYNC',
        payload: {
          access_token: session.access_token,
          refresh_token: session.refresh_token,
        },
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[LeetLoop Bridge] Failed to sync session:', chrome.runtime.lastError);
        } else if (response?.success) {
          console.log('[LeetLoop Bridge] Session synced successfully');
        }
      });
    }
  } catch (error) {
    console.error('[LeetLoop Bridge] Failed to parse session:', error);
  }
}

/**
 * Handle auth change event from web app
 */
function handleAuthChange(event: CustomEvent<{ access_token: string; refresh_token: string } | null>): void {
  const sessionData = event.detail;

  if (sessionData?.access_token && sessionData?.refresh_token) {
    chrome.runtime.sendMessage({
      type: 'WEB_SESSION_SYNC',
      payload: sessionData,
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[LeetLoop Bridge] Failed to sync session:', chrome.runtime.lastError);
      } else if (response?.success) {
        console.log('[LeetLoop Bridge] Auth change synced');
      }
    });
  }
}

/**
 * Handle signed out event from web app
 */
function handleSignedOut(): void {
  chrome.runtime.sendMessage({
    type: 'WEB_SIGNED_OUT',
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('[LeetLoop Bridge] Failed to notify sign out:', chrome.runtime.lastError);
    } else if (response?.success) {
      console.log('[LeetLoop Bridge] Sign out synced');
    }
  });
}

/**
 * Handle guest ID event from web app
 */
function handleGuestId(event: CustomEvent<string>): void {
  const guestId = event.detail;
  if (guestId) {
    chrome.storage.local.set({ webGuestUserId: guestId }).then(() => {
      console.log('[LeetLoop Bridge] Guest ID synced:', guestId);
    });
  }
}

/**
 * Check migration status and sync to extension
 */
async function syncMigrationStatus(): Promise<void> {
  const migrationComplete = localStorage.getItem(STORAGE_KEYS.MIGRATION_COMPLETE);
  if (migrationComplete === 'true') {
    await chrome.storage.local.set({ webMigrationComplete: true });
  }
}

/**
 * Initialize the web bridge
 */
async function init(): Promise<void> {
  console.log('[LeetLoop Bridge] Initializing web bridge on', window.location.href);

  // Check what's in localStorage
  console.log('[LeetLoop Bridge] Session bridge data:', localStorage.getItem(STORAGE_KEYS.SESSION_BRIDGE));
  console.log('[LeetLoop Bridge] Guest ID:', localStorage.getItem(STORAGE_KEYS.GUEST_ID));

  // Initial sync
  await syncGuestId();
  await syncSession();
  await syncMigrationStatus();

  // Listen for custom events from web app
  window.addEventListener(CUSTOM_EVENTS.AUTH_CHANGE, handleAuthChange as EventListener);
  window.addEventListener(CUSTOM_EVENTS.SIGNED_OUT, handleSignedOut);
  window.addEventListener(CUSTOM_EVENTS.GUEST_ID, handleGuestId as EventListener);

  // Also watch for localStorage changes (backup mechanism)
  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEYS.SESSION_BRIDGE) {
      syncSession();
    } else if (event.key === STORAGE_KEYS.GUEST_ID) {
      syncGuestId();
    } else if (event.key === STORAGE_KEYS.MIGRATION_COMPLETE) {
      syncMigrationStatus();
    }
  });

  console.log('[LeetLoop Bridge] Web bridge initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
