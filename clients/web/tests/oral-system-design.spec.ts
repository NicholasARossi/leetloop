import { test, expect } from '@playwright/test';

const TEST_USER_ID = 'test-user-oral-sd';

// ===== Mock Data =====

const mockOralSession = {
  id: 'oral-session-1',
  user_id: TEST_USER_ID,
  track_id: 'track-1',
  topic: 'Netflix Recommendation System',
  scenario: 'You are designing the recommendation engine for Netflix, serving 200M+ users with personalized content.',
  status: 'active',
  questions: [
    {
      id: 'oq-1',
      part_number: 1,
      question_text: 'How would you model the data for Netflix recommendations?',
      focus_area: 'Data & Storage',
      key_concepts: ['user profiles', 'content metadata', 'interaction logs'],
      suggested_duration_minutes: 4,
      status: 'pending',
    },
    {
      id: 'oq-2',
      part_number: 2,
      question_text: 'Design the batch and real-time inference pipeline.',
      focus_area: 'ML Pipeline',
      key_concepts: ['candidate generation', 'ranking', 'serving'],
      suggested_duration_minutes: 4,
      status: 'pending',
    },
    {
      id: 'oq-3',
      part_number: 3,
      question_text: 'How would you set up A/B testing for this recommendation system?',
      focus_area: 'Evaluation',
      key_concepts: ['metrics', 'experiment design', 'guardrails'],
      suggested_duration_minutes: 4,
      status: 'pending',
    },
  ],
  created_at: new Date().toISOString(),
};

const mockDimensionScores = [
  {
    name: 'technical_depth',
    score: 6,
    evidence: [
      { quote: 'I would use a collaborative filtering approach with user embeddings', analysis: 'Shows understanding of basic ML approach but lacks specific implementation details' },
    ],
    summary: 'Solid foundational understanding with room for more depth',
  },
  {
    name: 'structure_and_approach',
    score: 7,
    evidence: [
      { quote: 'Let me start with the data layer, then move to the serving infrastructure', analysis: 'Clear structure with logical flow' },
    ],
    summary: 'Well-organized response with clear sections',
  },
  {
    name: 'tradeoff_reasoning',
    score: 5,
    evidence: [
      { quote: 'We could use Redis for caching but DynamoDB might be better for persistence', analysis: 'Mentions alternatives but does not deeply compare them' },
    ],
    summary: 'Surface-level trade-off discussion',
  },
  {
    name: 'ml_data_fluency',
    score: 7,
    evidence: [
      { quote: 'The two-tower model gives us efficient retrieval with separate user and item encoders', analysis: 'Demonstrates practical knowledge of recommendation architectures' },
    ],
    summary: 'Strong ML knowledge with practical experience',
  },
  {
    name: 'communication_quality',
    score: 6,
    evidence: [
      { quote: 'So moving on to the serving layer, we need to think about latency requirements', analysis: 'Good transitions between sections with clear signposting' },
    ],
    summary: 'Clear communication with some filler',
  },
];

const mockGradeResult = {
  transcript: 'So for the Netflix recommendation system, I would start by thinking about the data model. We need user profiles with viewing history, content metadata including genres and actors, and real-time interaction signals.',
  dimensions: mockDimensionScores,
  overall_score: 6.2,
  verdict: 'borderline',
  feedback: 'Good foundational understanding of recommendation systems. To improve, go deeper on specific technical choices and trade-offs.',
  missed_concepts: ['cold start problem', 'feature store'],
  strongest_moment: 'The two-tower model gives us efficient retrieval with separate user and item encoders',
  weakest_moment: 'Did not address how to handle new users with no viewing history',
  follow_up_questions: [
    'How would you handle the cold start problem for new users?',
    'What metrics would you optimize for and how would you measure long-term engagement?',
  ],
};

const mockOralSessionPartiallyGraded = {
  ...mockOralSession,
  questions: [
    {
      ...mockOralSession.questions[0],
      status: 'graded',
      overall_score: 6.2,
      verdict: 'borderline',
      transcript: mockGradeResult.transcript,
      feedback: mockGradeResult.feedback,
      dimension_scores: mockDimensionScores,
      missed_concepts: mockGradeResult.missed_concepts,
      strongest_moment: mockGradeResult.strongest_moment,
      weakest_moment: mockGradeResult.weakest_moment,
      follow_up_questions: mockGradeResult.follow_up_questions,
    },
    mockOralSession.questions[1],
    mockOralSession.questions[2],
  ],
};

const mockOralSessionCompleted = {
  ...mockOralSession,
  status: 'completed',
  questions: mockOralSession.questions.map((q, i) => ({
    ...q,
    status: 'graded',
    overall_score: [6.2, 7.1, 5.8][i],
    verdict: ['borderline', 'pass', 'borderline'][i],
    transcript: 'Mock transcript for question ' + (i + 1),
    feedback: 'Mock feedback for question ' + (i + 1),
    dimension_scores: mockDimensionScores,
    missed_concepts: ['concept ' + (i + 1)],
    strongest_moment: 'Strong moment ' + (i + 1),
    weakest_moment: 'Weak moment ' + (i + 1),
    follow_up_questions: ['Follow up ' + (i + 1)],
  })),
};

