import { test, expect, Page } from '@playwright/test'

const TEST_USER_ID = 'test-user-ml-coding-editor'

const mockExercise = {
  id: 'ex-1',
  problem_id: 'kmeans-1',
  problem_slug: 'implement-kmeans',
  problem_title: 'Implement K-Means',
  prompt_text: 'Implement the K-means clustering algorithm from scratch using numpy.',
  starter_code: '',
  status: 'pending' as const,
  is_review: false,
  sort_order: 0,
  missed_concepts: [],
  suggested_improvements: [],
}

const mockBatch = {
  generated_date: '2026-03-16',
  exercises: [mockExercise],
  completed_count: 0,
  total_count: 1,
  average_score: null,
}

async function setUserAuth(page: Page) {
  await page.goto('http://localhost:3001/login', { waitUntil: 'commit' })
  await page.evaluate((userId) => {
    localStorage.setItem('leetloop_user_id', userId)
  }, TEST_USER_ID)
}

async function mockMLCodingAPI(page: Page, batch = mockBatch) {
  await page.route(`**/api/ml-coding/${TEST_USER_ID}/daily-exercises`, (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(batch),
      })
    } else {
      route.continue()
    }
  })
}

async function getEditor(page: Page) {
  return page.locator('.code-editor-textarea')
}

