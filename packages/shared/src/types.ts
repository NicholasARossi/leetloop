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
 * A submission event captured from LeetCode
 */
export interface SubmissionEvent {
  // Identity
  id: string;
  user_id: string;

  // Problem metadata
  problem_slug: string;
  problem_title: string;
  problem_id: number;
  difficulty: Difficulty;
  tags: string[];

  // Submission result
  status: SubmissionStatus;
  runtime_ms?: number;
  runtime_percentile?: number;
  memory_mb?: number;
  memory_percentile?: number;

  // Learning signals
  attempt_number: number;
  time_elapsed_seconds: number;
  language: string;
  code: string;
  code_length: number;

  // Context
  submitted_at: string;
  session_id: string;
}

/**
 * Payload sent from interceptor to content script via postMessage
 */
export interface InterceptorMessage {
  type: 'LEETLOOP_SUBMISSION';
  payload: {
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
  };
}

/**
 * Message sent from content script to background service worker
 */
export interface BackgroundMessage {
  type: 'SUBMISSION_CAPTURED';
  payload: Partial<SubmissionEvent>;
}

/**
 * Skill score tracking for a specific tag/topic
 */
export interface SkillScore {
  user_id: string;
  tag: string;
  score: number;
  total_attempts: number;
  success_rate: number;
  avg_time_seconds?: number;
  last_practiced?: string;
}

/**
 * Review queue item for spaced repetition
 */
export interface ReviewQueueItem {
  id: string;
  user_id: string;
  problem_slug: string;
  reason: string;
  next_review: string;
  interval_days: number;
  created_at: string;
}

/**
 * Session tracking for grouping attempts
 */
export interface Session {
  id: string;
  problem_slug: string;
  started_at: string;
  attempt_count: number;
}

/**
 * Extension popup state
 */
export interface PopupState {
  isEnabled: boolean;
  recentSubmissions: SubmissionEvent[];
  todayStats: {
    total: number;
    accepted: number;
    failed: number;
  };
}
