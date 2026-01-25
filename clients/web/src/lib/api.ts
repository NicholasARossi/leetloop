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

export { ApiError }
