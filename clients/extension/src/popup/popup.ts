/**
 * Popup UI script
 */

import type { StoredSubmission } from '../types';

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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  updateUI();

  const toggle = document.getElementById('enabled-toggle');
  toggle?.addEventListener('change', handleToggle);
});