const mockDashboardBase = {
  has_active_track: true,
  active_track: { id: 'track-1', name: 'MLE Track', track_type: 'mle', total_topics: 10 },
  next_topic: {
    track_id: 'track-1',
    track_name: 'MLE Track',
    track_type: 'mle',
    topic_name: 'Netflix Recommendation System',
    topic_order: 0,
    topic_difficulty: 'hard',
    example_systems: ['Netflix', 'YouTube', 'Spotify'],
    topics_completed: 0,
    total_topics: 10,
  },
  daily_questions: [],
  reviews_due_count: 0,
  reviews_due: [],
  recent_score: null,
  sessions_this_week: 0,
};

// ===== Helpers =====

async function setUserAuth(page: import('@playwright/test').Page) {
  await page.goto('http://localhost:3001/login', { waitUntil: 'commit' });
  await page.evaluate((userId) => {
    localStorage.setItem('leetloop_user_id', userId);
  }, TEST_USER_ID);
}

async function mockAllDashboardAPIs(
  page: import('@playwright/test').Page,
  dashboardOverrides: Record<string, unknown> = {},
) {
  const dashboardData = { ...mockDashboardBase, ...dashboardOverrides };

  await page.route(`**/api/users/${TEST_USER_ID}/onboarding-status`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ onboarding_complete: true }) });
  });

  await page.route(`**/api/progress/${TEST_USER_ID}/win-rate-stats`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ targets: null }) });
  });

  await page.route(`**/api/feed/${TEST_USER_ID}/daily`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], generated_at: new Date().toISOString() }) });
  });

  await page.route(`**/api/system-design/${TEST_USER_ID}/dashboard`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(dashboardData) });
  });

  await page.route(`**/api/progress/${TEST_USER_ID}**`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ trends: [], stats: null }) });
  });

  await page.route(`**/api/users/${TEST_USER_ID}/focus-notes`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ focus_notes: null }) });
  });
}

async function mockOralSessionAPI(
  page: import('@playwright/test').Page,
  session: Record<string, unknown> = mockOralSession as unknown as Record<string, unknown>,
) {
  await page.route('**/api/system-design/oral-sessions/*', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(session) });
    } else {
      route.continue();
    }
  });
}

async function mockSystemDesignPageAPIs(page: import('@playwright/test').Page) {
  await page.route('**/api/system-design/tracks', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route(`**/api/system-design/${TEST_USER_ID}/active-track`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ active_track_id: null }) });
  });

  await page.route(`**/api/system-design/${TEST_USER_ID}/oral-sessions*`, (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
}

// ===== Tests =====

test.describe('Oral System Design - Dashboard Card', () => {
  test('oral questions appear on dashboard', async ({ page }) => {
    await setUserAuth(page);
    await mockAllDashboardAPIs(page, { oral_session: mockOralSession });

    await page.goto('/dashboard');

    // 3 sub-questions visible with focus area labels
    await expect(page.getByText('Data & Storage')).toBeVisible();
    await expect(page.getByText('ML Pipeline')).toBeVisible();
    await expect(page.getByText('Evaluation')).toBeVisible();

    // Each pending question shows Record link
    const recordLinks = page.getByRole('link', { name: 'Record', exact: true });
    await expect(recordLinks).toHaveCount(3);

    // Scenario can be shown
    await page.getByText('Show scenario').click();
    await expect(page.getByText('200M+ users', { exact: false })).toBeVisible();
  });

  test('graded question shows score on dashboard', async ({ page }) => {
    await setUserAuth(page);
    await mockAllDashboardAPIs(page, { oral_session: mockOralSessionPartiallyGraded });

    await page.goto('/dashboard');

    // Q1 shows verdict badge
    await expect(page.getByText('borderline').first()).toBeVisible();

    // Q1 shows View link (scoped to the SD card section)
    const sdCard = page.locator('.card').filter({ hasText: 'System Design Practice' });
    await expect(sdCard.getByRole('link', { name: 'View', exact: true })).toBeVisible();

    // Q2, Q3 still show Record
    const recordLinks = sdCard.getByRole('link', { name: 'Record', exact: true });
    await expect(recordLinks).toHaveCount(2);

    // View Full Session link visible
    await expect(sdCard.getByText('View Full Session')).toBeVisible();
  });

  test('completed session shows overall score on dashboard', async ({ page }) => {
    await setUserAuth(page);
    await mockAllDashboardAPIs(page, {
      oral_session: mockOralSessionCompleted,
      recent_score: 6.4,
    });

    await page.goto('/dashboard');

    // Overall score visible
    const sdCard = page.locator('.card').filter({ hasText: 'System Design Practice' });
    await expect(sdCard.getByText('6.4/10')).toBeVisible();

    // All 3 questions show View links (no Record links)
    const viewLinks = sdCard.getByRole('link', { name: 'View', exact: true });
    await expect(viewLinks).toHaveCount(3);

    const recordLinks = sdCard.getByRole('link', { name: 'Record', exact: true });
    await expect(recordLinks).toHaveCount(0);
  });

  test('clicking Record navigates to oral flow', async ({ page }) => {
    await setUserAuth(page);
    await mockAllDashboardAPIs(page, { oral_session: mockOralSession });
    await mockSystemDesignPageAPIs(page);
    await mockOralSessionAPI(page);

    await page.goto('/dashboard');

    // Click Record on Q1
    const sdCard = page.locator('.card').filter({ hasText: 'System Design Practice' });
    await sdCard.getByRole('link', { name: 'Record', exact: true }).first().click();

    // Should navigate to system-design page with session params
    await page.waitForURL('**/system-design?session=*');

    // Correct question should be displayed
    await expect(page.getByText('Data & Storage').first()).toBeVisible();
    await expect(page.getByText('How would you model the data', { exact: false })).toBeVisible();

    // Audio input tabs should be visible
    await expect(page.getByRole('button', { name: /^Record$/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Upload File/i })).toBeVisible();
  });

  test('no oral session shows fallback CTA', async ({ page }) => {
    await setUserAuth(page);
    await mockAllDashboardAPIs(page, { oral_session: null });

    await page.goto('/dashboard');

    await expect(page.getByText('Start Oral Practice')).toBeVisible();
  });
});

test.describe('Oral System Design - Record & Grade Flow', () => {
  test('navigates to oral flow and shows upload tab', async ({ page }) => {
    await setUserAuth(page);
    await mockSystemDesignPageAPIs(page);
    await mockOralSessionAPI(page);

    await page.route('**/api/system-design/oral-questions/*/submit-audio', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockGradeResult) });
    });

    await page.goto(`/system-design?session=${mockOralSession.id}&q=0`);

    // Wait for question to load
    await expect(page.getByText('Data & Storage').first()).toBeVisible();
    await expect(page.getByText('How would you model the data', { exact: false })).toBeVisible();

    // Switch to Upload tab
    await page.getByRole('button', { name: /Upload File/i }).click();

    // The upload zone should be visible
    await expect(page.getByText('Drop audio file here', { exact: false })).toBeVisible();
  });
});

