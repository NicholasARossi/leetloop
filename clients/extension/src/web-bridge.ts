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
 * Check if the extension context is still valid
 * This can become invalid when the extension is reloaded/updated
 */
function isExtensionContextValid(): boolean {
  try {
    // Accessing chrome.runtime.id will throw if context is invalidated
    return !!chrome.runtime?.id;
  } catch {
    return false;
  }
}

/**
 * Safely send a message to the background script
 * Handles the case where the extension has been reloaded
 */
function safeSendMessage(
  message: unknown,
  callback?: (response: unknown) => void
): void {
  if (!isExtensionContextValid()) {
    console.log('[LeetLoop Bridge] Extension context invalidated, skipping message');
    return;
  }

  try {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        // Extension may have been reloaded - this is expected
        console.log('[LeetLoop Bridge] Message failed (extension may have reloaded):',
          chrome.runtime.lastError.message);
      } else if (callback) {
        callback(response);
      }
    });
  } catch (error) {
    // Extension context was invalidated during the call
    console.log('[LeetLoop Bridge] Could not send message:', error);
  }
}

/**
 * Sync guest UUID from web app localStorage to extension storage
 */
async function syncGuestId(): Promise<void> {
  if (!isExtensionContextValid()) return;

  const guestId = localStorage.getItem(STORAGE_KEYS.GUEST_ID);
  if (guestId) {
    try {
      await chrome.storage.local.set({ webGuestUserId: guestId });
      console.log('[LeetLoop Bridge] Synced guest ID from web:', guestId);
    } catch (error) {
      console.log('[LeetLoop Bridge] Could not sync guest ID:', error);
    }
  }
}

/**
 * Sync session from web app localStorage to extension
 */
async function syncSession(): Promise<void> {
  if (!isExtensionContextValid()) return;

  const sessionData = localStorage.getItem(STORAGE_KEYS.SESSION_BRIDGE);
  if (!sessionData) {
    return;
  }

  try {
    const session = JSON.parse(sessionData);
    if (session?.access_token && session?.refresh_token) {
      // Send session to background script
      safeSendMessage({
        type: 'WEB_SESSION_SYNC',
        payload: {
          access_token: session.access_token,
          refresh_token: session.refresh_token,
        },
      }, (response: unknown) => {
        const resp = response as { success?: boolean } | undefined;
        if (resp?.success) {
          console.log('[LeetLoop Bridge] Session synced successfully');
        }
      });
    }
  } catch (error) {
    console.log('[LeetLoop Bridge] Failed to parse session:', error);
  }
}

/**
 * Handle auth change event from web app
 */
function handleAuthChange(event: CustomEvent<{ access_token: string; refresh_token: string } | null>): void {
  if (!isExtensionContextValid()) return;

  const sessionData = event.detail;

  if (sessionData?.access_token && sessionData?.refresh_token) {
    safeSendMessage({
      type: 'WEB_SESSION_SYNC',
      payload: sessionData,
    }, (response: unknown) => {
      const resp = response as { success?: boolean } | undefined;
      if (resp?.success) {
        console.log('[LeetLoop Bridge] Auth change synced');
      }
    });
  }
}

/**
 * Handle signed out event from web app
 */
function handleSignedOut(): void {
  if (!isExtensionContextValid()) return;

  safeSendMessage({
    type: 'WEB_SIGNED_OUT',
  }, (response: unknown) => {
    const resp = response as { success?: boolean } | undefined;
    if (resp?.success) {
      console.log('[LeetLoop Bridge] Sign out synced');
    }
  });
}

/**
 * Handle guest ID event from web app
 */
function handleGuestId(event: CustomEvent<string>): void {
  if (!isExtensionContextValid()) return;

  const guestId = event.detail;
  if (guestId) {
    chrome.storage.local.set({ webGuestUserId: guestId })
      .then(() => {
        console.log('[LeetLoop Bridge] Guest ID synced:', guestId);
      })
      .catch((error) => {
        console.log('[LeetLoop Bridge] Could not sync guest ID:', error);
      });
  }
}

/**
 * Check migration status and sync to extension
 */
async function syncMigrationStatus(): Promise<void> {
  if (!isExtensionContextValid()) return;

  const migrationComplete = localStorage.getItem(STORAGE_KEYS.MIGRATION_COMPLETE);
  if (migrationComplete === 'true') {
    try {
      await chrome.storage.local.set({ webMigrationComplete: true });
    } catch (error) {
      console.log('[LeetLoop Bridge] Could not sync migration status:', error);
    }
  }
}

/**
 * Initialize the web bridge
 */
async function init(): Promise<void> {
  // Check if extension context is still valid before initializing
  if (!isExtensionContextValid()) {
    console.log('[LeetLoop Bridge] Extension context invalid, skipping initialization');
    return;
  }

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
    // Check context validity on each storage event
    if (!isExtensionContextValid()) return;

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
  document.addEventListener('DOMContentLoaded', () => {
    init().catch((error) => {
      console.log('[LeetLoop Bridge] Initialization failed:', error);
    });
  });
} else {
  init().catch((error) => {
    console.log('[LeetLoop Bridge] Initialization failed:', error);
  });
}
