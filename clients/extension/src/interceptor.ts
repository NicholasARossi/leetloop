/**
 * Interceptor script - Runs in MAIN world to intercept page-level fetch calls
 *
 * This script overrides window.fetch to capture LeetCode submission responses.
 * It watches for GraphQL queries and submission check endpoints.
 */

import type { LeetCodeCheckResponse, SubmissionStatus } from './types';

// Store the original fetch
const originalFetch = window.fetch;

// Track pending submissions for correlation
const pendingSubmissions = new Map<string, { code: string; language: string }>();

// Status code to status message mapping
const STATUS_MAP: Record<number, SubmissionStatus> = {
  10: 'Accepted',
  11: 'Wrong Answer',
  12: 'Memory Limit Exceeded',
  13: 'Output Limit Exceeded' as SubmissionStatus,
  14: 'Time Limit Exceeded',
  15: 'Runtime Error',
  16: 'Internal Error' as SubmissionStatus,
  20: 'Compile Error',
};

/**
 * Extract problem slug from current URL
 */
function getProblemSlug(): string {
  const match = window.location.pathname.match(/\/problems\/([^/]+)/);
  return match?.[1] ?? '';
}

/**
 * Parse submission response and send to content script
 */
function handleSubmissionResult(
  submissionId: string,
  result: LeetCodeCheckResponse,
  submissionData?: { code: string; language: string }
) {
  if (result.state !== 'SUCCESS') {
    return; // Still pending
  }

  const statusCode = result.status_code ?? 0;
  const status = STATUS_MAP[statusCode] ?? ('Unknown' as SubmissionStatus);

  const payload = {
    submissionId,
    status,
    statusCode,
    runtime: result.status_runtime,
    memory: result.status_memory,
    runtimePercentile: result.runtime_percentile,
    memoryPercentile: result.memory_percentile,
    code: submissionData?.code ?? '',
    language: submissionData?.language ?? '',
    problemSlug: getProblemSlug(),
    timestamp: new Date().toISOString(),
  };

  // Send to content script via postMessage
  window.postMessage({ type: 'LEETLOOP_SUBMISSION', payload }, '*');

  console.log('[LeetLoop] Submission captured:', status, submissionId);
}

/**
 * Intercept fetch and watch for LeetCode submission endpoints
 */
window.fetch = async function (input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;

  // Watch for submission requests
  if (url.includes('/submit')) {
    try {
      const body = init?.body;
      if (body) {
        const parsed = JSON.parse(body.toString());
        // Store submission data for correlation
        if (parsed.typed_code && parsed.lang) {
          const response = await originalFetch.call(window, input, init);
          const cloned = response.clone();
          const result = await cloned.json();
          if (result.submission_id) {
            pendingSubmissions.set(result.submission_id.toString(), {
              code: parsed.typed_code,
              language: parsed.lang,
            });
          }
          return response;
        }
      }
    } catch {
      // Ignore parse errors
    }
  }

  // Watch for submission check responses (polling endpoint)
  const checkMatch = url.match(/\/submissions\/detail\/(\d+)\/check/);
  if (checkMatch?.[1]) {
    const submissionId = checkMatch[1];
    const response = await originalFetch.call(window, input, init);
    const cloned = response.clone();

    try {
      const result: LeetCodeCheckResponse = await cloned.json();
      if (result.state === 'SUCCESS') {
        const submissionData = pendingSubmissions.get(submissionId);
        handleSubmissionResult(submissionId, result, submissionData);
        pendingSubmissions.delete(submissionId);
      }
    } catch {
      // Ignore parse errors
    }

    return response;
  }

  // Watch for GraphQL submission details query
  if (url.includes('/graphql') && init?.body) {
    try {
      const body = JSON.parse(init.body.toString());
      if (body.operationName === 'submissionDetails') {
        const response = await originalFetch.call(window, input, init);
        const cloned = response.clone();
        const result = await cloned.json();

        if (result.data?.submissionDetails) {
          const details = result.data.submissionDetails;
          const submissionId = body.variables?.submissionId?.toString() ?? '';

          handleSubmissionResult(submissionId, {
            state: 'SUCCESS',
            status_code: details.statusCode,
            status_runtime: details.runtime,
            status_memory: details.memory,
            runtime_percentile: details.runtimePercentile,
            memory_percentile: details.memoryPercentile,
          }, {
            code: details.code ?? '',
            language: details.lang?.name ?? '',
          });
        }

        return response;
      }
    } catch {
      // Ignore parse errors
    }
  }

  // Default: pass through to original fetch
  return originalFetch.call(window, input, init);
};

console.log('[LeetLoop] Interceptor loaded');
