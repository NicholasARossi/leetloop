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
  getProgress: (userId: string) =>
    api<{
      stats: UserStats
      skill_scores: SkillScore[]
      trends: ProgressTrend[]
      recent_submissions: Submission[]
    }>(`/api/progress/${userId}`),

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
    status: string
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
      }),
    }),

  getTips: (userId: string) =>
    api<{ tips: string[] }>(`/api/coaching/tips/${userId}`),

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

  // Today's Focus
  getTodaysFocus: (userId: string) =>
    api<TodaysFocus>(`/api/today/${userId}`),

  // Mastery
  getMastery: (userId: string) =>
    api<MasteryResponse>(`/api/mastery/${userId}`),

  getDomainDetail: (userId: string, domainName: string) =>
    api<DomainDetailResponse>(`/api/mastery/${userId}/${encodeURIComponent(domainName)}`),
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

// Today's Focus Types
export interface DailyFocusProblem {
  slug: string
  title: string
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  category: string
  reason: string
  priority: number
}

export interface TodaysFocus {
  user_id: string
  streak: number
  daily_goal: number
  completed_today: number
  reviews_due: DailyFocusProblem[]
  path_problems: DailyFocusProblem[]
  skill_builders: DailyFocusProblem[]
  llm_insight?: string
  generated_at: string
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

export { ApiError }
