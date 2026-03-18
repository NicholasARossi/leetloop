/**
 * API client for backend communication
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

interface FetchOptions extends RequestInit {
  timeout?: number
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchWithTimeout(
  url: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options

  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    })
    return response
  } finally {
    clearTimeout(id)
  }
}

async function api<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`

  const response = await fetchWithTimeout(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new ApiError(response.status, error.detail || response.statusText)
  }

  return response.json()
}

// API methods
export const leetloopApi = {
  // Health
  health: () => api<{ status: string }>('/health'),

  // Progress
  getProgress: (userId: string, days?: number) =>
    api<{
      stats: UserStats
      skill_scores: SkillScore[]
      trends: ProgressTrend[]
      recent_submissions: Submission[]
    }>(`/api/progress/${userId}${days ? `?days=${days}` : ''}`),

  getStats: (userId: string) =>
    api<UserStats>(`/api/progress/${userId}/stats`),

  getSkillScores: (userId: string) =>
    api<SkillScore[]>(`/api/progress/${userId}/skills`),

  getSubmissions: (
    userId: string,
    params?: {
      limit?: number
      offset?: number
      status?: string
      difficulty?: string
      tag?: string
    }
  ) => {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.offset) searchParams.set('offset', params.offset.toString())
    if (params?.status) searchParams.set('status', params.status)
    if (params?.difficulty) searchParams.set('difficulty', params.difficulty)
    if (params?.tag) searchParams.set('tag', params.tag)

    const query = searchParams.toString()
    return api<Submission[]>(`/api/submissions/${userId}${query ? `?${query}` : ''}`)
  },

  // Recommendations
  getRecommendations: (userId: string, limit = 5) =>
    api<{
      user_id: string
      recommendations: RecommendedProblem[]
      weak_areas: string[]
      generated_at: string
    }>(`/api/recommendations/${userId}?limit=${limit}`),

  getNextProblem: (userId: string) =>
    api<RecommendedProblem>(`/api/recommendations/${userId}/next`),

  // Reviews
  getReviews: (userId: string, limit = 10) =>
    api<ReviewItem[]>(`/api/reviews/${userId}?limit=${limit}`),

  getReviewCount: (userId: string) =>
    api<{ count: number }>(`/api/reviews/${userId}/count`),

  completeReview: (reviewId: string, success: boolean) =>
    api<{ id: string; next_review: string; new_interval_days: number }>(
      `/api/reviews/${reviewId}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ success }),
      }
    ),

  // Coaching
  chat: (
    userId: string,
    message: string,
    context?: Record<string, unknown>,
    history: ChatMessage[] = []
  ) =>
    api<{ message: string; suggestions: string[] }>('/api/coaching/chat', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, message, context, history }),
    }),

  analyzeCode: (
    userId: string,
    submissionId: string,
    code: string,
    language: string,
    problemSlug: string,
    status: string,
    errorContext?: {
      code_output?: string
      expected_output?: string
      status_msg?: string
      total_correct?: number
      total_testcases?: number
    }
  ) =>
    api<CodeAnalysis>('/api/coaching/analyze', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        submission_id: submissionId,
        code,
        language,
        problem_slug: problemSlug,
        status,
        ...errorContext,
      }),
    }),

  getTips: (userId: string) =>
    api<{ tips: string[] }>(`/api/coaching/tips/${userId}`),

  getPatterns: (userId: string) =>
    api<UserPatterns>(`/api/patterns/${userId}`),

  // Learning Paths
  getPaths: () =>
    api<LearningPathSummary[]>('/api/paths'),

  getPath: (pathId: string) =>
    api<LearningPath>(`/api/paths/${pathId}`),

  getPathProgress: (pathId: string, userId: string) =>
    api<PathProgressResponse>(`/api/paths/${pathId}/progress/${userId}`),

  completeProblem: (pathId: string, userId: string, problemSlug: string) =>
    api<{ success: boolean; problem_slug: string }>(
      `/api/paths/${pathId}/complete/${userId}`,
      {
        method: 'POST',
        body: JSON.stringify({ problem_slug: problemSlug }),
      }
    ),

  setCurrentPath: (userId: string, pathId: string) =>
    api<{ success: boolean; path_id: string; path_name: string }>(
      `/api/users/${userId}/current-path`,
      {
        method: 'PUT',
        body: JSON.stringify({ path_id: pathId }),
      }
    ),

  getCurrentPath: (userId: string) =>
    api<PathProgressResponse>(`/api/users/${userId}/current-path`),

  // Mastery
  getMastery: (userId: string) =>
    api<MasteryResponse>(`/api/mastery/${userId}`),

  getDomainDetail: (userId: string, domainName: string) =>
    api<DomainDetailResponse>(`/api/mastery/${userId}/${encodeURIComponent(domainName)}`),

  // Mission Control
  getDailyMission: (userId: string) =>
    api<MissionResponse>(`/api/mission/${userId}`),

  regenerateMission: (userId: string) =>
    api<MissionResponseV2>(`/api/mission/${userId}/regenerate`, {
      method: 'POST',
    }),

  // Win Rate
  getWinRateTargets: (userId: string) =>
    api<WinRateTargets>(`/api/winrate/${userId}/targets`),

  setWinRateTargets: (userId: string, request: SetWinRateTargetsRequest) =>
    api<WinRateTargets>(`/api/winrate/${userId}/targets`, {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  getWinRateStats: (userId: string) =>
    api<WinRateStats>(`/api/winrate/${userId}/stats`),

  // Daily Feed (longer timeout for cold start + Gemini generation)
  getDailyFeed: (userId: string) =>
    api<DailyFeedResponse>(`/api/feed/${userId}`, { timeout: 90000 }),

  regenerateFeed: (userId: string) =>
    api<DailyFeedResponse>(`/api/feed/${userId}/regenerate`, {
      method: 'POST',
    }),

  extendFeed: (userId: string) =>
    api<DailyFeedResponse>(`/api/feed/${userId}/extend`, {
      method: 'POST',
    }),

  getFocusNotes: (userId: string) =>
    api<FocusNotesResponse>(`/api/feed/${userId}/notes`),

  updateFocusNotes: (userId: string, focusNotes: string | null) =>
    api<FocusNotesResponse>(`/api/feed/${userId}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ focus_notes: focusNotes }),
    }),

  // Onboarding
  getOnboardingStatus: (userId: string) =>
    api<OnboardingStatus>(`/api/onboarding/${userId}`),

  updateOnboardingStep: (userId: string, step: string, completed: boolean = true, metadata?: Record<string, unknown>) =>
    api<OnboardingStatus>(`/api/onboarding/${userId}/step`, {
      method: 'POST',
      body: JSON.stringify({ step, completed, metadata }),
    }),

  verifyExtension: (userId: string) =>
    api<OnboardingStatus>(`/api/onboarding/${userId}/verify-extension`, {
      method: 'POST',
    }),

  importHistory: (userId: string) =>
    api<{ success: boolean; problems_imported: number; message: string }>(
      `/api/onboarding/${userId}/import-history`,
      { method: 'POST' }
    ),

  completeOnboarding: (userId: string) =>
    api<OnboardingStatus>(`/api/onboarding/${userId}/complete`, {
      method: 'POST',
    }),

  skipOnboardingStep: (userId: string, step: string) =>
    api<OnboardingStatus>(`/api/onboarding/${userId}/skip-step`, {
      method: 'POST',
      body: JSON.stringify({ step, completed: true }),
    }),

  resetOnboarding: (userId: string) =>
    api<OnboardingStatus>(`/api/onboarding/${userId}/reset`, {
      method: 'DELETE',
    }),

  // Mission v2 (with reasoning)
  getDailyMissionV2: (userId: string) =>
    api<MissionResponseV2>(`/api/mission/${userId}`),

  // System Design
  getSystemDesignTracks: () =>
    api<SystemDesignTrackSummary[]>('/api/system-design/tracks'),

  getSystemDesignTrack: (trackId: string) =>
    api<SystemDesignTrack>(`/api/system-design/tracks/${trackId}`),

  getTrackProgress: (trackId: string, userId: string) =>
    api<TrackProgressResponse>(`/api/system-design/tracks/${trackId}/progress/${userId}`),

  getSystemDesignReviews: (userId: string, limit = 10) =>
    api<SystemDesignReviewItem[]>(`/api/system-design/${userId}/reviews?limit=${limit}`),

  completeSystemDesignReview: (reviewId: string, success: boolean) =>
    api<{ id: string; next_review: string; new_interval_days: number }>(
      `/api/system-design/reviews/${reviewId}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ success }),
      }
    ),

  // System Design Dashboard
  getSystemDesignDashboard: (userId: string) =>
    api<SystemDesignDashboardSummary>(`/api/system-design/${userId}/dashboard`),

  setActiveSystemDesignTrack: (userId: string, trackId: string | null) =>
    api<{ success: boolean; active_track_id?: string }>(
      `/api/system-design/${userId}/active-track`,
      {
        method: 'PUT',
        body: JSON.stringify({ track_id: trackId }),
      }
    ),

  getActiveSystemDesignTrack: (userId: string) =>
    api<ActiveTrackResponse>(`/api/system-design/${userId}/active-track`),

  // Oral System Design Sessions
  createOralSession: (userId: string, data: { track_id: string; topic: string }) =>
    api<OralSession>(`/api/system-design/${userId}/oral-session`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getOralSession: (sessionId: string) =>
    api<OralSession>(`/api/system-design/oral-sessions/${sessionId}`),

  submitOralAudio: async (questionId: string, audioFile: Blob | File): Promise<OralGradeResult> => {
    const formData = new FormData()
    formData.append('audio', audioFile, audioFile instanceof File ? audioFile.name : 'recording.webm')

    const url = `${API_URL}/api/system-design/oral-questions/${questionId}/submit-audio`
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      body: formData,
      timeout: 120000, // 2 min timeout for audio processing
      // Do NOT set Content-Type — browser sets it with boundary for FormData
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new ApiError(response.status, error.detail || response.statusText)
    }

    return response.json()
  },

  submitFollowUpAudio: async (questionId: string, followUpIndex: number, audioFile: Blob | File): Promise<FollowUpGradeResult> => {
    const formData = new FormData()
    formData.append('audio', audioFile, audioFile instanceof File ? audioFile.name : 'recording.webm')

    const url = `${API_URL}/api/system-design/oral-questions/${questionId}/follow-ups/${followUpIndex}/submit-audio`
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      body: formData,
      timeout: 120000,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new ApiError(response.status, error.detail || response.statusText)
    }

    return response.json()
  },

  completeOralSession: (sessionId: string) =>
    api<OralSessionSummary>(`/api/system-design/oral-sessions/${sessionId}/complete`, {
      method: 'POST',
    }),

  getOralSessions: (userId: string, limit = 20) =>
    api<OralSession[]>(`/api/system-design/${userId}/oral-sessions?limit=${limit}`),

  // Language Learning
  getLanguageTracks: () =>
    api<LanguageTrackSummary[]>('/api/language/tracks'),

  getLanguageTrack: (trackId: string) =>
    api<LanguageTrack>(`/api/language/tracks/${trackId}`),

  getLanguageTrackProgress: (trackId: string, userId: string) =>
    api<LanguageTrackProgressResponse>(`/api/language/tracks/${trackId}/progress/${userId}`),

  createLanguageAttempt: (userId: string, data: CreateLanguageAttemptRequest) =>
    api<LanguageAttempt>(`/api/language/${userId}/attempt`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  submitLanguageAttempt: (attemptId: string, responseText: string) =>
    api<LanguageAttemptGrade>(`/api/language/attempts/${attemptId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ response_text: responseText }),
    }),

  getLanguageAttempt: (attemptId: string) =>
    api<LanguageAttempt>(`/api/language/attempts/${attemptId}`),

  getLanguageAttemptHistory: (userId: string, limit = 20, offset = 0) =>
    api<LanguageAttemptHistoryResponse>(
      `/api/language/${userId}/attempts?limit=${limit}&offset=${offset}`
    ),

  getLanguageReviews: (userId: string, limit = 10) =>
    api<LanguageReviewItem[]>(`/api/language/${userId}/reviews?limit=${limit}`),

  completeLanguageReview: (reviewId: string, success: boolean) =>
    api<{ id: string; next_review: string; new_interval_days: number }>(
      `/api/language/reviews/${reviewId}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ success }),
      }
    ),

  getLanguageDashboard: (userId: string) =>
    api<LanguageDashboardSummary>(`/api/language/${userId}/dashboard`),

  setActiveLanguageTrack: (userId: string, trackId: string | null) =>
    api<{ success: boolean; active_track_id?: string }>(
      `/api/language/${userId}/active-track`,
      {
        method: 'PUT',
        body: JSON.stringify({ track_id: trackId }),
      }
    ),

  // Daily Exercises
  getDailyExercises: (userId: string) =>
    api<DailyExerciseBatch>(`/api/language/${userId}/daily-exercises`),

  submitDailyExercise: (exerciseId: string, responseText: string) =>
    api<DailyExerciseGrade>(`/api/language/daily-exercises/${exerciseId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ response_text: responseText }),
    }),

  regenerateDailyExercises: (userId: string) =>
    api<DailyExerciseBatch>(`/api/language/${userId}/daily-exercises/regenerate`, {
      method: 'POST',
    }),

  // Book Progress
  getBookProgress: (trackId: string, userId: string) =>
    api<BookProgressResponse>(`/api/language/tracks/${trackId}/book-progress/${userId}`),

  // ML Coding Drills
  getMLCodingProblems: () =>
    api<MLCodingProblem[]>('/api/ml-coding/problems'),

  getMLCodingDailyExercises: (userId: string) =>
    api<MLCodingDailyBatch>(`/api/ml-coding/${userId}/daily-exercises`, { timeout: 90000 }),

  submitMLCodingExercise: (exerciseId: string, submittedCode: string) =>
    api<MLCodingExerciseGrade>(`/api/ml-coding/daily-exercises/${exerciseId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ submitted_code: submittedCode }),
      timeout: 120000,
    }),

  regenerateMLCodingExercises: (userId: string) =>
    api<MLCodingDailyBatch>(`/api/ml-coding/${userId}/daily-exercises/regenerate`, {
      method: 'POST',
      timeout: 90000,
    }),

  getMLCodingReviews: (userId: string, limit = 10) =>
    api<MLCodingReviewItem[]>(`/api/ml-coding/${userId}/reviews?limit=${limit}`),

  completeMLCodingReview: (reviewId: string, success: boolean) =>
    api<{ id: string; next_review: string; new_interval_days: number }>(
      `/api/ml-coding/reviews/${reviewId}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ success }),
      }
    ),

  getMLCodingDashboard: (userId: string) =>
    api<MLCodingDashboardSummary>(`/api/ml-coding/${userId}/dashboard`),
}

// Types (matching backend schemas)
export interface UserStats {
  total_submissions: number
  accepted_count: number
  failed_count: number
  success_rate: number
  problems_solved: number
  problems_attempted: number
  streak_days: number
  reviews_due: number
}

export interface SkillScore {
  user_id: string
  tag: string
  score: number
  total_attempts: number
  success_rate: number
  avg_time_seconds?: number
  last_practiced?: string
}

export interface ProgressTrend {
  date: string
  submissions: number
  accepted: number
  success_rate: number
}

export interface Submission {
  id: string
  user_id: string
  problem_slug: string
  problem_title: string
  problem_id?: number
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  tags?: string[]
  status: string
  runtime_ms?: number
  runtime_percentile?: number
  memory_mb?: number
  memory_percentile?: number
  attempt_number?: number
  time_elapsed_seconds?: number
  language?: string
  code?: string
  code_length?: number
  session_id?: string
  submitted_at: string
  created_at: string
}

export interface RecommendedProblem {
  problem_slug: string
  problem_title?: string
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  tags: string[]
  reason: string
  priority: number
  source: string
}

export interface ReviewItem {
  id: string
  user_id: string
  problem_slug: string
  problem_title?: string
  reason?: string
  priority: number
  next_review: string
  interval_days: number
  review_count: number
  last_reviewed?: string
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface CodeAnalysis {
  summary: string
  issues: string[]
  suggestions: string[]
  time_complexity?: string
  space_complexity?: string
  root_cause?: string
  the_fix?: string
  pattern_type?: string
  concept_gap?: string
}

export interface PatternInsight {
  pattern: string
  frequency: number
  example_problems: string[]
}

export interface UserPatterns {
  recurring_mistakes: PatternInsight[]
  error_distribution: Record<string, number>
  learning_velocity: string
  velocity_details: string
  blind_spots: string[]
  strategic_recommendations: string[]
  analyzed_at: string
}

// Learning Path Types
export interface PathProblem {
  slug: string
  title: string
  difficulty: 'Easy' | 'Medium' | 'Hard'
  order: number
}

export interface PathCategory {
  name: string
  order: number
  problems: PathProblem[]
}

export interface LearningPath {
  id: string
  name: string
  description?: string
  total_problems: number
  categories: PathCategory[]
}

export interface LearningPathSummary {
  id: string
  name: string
  description?: string
  total_problems: number
}

export interface CategoryProgress {
  total: number
  completed: number
  problems: {
    slug: string
    title: string
    difficulty?: string
    completed: boolean
  }[]
}

export interface PathProgressResponse {
  path: LearningPath
  progress?: {
    id: string
    user_id: string
    path_id: string
    completed_problems: string[]
    current_category?: string
    started_at: string
    last_activity_at?: string
  }
  completed_count: number
  completion_percentage: number
  categories_progress: Record<string, CategoryProgress>
}

// Mastery Types
export interface DomainScore {
  name: string
  score: number
  status: 'WEAK' | 'FAIR' | 'GOOD' | 'STRONG'
  problems_attempted: number
  problems_solved: number
  sub_patterns: {
    name: string
    score: number
    attempted: number
  }[]
}

export interface MasteryResponse {
  user_id: string
  readiness_score: number
  readiness_summary: string
  domains: DomainScore[]
  weak_areas: string[]
  strong_areas: string[]
  generated_at: string
}

export interface DomainDetailResponse {
  domain: DomainScore
  failure_analysis?: string
  recommended_path: PathProblem[]
  recent_submissions: Submission[]
}

// Mission Control Types
export type QuestStatus = 'completed' | 'current' | 'upcoming'

export interface MainQuest {
  slug: string
  title: string
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  category: string
  order: number
  status: QuestStatus
}

export interface SideQuest {
  slug: string
  title: string
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  reason: string
  source_problem_slug?: string
  target_weakness: string
  quest_type: 'review_due' | 'skill_gap' | 'slow_solve'
  completed: boolean
}

export interface MissionResponse {
  user_id: string
  mission_date: string
  objective?: { title: string; description: string; skill_tags: string[]; target_count: number; completed_count: number }
  main_quests: MainQuest[]
  side_quests: SideQuest[]
  streak: number
  total_completed_today: number
  can_regenerate: boolean
  generated_at: string
}

// Win Rate Types
export interface WinRateTargets {
  id: string
  user_id: string
  easy_target: number
  medium_target: number
  hard_target: number
  optimality_threshold: number
  created_at?: string
  updated_at?: string
}

export interface SetWinRateTargetsRequest {
  easy_target?: number
  medium_target?: number
  hard_target?: number
  optimality_threshold?: number
}

export interface DifficultyWinRate {
  rate: number
  attempts: number
  optimal: number
  target: number
}

export interface WinRateStats {
  targets: WinRateTargets | null
  current_30d: Record<string, DifficultyWinRate>
  current_alltime: Record<string, DifficultyWinRate>
  trend: { date: string; easy_rate: number; medium_rate: number; hard_rate: number }[]
}

export interface FeedItem {
  id: string
  problem_slug: string
  problem_title?: string
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  tags: string[]
  feed_type: 'practice' | 'metric'
  practice_source?: string
  practice_reason?: string
  metric_rationale?: string
  sort_order: number
  status: 'pending' | 'completed' | 'skipped'
  was_accepted?: boolean
  was_optimal?: boolean
  runtime_percentile?: number
}

export interface DailyFeedResponse {
  user_id: string
  feed_date: string
  items: FeedItem[]
  completed_count: number
  total_count: number
  practice_count: number
  metric_count: number
}

export interface FocusNotesResponse {
  user_id: string
  focus_notes: string | null
  updated_at: string | null
}

// Onboarding Types
export interface OnboardingStatus {
  user_id: string
  has_win_rate_target: boolean
  extension_installed: boolean
  history_imported: boolean
  first_path_selected: boolean
  onboarding_complete: boolean
  current_step: number
  extension_verified_at?: string
  history_imported_at?: string
  problems_imported_count: number
  created_at?: string
  updated_at?: string
}

// Mission v2 Types (with Gemini reasoning)
export interface MissionProblem {
  problem_id: string
  problem_title?: string
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  source: 'path' | 'gap_fill' | 'review' | 'reinforcement'
  reasoning: string
  priority: number
  skills: string[]
  estimated_difficulty?: 'easy' | 'medium' | 'hard'
  completed: boolean
  completed_at?: string
}

export interface MissionResponseV2 {
  user_id: string
  mission_date: string
  daily_objective: string
  problems: MissionProblem[]
  balance_explanation?: string
  pacing_status?: 'ahead' | 'on_track' | 'behind' | 'critical'
  pacing_note?: string
  streak: number
  total_completed_today: number
  completed_count?: number
  can_regenerate: boolean
  generated_at: string
  // Legacy fields for backward compatibility
  objective?: { title: string; description: string; skill_tags: string[]; target_count: number; completed_count: number }
  main_quests?: MainQuest[]
  side_quests?: SideQuest[]
}

// System Design Types
export interface SystemDesignTrackSummary {
  id: string
  name: string
  description?: string
  track_type: string
  total_topics: number
}

export interface TopicInfo {
  name: string
  order: number
  difficulty: string
  example_systems: string[]
}

export interface RubricWeights {
  depth: number
  tradeoffs: number
  clarity: number
  scalability: number
}

export interface SystemDesignTrack extends SystemDesignTrackSummary {
  topics: TopicInfo[]
  rubric: RubricWeights
  created_at?: string
}

export interface UserTrackProgressData {
  id: string
  user_id: string
  track_id: string
  completed_topics: string[]
  sessions_completed: number
  average_score: number
  started_at: string
  last_activity_at: string
}

export interface TrackProgressResponse {
  track: SystemDesignTrack
  progress?: UserTrackProgressData
  completion_percentage: number
  next_topic?: string
}

export interface SystemDesignReviewItem {
  id: string
  user_id: string
  track_id?: string
  topic: string
  reason?: string
  priority: number
  next_review: string
  interval_days: number
  review_count: number
  last_reviewed?: string
  source_session_id?: string
  created_at: string
}

// System Design Dashboard Types
export interface NextTopicInfo {
  track_id: string
  track_name: string
  track_type: string
  topic_name: string
  topic_order: number
  topic_difficulty: string
  example_systems: string[]
  topics_completed: number
  total_topics: number
}

export interface SystemDesignDashboardSummary {
  has_active_track: boolean
  active_track?: SystemDesignTrackSummary
  next_topic?: NextTopicInfo
  oral_session?: OralSession
  reviews_due_count: number
  reviews_due: SystemDesignReviewItem[]
  recent_score?: number
  sessions_this_week: number
}

export interface ActiveTrackResponse {
  active_track_id?: string
  track?: SystemDesignTrackSummary
}

// Oral System Design Types
export interface OralFollowUpResponse {
  id: string
  question_id: string
  follow_up_index: number
  follow_up_text: string
  status: 'pending' | 'graded'
  transcript?: string
  score?: number
  feedback?: string
  addressed_gap?: boolean
  graded_at?: string
}

export interface FollowUpGradeResult {
  transcript: string
  score: number
  feedback: string
  addressed_gap: boolean
}

export interface OralSubQuestion {
  id: string
  part_number: number
  question_text: string
  focus_area: string
  key_concepts: string[]
  suggested_duration_minutes: number
  status: 'pending' | 'graded'
  overall_score?: number
  verdict?: 'pass' | 'fail' | 'borderline'
  transcript?: string
  feedback?: string
  dimension_scores?: DimensionScore[]
  missed_concepts?: string[]
  strongest_moment?: string
  weakest_moment?: string
  follow_up_questions?: string[]
  follow_up_responses?: OralFollowUpResponse[]
}

export interface OralSession {
  id: string
  user_id: string
  track_id: string
  topic: string
  scenario: string
  status: 'active' | 'completed' | 'abandoned'
  questions: OralSubQuestion[]
  created_at: string
}

export interface DimensionEvidence {
  quote: string
  analysis: string
}

export interface DimensionScore {
  name: string
  score: number
  evidence: DimensionEvidence[]
  summary: string
}

export interface OralGradeResult {
  transcript: string
  dimensions: DimensionScore[]
  overall_score: number
  verdict: 'pass' | 'borderline' | 'fail'
  feedback: string
  missed_concepts: string[]
  strongest_moment: string
  weakest_moment: string
  follow_up_questions: string[]
}

export interface OralSessionSummary {
  session_id: string
  topic: string
  questions_graded: number
  dimension_averages: Record<string, number>
  overall_score: number
  verdict: 'pass' | 'borderline' | 'fail'
  review_topics_added: string[]
}

// Language Learning Types
export interface LanguageTrackSummary {
  id: string
  name: string
  description?: string
  language: string
  level: string
  total_topics: number
}

export interface LanguageTopicInfo {
  name: string
  order: number
  difficulty: string
  key_concepts: string[]
}

export interface LanguageRubricWeights {
  accuracy: number
  grammar: number
  vocabulary: number
  naturalness: number
}

export interface LanguageTrack extends LanguageTrackSummary {
  topics: LanguageTopicInfo[]
  rubric: LanguageRubricWeights
  source_book?: string
  created_at?: string
}

export interface LanguageTrackProgressData {
  id: string
  user_id: string
  track_id: string
  completed_topics: string[]
  sessions_completed: number
  average_score: number
  started_at: string
  last_activity_at: string
}

export interface LanguageTrackProgressResponse {
  track: LanguageTrack
  progress?: LanguageTrackProgressData
  completion_percentage: number
  next_topic?: string
}

export interface CreateLanguageAttemptRequest {
  track_id: string
  topic: string
  exercise_type?: string
}

export interface LanguageAttempt {
  id: string
  user_id: string
  track_id?: string
  topic: string
  exercise_type: string
  question_text: string
  expected_answer?: string
  question_focus_area?: string
  question_key_concepts: string[]
  response_text?: string
  word_count: number
  score?: number
  verdict?: 'pass' | 'fail' | 'borderline'
  feedback?: string
  corrections?: string
  missed_concepts: string[]
  status: 'pending' | 'graded' | 'abandoned'
  created_at: string
  graded_at?: string
}

export interface LanguageAttemptGrade {
  score: number
  verdict: 'pass' | 'fail' | 'borderline'
  feedback: string
  corrections?: string
  missed_concepts: string[]
}

export interface LanguageAttemptHistoryItem {
  id: string
  topic: string
  exercise_type: string
  question_text: string
  score?: number
  verdict?: 'pass' | 'fail' | 'borderline'
  status: string
  created_at: string
  graded_at?: string
  track_name?: string
}

export interface LanguageAttemptHistoryResponse {
  attempts: LanguageAttemptHistoryItem[]
  total: number
  has_more: boolean
}

export interface LanguageReviewItem {
  id: string
  user_id: string
  track_id?: string
  topic: string
  reason?: string
  priority: number
  next_review: string
  interval_days: number
  review_count: number
  last_reviewed?: string
  source_attempt_id?: string
  created_at: string
}

export interface LanguageNextTopicInfo {
  track_id: string
  track_name: string
  language: string
  level: string
  topic_name: string
  topic_order: number
  topic_difficulty: string
  key_concepts: string[]
  topics_completed: number
  total_topics: number
}

export interface LanguageDashboardExercise {
  id: string
  exercise_type: string
  question_text: string
  topic: string
  track_id: string
  completed: boolean
}

export interface LanguageDashboardSummary {
  has_active_track: boolean
  active_track?: LanguageTrackSummary
  next_topic?: LanguageNextTopicInfo
  daily_exercise?: LanguageDashboardExercise
  reviews_due_count: number
  reviews_due: LanguageReviewItem[]
  recent_score?: number
  exercises_this_week: number
  book_total_chapters: number
  book_completed_chapters: number
  book_completion_percentage: number
}

// Daily Exercise Types
export interface DailyExercise {
  id: string
  topic: string
  exercise_type: string
  question_text: string
  expected_answer?: string
  focus_area?: string
  key_concepts: string[]
  is_review: boolean
  review_topic_reason?: string
  status: 'pending' | 'completed' | 'skipped'
  sort_order: number
  response_format: 'single_line' | 'short_text' | 'long_text' | 'free_form'
  word_target: number
  response_text?: string
  score?: number
  verdict?: string
  feedback?: string
  corrections?: string
  missed_concepts: string[]
  completed_at?: string
}

export interface DailyExerciseBatch {
  generated_date: string
  track_id?: string
  exercises: DailyExercise[]
  completed_count: number
  total_count: number
  average_score: number | null
}

export interface DailyExerciseGrade {
  score: number
  verdict: string
  feedback: string
  corrections?: string
  missed_concepts: string[]
}

// Book Progress Types
export interface BookContentSection {
  title: string
  summary: string
  key_points: string[]
}

export interface ChapterProgressItem {
  name: string
  order: number
  difficulty: string
  key_concepts: string[]
  is_completed: boolean
  is_current: boolean
  has_review_due: boolean
  review_reason?: string
  book_summary?: string
  book_sections: BookContentSection[]
}

export interface BookProgressResponse {
  track_name: string
  language: string
  level: string
  source_book?: string
  total_chapters: number
  completed_chapters: number
  completion_percentage: number
  average_score: number
  chapters: ChapterProgressItem[]
}

// ML Coding Types
export interface MLCodingProblem {
  id: string
  slug: string
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  category: string
  key_concepts: string[]
  math_concepts: string[]
  estimated_minutes: number
  sort_order: number
}

export interface MLCodingDailyExercise {
  id: string
  problem_id?: string
  problem_slug?: string
  problem_title?: string
  prompt_text: string
  starter_code?: string
  status: 'pending' | 'completed' | 'skipped'
  is_review: boolean
  sort_order: number
  submitted_code?: string
  score?: number
  verdict?: 'pass' | 'borderline' | 'fail'
  feedback?: string
  correctness_score?: number
  code_quality_score?: number
  math_understanding_score?: number
  missed_concepts: string[]
  suggested_improvements: string[]
  completed_at?: string
}

export interface MLCodingDailyBatch {
  generated_date: string
  exercises: MLCodingDailyExercise[]
  completed_count: number
  total_count: number
  average_score: number | null
}

export interface MLCodingExerciseGrade {
  score: number
  verdict: 'pass' | 'borderline' | 'fail'
  feedback: string
  correctness_score: number
  code_quality_score: number
  math_understanding_score: number
  missed_concepts: string[]
  suggested_improvements: string[]
}

export interface MLCodingReviewItem {
  id: string
  user_id: string
  problem_slug: string
  reason?: string
  priority: number
  next_review: string
  interval_days: number
  review_count: number
  last_reviewed?: string
  created_at: string
}

export interface MLCodingDashboardSummary {
  problems_attempted: number
  problems_total: number
  today_exercise_count: number
  today_completed_count: number
  average_score: number | null
  reviews_due_count: number
  recent_scores: number[]
}

export { ApiError }