test.describe('ML Coding Editor', () => {
  test.beforeEach(async ({ page }) => {
    await setUserAuth(page)
    await mockMLCodingAPI(page)
  })

  test.describe('Basic typing', () => {
    test('should accept regular text input', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('import numpy as np')
      await expect(editor).toHaveValue('import numpy as np')
    })

    test('should handle angle brackets without breaking', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('if x < 5 and y > 3:')
      await expect(editor).toHaveValue('if x < 5 and y > 3:')
    })

    test('should handle comparison operators', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('x <= 10 and y >= 0 and z != 5')
      await expect(editor).toHaveValue('x <= 10 and y >= 0 and z != 5')
    })

    test('should handle type annotations with brackets', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('def foo(x: list[int]) -> dict[str, float]:')
      await expect(editor).toHaveValue('def foo(x: list[int]) -> dict[str, float]:')
    })

    test('should handle ampersands and special chars', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('x = a & b | c')
      await expect(editor).toHaveValue('x = a & b | c')
    })
  })

  test.describe('Syntax highlighting', () => {
    test('should render highlighted keywords in overlay', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('import numpy as np')

      const highlight = page.locator('.code-editor-highlight')
      await expect(highlight).toBeVisible()
      const html = await highlight.innerHTML()
      expect(html).toContain('py-kw')
      expect(html).toContain('import')
    })

    test('should highlight strings', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('name = "hello world"')

      const html = await page.locator('.code-editor-highlight').innerHTML()
      expect(html).toContain('py-str')
    })

    test('should highlight comments', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('# this is a comment')

      const html = await page.locator('.code-editor-highlight').innerHTML()
      expect(html).toContain('py-cmt')
    })

    test('should highlight numbers', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('x = 42')

      const html = await page.locator('.code-editor-highlight').innerHTML()
      expect(html).toContain('py-num')
    })

    test('should highlight function names after def', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('def kmeans():')

      const html = await page.locator('.code-editor-highlight').innerHTML()
      expect(html).toContain('py-fn')
      expect(html).toContain('kmeans')
    })

    test('should escape angle brackets in highlight layer', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('if x < 5:')

      const html = await page.locator('.code-editor-highlight').innerHTML()
      // Should be escaped as &lt; not raw <
      expect(html).toContain('&lt;')
      expect(html).not.toMatch(/<\s*5/)
    })
  })

  test.describe('Tab indentation', () => {
    test('should insert 2 spaces on Tab', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.press('Tab')
      await expect(editor).toHaveValue('  ')
    })

    test('should insert Tab mid-line', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      // Type two words with Tab between them
      await editor.pressSequentially('xy')
      // Move cursor back one character
      await editor.press('ArrowLeft')
      await editor.press('Tab')
      await expect(editor).toHaveValue('x  y')
    })
  })

  test.describe('Auto-indent on Enter', () => {
    test('should maintain indent level on Enter', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      // Type an indented line and press Enter
      await editor.pressSequentially('  x = 1')
      await editor.press('Enter')
      await page.waitForTimeout(100)
      await editor.pressSequentially('y = 2')
      await expect(editor).toHaveValue('  x = 1\n  y = 2')
    })

    test('should add extra indent after colon', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.pressSequentially('def foo():')
      await editor.press('Enter')
      await page.waitForTimeout(100)
      await editor.pressSequentially('return 1')
      await expect(editor).toHaveValue('def foo():\n  return 1')
    })

    test('should add extra indent after if-colon', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.pressSequentially('if x > 0:')
      await editor.press('Enter')
      await page.waitForTimeout(100)
      await editor.pressSequentially('print(x)')
      await expect(editor).toHaveValue('if x > 0:\n  print(x)')
    })

    test('should maintain nested indent after colon', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.pressSequentially('def foo():')
      await editor.press('Enter')
      await page.waitForTimeout(100)
      await editor.pressSequentially('if True:')
      await editor.press('Enter')
      await page.waitForTimeout(100)
      await editor.pressSequentially('pass')
      await expect(editor).toHaveValue('def foo():\n  if True:\n    pass')
    })

    test('should not add extra indent without colon', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.pressSequentially('x = 1')
      await editor.press('Enter')
      await editor.pressSequentially('y = 2')
      await expect(editor).toHaveValue('x = 1\ny = 2')
    })
  })

  test.describe('Submit shortcut', () => {
    test('should submit on Cmd+Enter', async ({ page }) => {
      // Mock the submit endpoint
      let submittedCode = ''
      await page.route('**/api/ml-coding/daily-exercises/*/submit', (route) => {
        const body = JSON.parse(route.request().postData() || '{}')
        submittedCode = body.submitted_code
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            score: 8.0,
            verdict: 'pass',
            feedback: 'Good job',
            correctness_score: 8.0,
            code_quality_score: 8.0,
            math_understanding_score: 8.0,
            missed_concepts: [],
            suggested_improvements: [],
          }),
        })
      })

      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('import numpy as np')
      await editor.press('Meta+Enter')

      // Should transition to graded state — score appears in collapsed summary
      await expect(page.locator('.tag', { hasText: 'Implement K-Means' })).toBeVisible({ timeout: 5000 })
      expect(submittedCode).toBe('import numpy as np')
    })
  })

  test.describe('Line numbers', () => {
    test('should show line numbers matching code lines', async ({ page }) => {
      await page.goto('/ml-coding')
      const editor = await getEditor(page)
      await editor.click()
      await editor.fill('line1\nline2\nline3')

      const gutter = page.locator('.code-editor-gutter')
      await expect(gutter).toBeVisible()
      // Should have at least 15 line numbers (minimum)
      const lineNums = gutter.locator('.line-num')
      const count = await lineNums.count()
      expect(count).toBeGreaterThanOrEqual(15)
      // First three should be 1, 2, 3
      await expect(lineNums.nth(0)).toHaveText('1')
      await expect(lineNums.nth(1)).toHaveText('2')
      await expect(lineNums.nth(2)).toHaveText('3')
    })
  })

  test.describe('Editor structure', () => {
    test('should render header with problem title and Python badge', async ({ page }) => {
      await page.goto('/ml-coding')
      const header = page.locator('.code-editor-header')
      await expect(header).toBeVisible()
      await expect(header.getByText('Implement K-Means')).toBeVisible()
      await expect(header.getByText('Python')).toBeVisible()
    })

    test('should render footer with keyboard hints', async ({ page }) => {
      await page.goto('/ml-coding')
      const footer = page.locator('.code-editor-footer')
      await expect(footer).toBeVisible()
      await expect(footer.locator('kbd').first()).toBeVisible()
      await expect(footer.getByRole('button', { name: /submit/i })).toBeVisible()
    })

    test('should show problem prompt above editor', async ({ page }) => {
      await page.goto('/ml-coding')
      await expect(page.getByText('Implement the K-means clustering')).toBeVisible()
    })
  })
})
