import { test, expect } from '@playwright/test';

const TEST_USER_ID = 'test-user-daily-exercises';

// Mock data matching the DailyExerciseBatch type from api.ts
const mockExercises = [
  {
    id: 'ex-1',
    topic: 'Passé Composé',
    exercise_type: 'conjugation',
    question_text: 'Conjuguez le verbe "aller" au passé composé pour "nous":',
    focus_area: 'passé composé avec être',
    key_concepts: ['passé composé', 'auxiliaire être'],
    is_review: true,
    review_topic_reason: 'Weak area from previous exercise',
    status: 'pending' as const,
    sort_order: 0,
    response_format: 'single_line' as const,
    word_target: 3,
    missed_concepts: [],
  },
  {
    id: 'ex-2',
    topic: 'Imparfait',
    exercise_type: 'sentence_construction',
    question_text: 'Écrivez une phrase en utilisant le subjonctif avec "il faut que".',
    focus_area: 'subjonctif présent',
    key_concepts: ['subjonctif', 'expressions de nécessité'],
    is_review: false,
    status: 'pending' as const,
    sort_order: 1,
    response_format: 'short_text' as const,
    word_target: 20,
    missed_concepts: [],
  },
  {
    id: 'ex-3',
    topic: 'Subjonctif',
    exercise_type: 'situational',
    question_text:
      'Vous êtes dans un hôtel. Votre chambre a un problème. Expliquez à la réception.',
    focus_area: 'conditionnel + politesse',
    key_concepts: ['conditionnel', 'politesse'],
    is_review: false,
    status: 'pending' as const,
    sort_order: 2,
    response_format: 'long_text' as const,
    word_target: 60,
    missed_concepts: [],
  },
  {
    id: 'ex-4',
    topic: 'Expression Libre',
    exercise_type: 'journal_entry',
    question_text:
      "Racontez un souvenir d'enfance. Utilisez l'imparfait et le passé composé.",
    focus_area: 'expression écrite libre',
    key_concepts: ['imparfait', 'passé composé', 'connecteurs'],
    is_review: false,
    status: 'pending' as const,
    sort_order: 3,
    response_format: 'free_form' as const,
    word_target: 150,
    missed_concepts: [],
  },
];

const mockBatch = {
  generated_date: '2026-02-18',
  exercises: mockExercises,
  completed_count: 0,
  total_count: 4,
  average_score: null,
};

const mockGradeResponse = {
  score: 8.5,
  verdict: 'pass',
  feedback:
    'Excellent conjugation! The auxiliary verb "être" is correctly used with "aller".',
  corrections: null,
  missed_concepts: [],
};

const mockGradeResponseFail = {
  score: 3.0,
  verdict: 'fail',
  feedback:
    'The conjugation is incorrect. Remember that "aller" uses "être" as its auxiliary.',
  corrections: 'nous sommes allé(e)s',
  missed_concepts: ['auxiliaire être', 'accord du participe passé'],
};

// Helper: set up localStorage with test user ID before page navigation
async function setUserAuth(page: import('@playwright/test').Page) {
  await page.goto('http://localhost:3001/login', { waitUntil: 'commit' });
  await page.evaluate((userId) => {
    localStorage.setItem('leetloop_user_id', userId);
  }, TEST_USER_ID);
}

// Helper: mock the daily exercises API endpoint
async function mockDailyExercisesAPI(
  page: import('@playwright/test').Page,
  batch: Record<string, unknown> = mockBatch,
) {
  await page.route(
    `**/api/language/${TEST_USER_ID}/daily-exercises`,
    (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(batch),
        });
      } else {
        route.continue();
      }
    },
  );
}

// Helper: mock the submit endpoint
async function mockSubmitAPI(
  page: import('@playwright/test').Page,
  grade: Record<string, unknown> = mockGradeResponse,
) {
  await page.route('**/api/language/daily-exercises/*/submit', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(grade),
    });
  });
}

// Helper: mock the regenerate endpoint
async function mockRegenerateAPI(page: import('@playwright/test').Page) {
  const regeneratedBatch = {
    ...mockBatch,
    exercises: mockBatch.exercises.map((ex) => ({
      ...ex,
      id: `regen-${ex.id}`,
      question_text: `[Regenerated] ${ex.question_text}`,
    })),
  };

  await page.route(
    `**/api/language/${TEST_USER_ID}/daily-exercises/regenerate`,
    (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(regeneratedBatch),
      });
    },
  );
}

