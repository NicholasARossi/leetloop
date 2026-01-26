/**
 * Content script - Runs in isolated world
 *
 * Coordinates between the interceptor (MAIN world) and background service worker.
 * Also extracts problem metadata from the page DOM.
 */

import type { InterceptorMessage, SubmissionPayload, Session, Difficulty } from './types';

/**
 * Check if the extension context is still valid
 * This can become invalid when the extension is reloaded/updated
 */
function isExtensionContextValid(): boolean {
  try {
    return !!chrome.runtime?.id;
  } catch {
    return false;
  }
}

// Session tracking
let currentSession: Session | null = null;

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
 * Get or create a session for the current problem
 */
function getSession(problemSlug: string): Session {
  if (!currentSession || currentSession.problemSlug !== problemSlug) {
    currentSession = {
      id: generateUUID(),
      problemSlug,
      startedAt: Date.now(),
      attemptCount: 0,
    };
  }
  currentSession.attemptCount++;
  return currentSession;
}

/**
 * Extract problem metadata from the page DOM
 */
function extractProblemMetadata(): {
  title: string;
  difficulty?: Difficulty;
  tags?: string[];
} {
  // Try to get title from the page
  const titleElement = document.querySelector('[data-cy="question-title"]') ||
    document.querySelector('div[class*="text-title"]') ||
    document.querySelector('h4[class*="title"]');

  const title = titleElement?.textContent?.trim() ?? '';

  // Try to get difficulty
  let difficulty: Difficulty | undefined;
  const difficultyElement = document.querySelector('[diff]') ||
    document.querySelector('div[class*="difficulty"]');

  if (difficultyElement) {
    const text = difficultyElement.textContent?.toLowerCase() ?? '';
    if (text.includes('easy')) difficulty = 'Easy';
    else if (text.includes('medium')) difficulty = 'Medium';
    else if (text.includes('hard')) difficulty = 'Hard';
  }

  // Try to get tags
  const tagElements = document.querySelectorAll('a[href*="/tag/"]');
  const tags = Array.from(tagElements)
    .map((el) => el.textContent?.trim())
    .filter((t): t is string => !!t);

  return { title, difficulty, tags };
}

/**
 * Parse runtime string to milliseconds
 */
function parseRuntime(runtime?: string): number | undefined {
  if (!runtime) return undefined;
  const match = runtime.match(/(\d+)/);
  return match?.[1] ? parseInt(match[1], 10) : undefined;
}

/**
 * Parse memory string to MB
 */
function parseMemory(memory?: string): number | undefined {
  if (!memory) return undefined;
  const match = memory.match(/([\d.]+)/);
  return match?.[1] ? parseFloat(match[1]) : undefined;
}

/**
 * Handle submission message from interceptor
 */
function handleSubmission(message: InterceptorMessage) {
  const { payload } = message;
  const session = getSession(payload.problemSlug);
  const metadata = extractProblemMetadata();

  const submissionPayload: SubmissionPayload = {
    problem_slug: payload.problemSlug,
    problem_title: metadata.title || payload.problemSlug,
    difficulty: metadata.difficulty,
    tags: metadata.tags,
    status: payload.status,
    runtime_ms: parseRuntime(payload.runtime),
    runtime_percentile: payload.runtimePercentile,
    memory_mb: parseMemory(payload.memory),
    memory_percentile: payload.memoryPercentile,
    attempt_number: session.attemptCount,
    time_elapsed_seconds: Math.floor((Date.now() - session.startedAt) / 1000),
    language: payload.language,
    code: payload.code,
    code_length: payload.code.length,
    session_id: session.id,
    submitted_at: payload.timestamp,
  };

  // Send to background service worker
  if (!isExtensionContextValid()) {
    console.log('[LeetLoop] Extension context invalid, cannot forward submission');
    return;
  }

  try {
    chrome.runtime.sendMessage({
      type: 'SUBMISSION_CAPTURED',
      payload: submissionPayload,
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[LeetLoop] Failed to forward submission:', chrome.runtime.lastError.message);
      } else if (response?.success) {
        console.log('[LeetLoop] Submission forwarded successfully:', submissionPayload.status);
      }
    });
  } catch (error) {
    console.error('[LeetLoop] Error forwarding submission:', error);
  }
}

/**
 * Listen for messages from the interceptor (MAIN world)
 */
window.addEventListener('message', (event) => {
  if (event.source !== window) return;
  if (event.data?.type === 'LEETLOOP_SUBMISSION') {
    handleSubmission(event.data as InterceptorMessage);
  }
});

console.log('[LeetLoop] Content script loaded');
