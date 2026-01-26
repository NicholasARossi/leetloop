/**
 * Submission status returned by LeetCode
 */
export type SubmissionStatus =
  | 'Accepted'
  | 'Wrong Answer'
  | 'Time Limit Exceeded'
  | 'Memory Limit Exceeded'
  | 'Runtime Error'
  | 'Compile Error';

/**
 * Problem difficulty levels
 */
export type Difficulty = 'Easy' | 'Medium' | 'Hard';

/**
 * Payload sent from interceptor to content script via postMessage
 */
export interface InterceptorPayload {
  submissionId: string;
  status: SubmissionStatus;
  statusCode: number;
  runtime?: string;
  memory?: string;
  runtimePercentile?: number;
  memoryPercentile?: number;
  code: string;
  language: string;
  problemSlug: string;
  timestamp: string;
}

/**
 * Message sent from interceptor via postMessage
 */
export interface InterceptorMessage {
  type: 'LEETLOOP_SUBMISSION';
  payload: InterceptorPayload;
}

/**
 * Message sent from content script to background service worker
 */
export type BackgroundMessage =
  | { type: 'SUBMISSION_CAPTURED'; payload: SubmissionPayload }
  | { type: 'SYNC_PENDING' }
  | { type: 'GET_CONFIG' }
  | { type: 'CHECK_MIGRATION' }
  | { type: 'WEB_SESSION_SYNC'; payload: { access_token: string; refresh_token: string } }
  | { type: 'WEB_SIGNED_OUT' };

/**
 * Full submission payload sent to background/Supabase
 */
export interface SubmissionPayload {
  problem_slug: string;
  problem_title: string;
  problem_id?: number;
  difficulty?: Difficulty;
  tags?: string[];
  status: SubmissionStatus;
  runtime_ms?: number;
  runtime_percentile?: number;
  memory_mb?: number;
  memory_percentile?: number;
  attempt_number: number;
  time_elapsed_seconds: number;
  language: string;
  code: string;
  code_length: number;
  session_id: string;
  submitted_at: string;
}

/**
 * Stored submission in chrome.storage
 */
export interface StoredSubmission extends SubmissionPayload {
  id: string;
  synced: boolean;
}

/**
 * Session tracking
 */
export interface Session {
  id: string;
  problemSlug: string;
  startedAt: number;
  attemptCount: number;
}

/**
 * LeetCode GraphQL submission response structure
 */
export interface LeetCodeSubmissionResponse {
  data?: {
    submissionDetails?: {
      statusCode: number;
      runtime?: string;
      runtimePercentile?: number;
      memory?: string;
      memoryPercentile?: number;
      code?: string;
      lang?: {
        name: string;
      };
    };
  };
}

/**
 * LeetCode submit response (initial submission)
 */
export interface LeetCodeSubmitResponse {
  submission_id?: number;
}

/**
 * LeetCode check response (polling for result)
 */
export interface LeetCodeCheckResponse {
  state: string;
  status_code?: number;
  status_msg?: string;
  status_runtime?: string;
  status_memory?: string;
  runtime_percentile?: number;
  memory_percentile?: number;
  code_output?: string;
  expected_output?: string;
  total_correct?: number;
  total_testcases?: number;
}