test.describe('Oral System Design - Session Detail Page', () => {
  test('loads with full grades for completed session', async ({ page }) => {
    await setUserAuth(page);
    await mockOralSessionAPI(page, mockOralSessionCompleted as unknown as Record<string, unknown>);

    await page.goto(`/system-design/session/${mockOralSessionCompleted.id}`);

    // Header with topic and scenario
    await expect(page.getByText('Netflix Recommendation System').first()).toBeVisible();
    await expect(page.getByText('200M+ users', { exact: false })).toBeVisible();

    // Dimension averages section
    await expect(page.getByText('Dimension Averages')).toBeVisible();

    // Use first() to avoid strict mode with repeated labels
    await expect(page.getByText('Technical Depth').first()).toBeVisible();
    await expect(page.getByText('Trade-off Reasoning').first()).toBeVisible();

    // 3 question sections with focus area titles
    await expect(page.getByText('Q1: Data & Storage')).toBeVisible();
    await expect(page.getByText('Q2: ML Pipeline')).toBeVisible();
    await expect(page.getByText('Q3: Evaluation')).toBeVisible();
  });

  test('pending questions show placeholder', async ({ page }) => {
    await setUserAuth(page);
    await mockOralSessionAPI(page, mockOralSessionPartiallyGraded as unknown as Record<string, unknown>);

    await page.goto(`/system-design/session/${mockOralSessionPartiallyGraded.id}`);

    // Q1 shows grade content
    await expect(page.getByText('Q1: Data & Storage')).toBeVisible();

    // Q2, Q3 show "Not yet answered" placeholders
    const placeholders = page.getByText('Not yet answered');
    await expect(placeholders).toHaveCount(2);

    // Record Answer links for pending questions
    const recordLinks = page.getByRole('link', { name: 'Record Answer' });
    await expect(recordLinks).toHaveCount(2);
  });

  test('dimension evidence is expandable', async ({ page }) => {
    await setUserAuth(page);
    await mockOralSessionAPI(page, mockOralSessionCompleted as unknown as Record<string, unknown>);

    await page.goto(`/system-design/session/${mockOralSessionCompleted.id}`);

    // Dimension scores should be visible (use first() since 3 graded questions each show dims)
    await expect(page.getByText('Technical Depth').first()).toBeVisible();
    await expect(page.getByText('Structure', { exact: false }).first()).toBeVisible();
  });

  test('back to dashboard link works', async ({ page }) => {
    await setUserAuth(page);
    await mockOralSessionAPI(page, mockOralSessionCompleted as unknown as Record<string, unknown>);
    await mockAllDashboardAPIs(page, { oral_session: mockOralSessionCompleted });

    await page.goto(`/system-design/session/${mockOralSessionCompleted.id}`);

    // Use exact match on the bottom button to avoid ambiguity
    await page.getByRole('link', { name: 'Back to Dashboard', exact: true }).click();

    await page.waitForURL('**/dashboard');
  });
});
