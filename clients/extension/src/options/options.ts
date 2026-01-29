/**
 * Options page script
 */

import { loadConfig, saveConfig } from '../config';

/**
 * Show status message
 */
function showStatus(message: string, type: 'success' | 'error') {
  const status = document.getElementById('status')!;
  status.textContent = message;
  status.className = `status ${type}`;

  setTimeout(() => {
    status.className = 'status';
  }, 3000);
}

/**
 * Load current settings into form
 */
async function loadSettings() {
  const config = await loadConfig();

  (document.getElementById('api-url') as HTMLInputElement).value =
    config.apiUrl || '';
  (document.getElementById('user-id') as HTMLInputElement).value =
    config.userId || '';
}

/**
 * Save settings from form
 */
async function saveSettings(event: Event) {
  event.preventDefault();

  const apiUrl = (document.getElementById('api-url') as HTMLInputElement).value.trim();

  try {
    await saveConfig({ apiUrl });
    showStatus('Settings saved successfully!', 'success');
  } catch (error) {
    showStatus('Failed to save settings: ' + String(error), 'error');
  }
}

/**
 * Sync pending submissions
 */
async function syncPending() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'SYNC_PENDING' });
    if (response.success) {
      showStatus(`Synced ${response.synced} pending submissions`, 'success');
    } else {
      showStatus('Sync failed: ' + response.error, 'error');
    }
  } catch (error) {
    showStatus('Sync failed: ' + String(error), 'error');
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();

  document.getElementById('settings-form')?.addEventListener('submit', saveSettings);
  document.getElementById('sync-btn')?.addEventListener('click', syncPending);
});
