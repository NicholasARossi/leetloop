import { test, expect, type CDPSession } from '@playwright/test';

/**
 * Dashboard load timing diagnostic test.
 * Uses CDP to capture ALL network requests including cross-origin API calls.
 * Injects a real user ID so the dashboard makes all API calls (mission, progress, etc).
 */

// Real user ID with data and completed onboarding
const TEST_USER_ID = '155d3a9c-6d5a-49dc-870c-06c117314e1e';

const RUNS = 3;

test.setTimeout(120_000);
test.describe.configure({ mode: 'serial' });

for (let run = 1; run <= RUNS; run++) {
  test(`Dashboard load timing - run ${run}/${RUNS}`, async ({ page, context }) => {
    const requests = new Map<string, { url: string; start: number; duration?: number; status?: number }>();

    // Use CDP to capture all network requests (including cross-origin to :8080)
    const client: CDPSession = await context.newCDPSession(page);
    await client.send('Network.enable');

    client.on('Network.requestWillBeSent', (params: any) => {
      const url: string = params.request.url;
      if (url.includes('/api/')) {
        requests.set(params.requestId, {
          url,
          start: params.timestamp * 1000,
        });
      }
    });

    client.on('Network.responseReceived', (params: any) => {
      const req = requests.get(params.requestId);
      if (req) {
        req.duration = Math.round(params.timestamp * 1000 - req.start);
        req.status = params.response.status;
      }
    });

    client.on('Network.loadingFailed', (params: any) => {
      const req = requests.get(params.requestId);
      if (req) {
        req.duration = Math.round(params.timestamp * 1000 - req.start);
        req.status = 0;
      }
    });

    // Set the real user ID in localStorage BEFORE navigating
    // Navigate to a blank page first to set localStorage on the correct origin
    await page.goto('http://localhost:3001/login', { waitUntil: 'commit' });
    await page.evaluate((userId) => {
      localStorage.setItem('leetloop_user_id', userId);
    }, TEST_USER_ID);

    // Now navigate to dashboard and time it
    const navStart = Date.now();
    await page.goto('/dashboard', { waitUntil: 'commit' });

    // Wait for dashboard content to appear (skeleton replaced by real content)
    let contentFound = false;
    try {
      await page.waitForFunction(
        () => {
          const body = document.body?.textContent || '';
          return (
            body.includes('Your Daily Mission') ||
            body.includes('Failed to load mission') ||
            body.includes('No mission data')
          );
        },
        { timeout: 90_000, polling: 500 }
      );
      contentFound = true;
    } catch {
      // timed out
    }

    const totalTime = Date.now() - navStart;
    const finalUrl = page.url();

    // Detect page state
    const pageState = await page.evaluate(() => {
      const body = document.body?.textContent || '';
      if (body.includes('Your Daily Mission')) return 'Dashboard loaded';
      if (body.includes('Failed to load mission')) return 'Error state';
      if (body.includes('No mission data')) return 'Empty mission';
      if (body.includes('What are you preparing for')) return 'Onboarding redirect';
      const h1 = document.querySelector('h1');
      return `Other: ${h1?.textContent || '(no heading)'}`;
    });

    // Categorize captured requests
    const byLabel: Record<string, { url: string; duration?: number; status?: number }> = {};
    for (const [, req] of requests) {
      let label: string;
      if (/\/api\/onboarding\//.test(req.url)) label = 'onboarding';
      else if (/\/api\/mission\/(?!.*regenerate)/.test(req.url)) label = 'mission';
      else if (/\/api\/system-design\/.*\/dashboard/.test(req.url)) label = 'system-design';
      else if (/\/api\/progress\//.test(req.url)) label = 'progress';
      else label = new URL(req.url).pathname;

      // Keep the longest duration if there are duplicate calls
      if (!byLabel[label] || (req.duration || 0) > (byLabel[label].duration || 0)) {
        byLabel[label] = { url: req.url, duration: req.duration, status: req.status };
      }
    }

    // Print results
    console.log(`\n${'='.repeat(60)}`);
    console.log(`  DASHBOARD TIMING - RUN ${run}/${RUNS}`);
    console.log(`${'='.repeat(60)}`);
    console.log(`  User ID:          ${TEST_USER_ID}`);
    console.log(`  Final URL:        ${finalUrl}`);
    console.log(`  Page state:       ${pageState}`);
    console.log(`  Content found:    ${contentFound}`);
    console.log(`  Total load time:  ${totalTime}ms`);
    console.log(`\n  API Call Timings:`);
    console.log(`  ${'─'.repeat(55)}`);

    const sorted = Object.entries(byLabel).sort(
      (a, b) => (b[1].duration || 0) - (a[1].duration || 0)
    );

    if (sorted.length === 0) {
      console.log(`  (no /api/ calls captured)`);
    }

    for (const [label, timing] of sorted) {
      const dur = timing.duration != null ? `${timing.duration}ms` : 'pending';
      const status = timing.status ?? '???';
      const bar = timing.duration
        ? '█'.repeat(Math.min(Math.ceil(timing.duration / 500), 30))
        : '';
      console.log(`  ${label.padEnd(22)} ${String(status).padEnd(5)} ${dur.padStart(9)}  ${bar}`);
    }

    // Summary
    const completed = sorted.filter(([, t]) => t.duration != null);
    if (completed.length > 0) {
      const slowest = completed[0];
      console.log(`\n  Slowest API call: ${slowest[0]} (${slowest[1].duration}ms)`);
    }
    console.log(`  Total page load:  ${totalTime}ms`);

    if (totalTime > 10000) {
      console.log(`  >> VERY SLOW (${(totalTime / 1000).toFixed(1)}s)`);
    } else if (totalTime > 5000) {
      console.log(`  >> SLOW (${(totalTime / 1000).toFixed(1)}s)`);
    } else if (totalTime > 3000) {
      console.log(`  >> MODERATE (${(totalTime / 1000).toFixed(1)}s)`);
    } else {
      console.log(`  >> OK (${(totalTime / 1000).toFixed(1)}s)`);
    }

    console.log(`${'='.repeat(60)}\n`);

    // Raw request dump
    if (requests.size > 0) {
      console.log('  All captured /api/ requests:');
      for (const [, req] of requests) {
        console.log(`    ${req.status ?? '???'} ${req.duration ?? '?'}ms  ${req.url}`);
      }
      console.log('');
    }

    expect(true).toBe(true);
    await client.detach();
  });
}
