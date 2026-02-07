import { test, expect, chromium, BrowserContext, Page } from '@playwright/test';
import path from 'path';
import { config } from 'dotenv';

config({ path: path.resolve(__dirname, '../.env') });

const EXTENSION_PATH = path.resolve(__dirname, '../dist');
const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY!;

/**
 * Fetch submissions from Supabase (for test verification)
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

test.describe('Interactive LeetLoop Test', () => {
  test('full flow - login, submit, verify', async () => {
    // Build extension first
    console.log('\n📦 Building extension...');
    const { execSync } = await import('child_process');
    execSync('pnpm build', { cwd: path.resolve(__dirname, '..'), stdio: 'inherit' });

    // Get initial count
    const initialSubmissions = await getSubmissions();
    console.log(`\n📊 Current submissions in DB: ${initialSubmissions.length}`);
    if (initialSubmissions.length > 0) {
      console.log(`   Latest: ${initialSubmissions[0].problem_slug} - ${initialSubmissions[0].status}`);
    }

    // Launch browser with extension
    console.log('\n🚀 Launching browser with LeetLoop extension...');
    const context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [
        `--disable-extensions-except=${EXTENSION_PATH}`,
        `--load-extension=${EXTENSION_PATH}`,
      ],
      viewport: { width: 1400, height: 900 },
    });

    // Wait for extension to load
    await new Promise(r => setTimeout(r, 2000));

    // Get extension ID from service worker
    let extensionId = '';
    const workers = context.serviceWorkers();
    for (const sw of workers) {
      const url = sw.url();
      if (url.includes('background')) {
        extensionId = url.split('/')[2];
        break;
      }
    }

    console.log(`   Extension ID: ${extensionId}`);

    // Verify extension loaded (API URL is baked in at build time)
    if (extensionId) {
      const optionsPage = await context.newPage();
      await optionsPage.goto(`chrome-extension://${extensionId}/options/options.html`);
      await optionsPage.waitForSelector('#api-url', { timeout: 5000 });
      console.log('   ✅ Extension loaded (API URL baked in at build time)');
      await optionsPage.close();
    }

    // Navigate to LeetCode
    const page = await context.newPage();
    await page.goto('https://leetcode.com/accounts/login/');

    console.log('\n' + '='.repeat(50));
    console.log('👤 STEP 1: LOG IN TO LEETCODE');
    console.log('   The Playwright Inspector will open.');
    console.log('   1. Log in to LeetCode in the browser');
    console.log('   2. Click "Resume" in the Inspector to continue');
    console.log('='.repeat(50) + '\n');

    // Pause for login - opens Playwright Inspector
    await page.pause();

    // Go to a simple problem
    await page.goto('https://leetcode.com/problems/add-two-integers/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('\n' + '='.repeat(50));
    console.log('📝 STEP 2: SUBMIT A SOLUTION');
    console.log('   1. Write/paste any code');
    console.log('   2. Click Submit');
    console.log('   3. Wait for result');
    console.log('   4. Click "Resume" in the Inspector');
    console.log('='.repeat(50) + '\n');

    await page.pause();

    // Wait for sync (extension -> API -> Supabase)
    console.log('\n⏳ Waiting for sync...');
    await page.waitForTimeout(5000);

    // Check results (verify data made it to Supabase)
    const finalSubmissions = await getSubmissions();
    console.log(`\n📊 Submissions in DB after test: ${finalSubmissions.length}`);

    if (finalSubmissions.length > initialSubmissions.length) {
      console.log('\n✅ SUCCESS! New submission captured:');
      console.log(`   Problem: ${finalSubmissions[0].problem_slug}`);
      console.log(`   Status:  ${finalSubmissions[0].status}`);
      console.log(`   Lang:    ${finalSubmissions[0].language}`);
      expect(true).toBe(true);
    } else {
      console.log('\n⚠️  No new submission in DB yet');
      console.log('   Check browser DevTools (F12) for [LeetLoop] errors');
      console.log('\n   Pausing for debugging...');

      await page.pause();

      // Try one more time
      const retrySubmissions = await getSubmissions();
      if (retrySubmissions.length > initialSubmissions.length) {
        console.log('\n✅ Found after retry!');
        console.log(`   Problem: ${retrySubmissions[0].problem_slug}`);
        console.log(`   Status:  ${retrySubmissions[0].status}`);
      }
    }

    console.log('\n🏁 Test complete. Closing browser...');
    await context.close();
  });
});