test.describe('Daily Exercise Dashboard', () => {
  test.describe('Page Loading', () => {
    test('should display loading state while fetching exercises', async ({
      page,
    }) => {
      await setUserAuth(page);

      // Delay the API response so loading state is visible
      await page.route(
        `**/api/language/${TEST_USER_ID}/daily-exercises`,
        async (route) => {
          await new Promise((r) => setTimeout(r, 2000));
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockBatch),
          });
        },
      );

      await page.goto('/language');

      // Should show loading indicator
      await expect(
        page.getByText("Loading today's exercises..."),
      ).toBeVisible();
    });

    test('should display daily exercises after loading', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // Wait for exercises to render
      await expect(page.getByText("Today's Exercises")).toBeVisible();

      // Check that exercise cards render with question text
      await expect(
        page.getByText('Conjuguez le verbe "aller"', { exact: false }),
      ).toBeVisible();
      await expect(
        page.getByText('Écrivez une phrase en utilisant', { exact: false }),
      ).toBeVisible();
      await expect(
        page.getByText('Vous êtes dans un hôtel', { exact: false }),
      ).toBeVisible();
    });

    test('should show progress header with correct count', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      await expect(page.getByText("Today's Exercises")).toBeVisible();
      // Progress counter: "0/4" (completedCount / totalCount)
      await expect(page.getByText('/4')).toBeVisible();
    });
  });

  test.describe('Exercise Card Interaction', () => {
    test('should show question text on exercise card', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      await expect(
        page.getByText(
          'Conjuguez le verbe "aller" au passé composé pour "nous":',
        ),
      ).toBeVisible();
    });

    test('should show exercise type tag', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // Exercise type displayed as uppercase tag
      await expect(page.getByText('CONJUGATION')).toBeVisible();
      await expect(page.getByText('SENTENCE_CONSTRUCTION')).toBeVisible();
      await expect(page.getByText('SITUATIONAL')).toBeVisible();
    });

    test('should show review badge for review exercises', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // The review exercise (ex-1) should show a "Review" badge
      await expect(page.getByText('Review')).toBeVisible();

      // The "Reviews" section heading should appear
      await expect(page.getByText('Reviews')).toBeVisible();
    });

    test('should enable submit button when text is entered', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // Find the first input field (single_line exercise)
      const firstInput = page.getByPlaceholder('Your answer...').first();
      const firstSubmitBtn = page
        .getByRole('button', { name: 'Submit' })
        .first();

      // Submit should be disabled initially (no text)
      await expect(firstSubmitBtn).toBeDisabled();

      // Type text into the input
      await firstInput.fill('nous sommes allés');

      // Submit should now be enabled
      await expect(firstSubmitBtn).toBeEnabled();
    });

    test('should show grading state after submit', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      // Delay the submit response to see the grading state
      await page.route(
        '**/api/language/daily-exercises/*/submit',
        async (route) => {
          await new Promise((r) => setTimeout(r, 1500));
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockGradeResponse),
          });
        },
      );

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Should show "Grading..." while waiting
      await expect(
        page.getByRole('button', { name: 'Grading...' }),
      ).toBeVisible();
    });
  });

  test.describe('Tiered Response Formats', () => {
    test('should render input for single_line exercises', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // The conjugation exercise (single_line) should have an <input>
      const reviewSection = page.locator('.section-id', { hasText: 'Reviews' });
      await expect(reviewSection).toBeVisible();

      // First exercise (conjugation, single_line) should use input, not textarea
      const firstCard = page
        .getByText('Conjuguez le verbe "aller"', { exact: false })
        .locator('..');
      const inputField = firstCard.locator('input[type="text"]');
      await expect(inputField).toBeVisible();
    });

    test('should render textarea for short_text exercises', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // The sentence_construction exercise (short_text) should have a <textarea>
      const card = page
        .getByText('Écrivez une phrase en utilisant', { exact: false })
        .locator('..');
      const textarea = card.locator('textarea');
      await expect(textarea).toBeVisible();
    });

    test('should render textarea for long_text exercises with word count', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // The situational exercise (long_text) should show word count
      await expect(
        page.getByText('target: 60', { exact: false }),
      ).toBeVisible();
    });

    test('should render textarea for free_form exercises with word count', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // The journal_entry exercise (free_form) should show word count
      await expect(
        page.getByText('target: 150', { exact: false }),
      ).toBeVisible();
    });

    test('should show Cmd+Enter hint for textarea exercises', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // Textarea exercises should show keyboard shortcut hint
      await expect(
        page.getByText('Enter to submit', { exact: false }).first(),
      ).toBeVisible();
    });

    test('should update word count as user types in textarea', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // Find the long_text textarea (situational exercise)
      const textareas = page.locator('textarea');
      // First textarea is the short_text one, second is long_text, third is free_form
      const longTextArea = textareas.nth(1);
      await longTextArea.fill('Bonjour monsieur je voudrais');

      // Word count should update
      await expect(
        page.getByText('4 words', { exact: false }),
      ).toBeVisible();
    });
  });

  test.describe('Grading Flow', () => {
    test('should display score after grading', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page);

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // After grading, the card should collapse and show the score
      await expect(page.getByText('8.5')).toBeVisible({ timeout: 5000 });
    });

    test('should display verdict badge after grading', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page);

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Should show PASS badge (use locator with class to avoid matching other text)
      await expect(
        page.locator('.badge-accent', { hasText: 'PASS' }),
      ).toBeVisible({ timeout: 5000 });
    });

    test('should display feedback after expanding graded card', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page);

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Wait for graded state
      await expect(page.getByText('8.5')).toBeVisible({ timeout: 5000 });

      // Click the graded card to expand it
      await page.getByText('8.5').click();

      // Should show the feedback text
      await expect(
        page.getByText('Excellent conjugation!', { exact: false }),
      ).toBeVisible();
    });

    test('should collapse graded card to summary line', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page);

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Wait for grading to complete
      await expect(page.getByText('8.5')).toBeVisible({ timeout: 5000 });

      // In collapsed state, the full question text should NOT be visible
      // (only the focus_area or topic and score are shown)
      await expect(
        page.getByText('passé composé avec être'),
      ).toBeVisible();

      // The full feedback should be hidden until expanded
      await expect(
        page.getByText('Excellent conjugation!', { exact: false }),
      ).not.toBeVisible();
    });

    test('should expand graded card on click to reveal full details', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page);

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Wait for grading
      await expect(page.getByText('8.5')).toBeVisible({ timeout: 5000 });

      // Click to expand
      await page.getByText('passé composé avec être').click();

      // Expanded: question, answer, feedback should be visible
      await expect(page.getByText('Q:')).toBeVisible();
      await expect(page.getByText('A:')).toBeVisible();
      await expect(page.getByText('Feedback:')).toBeVisible();
      await expect(
        page.getByText('Excellent conjugation!', { exact: false }),
      ).toBeVisible();
    });

    test('should show corrections for failed exercises', async ({ page }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page, mockGradeResponseFail);

      await page.goto('/language');

      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous avons allé');

      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Wait for grading
      await expect(page.getByText('3.0')).toBeVisible({ timeout: 5000 });
      await expect(page.getByText('FAIL')).toBeVisible();

      // Expand card
      await page.getByText('3.0').click();

      // Should show correction
      await expect(page.getByText('Correction:')).toBeVisible();
      await expect(page.getByText('nous sommes allé(e)s')).toBeVisible();

      // Should show missed concepts as tags
      await expect(page.getByText('auxiliaire être')).toBeVisible();
      await expect(
        page.getByText('accord du participe passé'),
      ).toBeVisible();
    });
  });

  test.describe('Progress Tracking', () => {
    test('should update progress count after completing exercise', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);
      await mockSubmitAPI(page);

      await page.goto('/language');

      // Initially 0/4 - use text-gray-600 to distinguish from input fields
      const progressText = page.locator('.font-mono.text-sm.text-gray-600');
      await expect(progressText).toContainText('/4');

      // Submit an answer
      const firstInput = page.getByPlaceholder('Your answer...').first();
      await firstInput.fill('nous sommes allés');
      const submitBtn = page.getByRole('button', { name: 'Submit' }).first();
      await submitBtn.click();

      // Wait for grading
      await expect(page.getByText('8.5')).toBeVisible({ timeout: 5000 });

      // Progress should now show 1 completed
      await expect(progressText).toContainText('1');
    });

    test('should show completion state when all exercises done', async ({
      page,
    }) => {
      await setUserAuth(page);

      // Create a batch where all exercises are already completed
      const completedBatch = {
        ...mockBatch,
        exercises: mockExercises.map((ex) => ({
          ...ex,
          status: 'completed' as const,
          response_text: 'test answer',
          score: 8.0,
          verdict: 'pass',
          feedback: 'Good job!',
        })),
        completed_count: 4,
        total_count: 4,
        average_score: 8.0,
      };

      await mockDailyExercisesAPI(page, completedBatch);
      await mockRegenerateAPI(page);

      await page.goto('/language');

      // Should show the completion summary
      await expect(
        page.getByText("Today's exercises complete!"),
      ).toBeVisible();

      // Should show stats
      await expect(page.getByText('Done')).toBeVisible();
      await expect(page.getByText('Avg Score')).toBeVisible();

      // Should show regenerate button
      await expect(
        page.getByRole('button', { name: 'Regenerate Exercises' }),
      ).toBeVisible();
    });
  });

  test.describe('Regeneration', () => {
    test('should regenerate exercises on button click', async ({ page }) => {
      await setUserAuth(page);

      // Start with all completed
      const completedBatch = {
        ...mockBatch,
        exercises: mockExercises.map((ex) => ({
          ...ex,
          status: 'completed' as const,
          response_text: 'test answer',
          score: 8.0,
          verdict: 'pass',
          feedback: 'Good job!',
        })),
        completed_count: 4,
        total_count: 4,
        average_score: 8.0,
      };

      await mockDailyExercisesAPI(page, completedBatch);
      await mockRegenerateAPI(page);

      await page.goto('/language');

      // Should show completion state
      await expect(
        page.getByText("Today's exercises complete!"),
      ).toBeVisible();

      // Click regenerate
      const regenBtn = page.getByRole('button', {
        name: 'Regenerate Exercises',
      });
      await regenBtn.click();

      // After regeneration, new exercises should appear with [Regenerated] prefix
      await expect(
        page.getByText('[Regenerated]', { exact: false }).first(),
      ).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Error Handling', () => {
    test('should show error message on API failure', async ({ page }) => {
      await setUserAuth(page);

      // Mock API to return an error
      await page.route(
        `**/api/language/${TEST_USER_ID}/daily-exercises`,
        (route) => {
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Internal server error' }),
          });
        },
      );

      await page.goto('/language');

      // Should display the error message
      await expect(page.getByText('Internal server error')).toBeVisible({
        timeout: 5000,
      });

      // Should show retry button
      await expect(
        page.getByRole('button', { name: 'Retry' }),
      ).toBeVisible();
    });

    test('should show track selection when no active track', async ({
      page,
    }) => {
      await setUserAuth(page);

      // Mock the daily exercises endpoint to return 400 "no active track"
      await page.route(
        `**/api/language/${TEST_USER_ID}/daily-exercises`,
        (route) => {
          route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              detail: 'No active language track set for this user.',
            }),
          });
        },
      );

      // Mock the tracks endpoint
      await page.route('**/api/language/tracks', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'track-1',
              name: 'French Verbs',
              description: 'Master French verb conjugation',
              language: 'french',
              level: 'b1',
              total_topics: 13,
            },
          ]),
        });
      });

      await page.goto('/language');

      // Should show track selection UI
      await expect(
        page.getByRole('heading', { name: 'Choose a Track' }),
      ).toBeVisible({
        timeout: 5000,
      });
      await expect(page.getByText('French Verbs')).toBeVisible();
      await expect(page.getByText('FRENCH', { exact: true })).toBeVisible();
      await expect(page.getByText('B1', { exact: true })).toBeVisible();
      await expect(
        page.getByRole('button', { name: 'Set Active' }),
      ).toBeVisible();
    });
  });

  test.describe('Section Organization', () => {
    test('should separate review exercises from new exercises', async ({
      page,
    }) => {
      await setUserAuth(page);
      await mockDailyExercisesAPI(page);

      await page.goto('/language');

      // Wait for exercises to load
      await expect(page.getByText("Today's Exercises")).toBeVisible();

      // Should have "REVIEWS" section-id heading for review exercises
      await expect(
        page.locator('.section-id', { hasText: 'Reviews' }),
      ).toBeVisible();

      // Should have "EXERCISES" section-id heading for new exercises
      await expect(
        page.locator('.section-id', { hasText: 'Exercises' }),
      ).toBeVisible();
    });
  });
});
