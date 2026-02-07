import { test, expect, chromium, BrowserContext } from '@playwright/test';
import path from 'path';
import { config } from 'dotenv';

// Load environment variables from extension .env
config({ path: path.resolve(__dirname, '../.env') });

const EXTENSION_PATH = path.resolve(__dirname, '../dist');
const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY!;

/**
 * Helper to fetch submissions from Supabase (for test verification)
 * Note: Extension routes through API, but tests verify data via Supabase directly
 */
async function getSubmissions(limit = 10): Promise<any[]> {
  const response = await fetch(
    `${SUPABASE_URL}/rest/v1/submissions?select=*&order=submitted_at.desc&limit=${limit}`,
    {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
      },
    }
  );
  return response.json();
}

/**
 * Helper to get submission count
 */
async function getSubmissionCount(): Promise<number> {
  const submissions = await getSubmissions(100);
  return submissions.length;
}

/**
 * Launch browser with extension loaded
 */
async function launchBrowserWithExtension(): Promise<BrowserContext> {
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`,
    ],
  });
  return context;
}

/**
 * Verify extension is configured (API URL is baked in at build time)
 */
async function verifyExtensionConfigured(context: BrowserContext): Promise<void> {
  const extensionId = await getExtensionId(context);

  // Open extension options page to verify it loads
  const optionsPage = await context.newPage();
  await optionsPage.goto(`chrome-extension://${extensionId}/options/options.html`);

  // Verify the page loaded and has the expected elements
  await optionsPage.waitForSelector('#api-url', { timeout: 5000 });

  await optionsPage.close();
}

/**
 * Get extension ID from service worker
 */
async function getExtensionId(context: BrowserContext): Promise<string> {
  // Navigate to extensions page and find our extension
  const page = await context.newPage();
  await page.goto('chrome://extensions');

  // Enable developer mode to see extension IDs
  await page.evaluate(() => {
    const devModeToggle = document.querySelector('extensions-manager')
      ?.shadowRoot?.querySelector('extensions-toolbar')
      ?.shadowRoot?.querySelector('#devMode');
    if (devModeToggle) (devModeToggle as HTMLElement).click();
  });

  await page.waitForTimeout(500);

  // Find LeetLoop extension ID
  const extensionId = await page.evaluate(() => {
    const manager = document.querySelector('extensions-manager');
    const itemList = manager?.shadowRoot?.querySelector('extensions-item-list');
    const items = itemList?.shadowRoot?.querySelectorAll('extensions-item');

    for (const item of items || []) {
      const name = item.shadowRoot?.querySelector('#name')?.textContent;
      if (name?.includes('LeetLoop')) {
        const id = item.getAttribute('id');
        return id;
      }
    }
    return null;
  });

  await page.close();

  if (!extensionId) {
    throw new Error('Could not find LeetLoop extension ID');
  }

  return extensionId;
}

/**
 * Wait for user to complete LeetCode login
 */
async function waitForLeetCodeLogin(page: any): Promise<void> {
  console.log('\n===========================================');
  console.log('HUMAN ACTION REQUIRED: Please log in to LeetCode');
  console.log('===========================================\n');

  // Wait for the user to be logged in (nav shows username or premium badge)
  await page.waitForSelector('[class*="nav-user"], [class*="premium"]', {
    timeout: 120000, // 2 minutes to login
  });

  console.log('Login detected! Continuing test...\n');
}

test.describe('LeetLoop Extension', () => {
  let context: BrowserContext;

  test.beforeAll(async () => {
    // Build extension first
    console.log('Building extension...');
    const { execSync } = await import('child_process');
    execSync('pnpm build', { cwd: path.resolve(__dirname, '..'), stdio: 'inherit' });
  });

  test.beforeEach(async () => {
    context = await launchBrowserWithExtension();
  });

  test.afterEach(async () => {
    await context?.close();
  });

  test('should capture accepted submission', async () => {
    // Configure extension with Supabase
    await verifyExtensionConfigured(context);

    // Get initial submission count
    const initialCount = await getSubmissionCount();
    console.log(`Initial submissions in DB: ${initialCount}`);

    // Navigate to LeetCode
    const page = await context.newPage();
    await page.goto('https://leetcode.com/accounts/login/');

    // Wait for human to login
    await waitForLeetCodeLogin(page);

    // Navigate to a simple problem
    await page.goto('https://leetcode.com/problems/add-two-integers/');
    await page.waitForLoadState('networkidle');

    // Wait for code editor to load
    await page.waitForSelector('[class*="editor"]', { timeout: 10000 });

    console.log('\n===========================================');
    console.log('HUMAN ACTION REQUIRED: Submit a solution');
    console.log('(You can submit any code - pass or fail)');
    console.log('===========================================\n');

    // Wait for submission result (either success or failure modal/message)
    await page.waitForSelector('[class*="result"], [class*="success"], [class*="error"], [class*="accepted"], [class*="wrong"]', {
      timeout: 120000,
    });

    // Wait a bit for sync to complete
    await page.waitForTimeout(3000);

    // Check Supabase for new submission
    const finalCount = await getSubmissionCount();
    console.log(`Final submissions in DB: ${finalCount}`);

    expect(finalCount).toBeGreaterThan(initialCount);

    // Verify the submission details
    const submissions = await getSubmissions(1);
    expect(submissions[0].problem_slug).toBe('add-two-integers');
  });

  test('should capture failed submission (TLE/Wrong Answer)', async () => {
    await verifyExtensionConfigured(context);

    const initialCount = await getSubmissionCount();

    const page = await context.newPage();
    await page.goto('https://leetcode.com/accounts/login/');
    await waitForLeetCodeLogin(page);

    // Go to a problem where we can easily trigger TLE
    await page.goto('https://leetcode.com/problems/two-sum/');
    await page.waitForLoadState('networkidle');

    console.log('\n===========================================');
    console.log('HUMAN ACTION REQUIRED: Submit a FAILING solution');
    console.log('(Submit incorrect code or infinite loop for TLE)');
    console.log('===========================================\n');

    // Wait for failure result
    await page.waitForSelector('[class*="result"], [class*="wrong"], [class*="error"], [class*="time"]', {
      timeout: 120000,
    });

    await page.waitForTimeout(3000);

    const finalCount = await getSubmissionCount();
    expect(finalCount).toBeGreaterThan(initialCount);

    // Verify failure was captured
    const submissions = await getSubmissions(1);
    expect(['Wrong Answer', 'Time Limit Exceeded', 'Runtime Error', 'Compile Error']).toContain(
      submissions[0].status
    );
  });
});

test.describe('Extension Popup', () => {
  let context: BrowserContext;

  test.beforeEach(async () => {
    context = await launchBrowserWithExtension();
  });

  test.afterEach(async () => {
    await context?.close();
  });

  test('should show recent submissions in popup', async () => {
    const extensionId = await getExtensionId(context);

    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup/popup.html`);

    // Check popup loads
    await expect(page.locator('h1')).toContainText('LeetLoop');

    // Stats should be visible
    await expect(page.locator('#today-total')).toBeVisible();
    await expect(page.locator('#today-accepted')).toBeVisible();
    await expect(page.locator('#today-failed')).toBeVisible();
  });
});
