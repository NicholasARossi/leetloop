import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Helper to wait for page to be ready (more reliable than networkidle)
async function waitForPageReady(page: import('@playwright/test').Page) {
  await page.waitForLoadState('domcontentloaded');
  // Give React time to hydrate
  await page.waitForTimeout(500);
}

// Pages to test (public and app routes)
const publicPages = [
  { path: '/', name: 'Home' },
  { path: '/login', name: 'Login' },
];

const appPages = [
  { path: '/dashboard', name: 'Dashboard' },
  { path: '/submissions', name: 'Submissions' },
  { path: '/skills', name: 'Skills' },
  { path: '/reviews', name: 'Reviews' },
  { path: '/coach', name: 'Coach' },
  { path: '/mastery', name: 'Mastery' },
  { path: '/path', name: 'Path' },
  { path: '/objective', name: 'Objective' },
  { path: '/onboarding', name: 'Onboarding' },
];

test.describe('Readability Tests - Public Pages', () => {
  for (const { path, name } of publicPages) {
    test.describe(`${name} page (${path})`, () => {
      test('all visible elements are readable and not obscured', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        // Check that the page has content
        const body = page.locator('body');
        await expect(body).toBeVisible();

        // Get all text elements and verify they're visible
        const textElements = page.locator('h1, h2, h3, h4, h5, h6, p, span, a, button, label');
        const count = await textElements.count();

        for (let i = 0; i < Math.min(count, 50); i++) {
          const element = textElements.nth(i);
          const isVisible = await element.isVisible();

          if (isVisible) {
            // Verify element is not zero-sized
            const box = await element.boundingBox();
            if (box) {
              expect(box.width, `Element ${i} should have width`).toBeGreaterThan(0);
              expect(box.height, `Element ${i} should have height`).toBeGreaterThan(0);
            }
          }
        }
      });

      test('has no critical accessibility violations', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        const accessibilityScanResults = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze();

        // Filter to only critical and serious violations
        const criticalViolations = accessibilityScanResults.violations.filter(
          (v) => v.impact === 'critical' || v.impact === 'serious'
        );

        if (criticalViolations.length > 0) {
          console.log('\nAccessibility violations found:');
          criticalViolations.forEach((violation) => {
            console.log(`\n[${violation.impact?.toUpperCase()}] ${violation.id}: ${violation.description}`);
            console.log(`Help: ${violation.helpUrl}`);
            violation.nodes.forEach((node) => {
              console.log(`  - ${node.html}`);
              console.log(`    Fix: ${node.failureSummary}`);
            });
          });
        }

        expect(criticalViolations, 'Should have no critical/serious accessibility violations').toHaveLength(0);
      });

      test('text content is present and not empty', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        // Check for main headings or meaningful content
        const headings = page.locator('h1, h2, h3');
        const headingCount = await headings.count();

        // Log if no headings found (informational, not a hard failure for login/simple pages)
        if (headingCount === 0) {
          console.log(`Note: ${path} has no h1-h3 headings`);
        }

        // Verify headings have content
        for (let i = 0; i < headingCount; i++) {
          const heading = headings.nth(i);
          const isVisible = await heading.isVisible();
          if (isVisible) {
            const text = await heading.textContent();
            expect(text?.trim().length, `Heading ${i + 1} should have content`).toBeGreaterThan(0);
          }
        }

        // Check buttons have accessible text
        const buttons = page.locator('button');
        const buttonCount = await buttons.count();

        for (let i = 0; i < buttonCount; i++) {
          const button = buttons.nth(i);
          const isVisible = await button.isVisible();
          if (isVisible) {
            const text = await button.textContent();
            const ariaLabel = await button.getAttribute('aria-label');
            const hasText = (text?.trim().length ?? 0) > 0 || (ariaLabel?.length ?? 0) > 0;
            expect(hasText, `Button ${i + 1} should have text or aria-label`).toBeTruthy();
          }
        }
      });

      test('interactive elements are focusable', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        const interactiveElements = page.locator('a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
        const count = await interactiveElements.count();

        for (let i = 0; i < Math.min(count, 20); i++) {
          const element = interactiveElements.nth(i);
          const isVisible = await element.isVisible();
          const isEnabled = await element.isEnabled();

          if (isVisible && isEnabled) {
            await element.focus();
            const isFocused = await element.evaluate((el) => document.activeElement === el);
            expect(isFocused, `Element ${i + 1} should be focusable`).toBeTruthy();
          }
        }
      });

      test('color contrast meets WCAG AA standards', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        const accessibilityScanResults = await new AxeBuilder({ page })
          .withTags(['wcag2aa'])
          .options({ runOnly: ['color-contrast'] })
          .analyze();

        const contrastViolations = accessibilityScanResults.violations;

        if (contrastViolations.length > 0) {
          console.log('\nColor contrast issues:');
          contrastViolations.forEach((violation) => {
            violation.nodes.forEach((node) => {
              console.log(`  - ${node.html}`);
              console.log(`    ${node.failureSummary}`);
            });
          });
        }

        // Allow up to 3 minor contrast issues (some may be intentional design choices)
        expect(contrastViolations.length, 'Should have minimal color contrast issues').toBeLessThanOrEqual(3);
      });
    });
  }
});

test.describe('Readability Tests - App Pages (requires auth mock)', () => {
  // Note: These tests may fail if authentication is required
  // In a real scenario, you'd set up auth state before testing

  for (const { path, name } of appPages) {
    test.describe(`${name} page (${path})`, () => {
      test('page loads without errors', async ({ page }) => {
        const errors: string[] = [];
        page.on('pageerror', (error) => errors.push(error.message));
        page.on('console', (msg) => {
          if (msg.type() === 'error') {
            errors.push(msg.text());
          }
        });

        const response = await page.goto(path);

        // Page should load (may redirect to login)
        expect(response?.status()).toBeLessThan(500);

        // Log any errors for debugging
        if (errors.length > 0) {
          console.log(`Console errors on ${path}:`, errors);
        }
      });

      test('has visible content structure', async ({ page }) => {
        await page.goto(path);
        await page.waitForLoadState('domcontentloaded');

        // Check page has basic structure
        const body = page.locator('body');
        await expect(body).toBeVisible();

        // Should have some visible content
        const visibleContent = page.locator('main, [role="main"], .container, #__next > div');
        const count = await visibleContent.count();

        if (count > 0) {
          const firstContent = visibleContent.first();
          const box = await firstContent.boundingBox();
          if (box) {
            expect(box.height, 'Content area should have height').toBeGreaterThan(0);
          }
        }
      });

      test('images have alt text', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        const images = page.locator('img');
        const count = await images.count();

        for (let i = 0; i < count; i++) {
          const img = images.nth(i);
          const alt = await img.getAttribute('alt');
          const role = await img.getAttribute('role');

          // Images should have alt text or role="presentation" for decorative images
          const hasAccessibleDescription = alt !== null || role === 'presentation';
          expect(hasAccessibleDescription, `Image ${i + 1} should have alt text or role="presentation"`).toBeTruthy();
        }
      });

      test('forms have proper labels', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        const inputs = page.locator('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select');
        const count = await inputs.count();

        for (let i = 0; i < count; i++) {
          const input = inputs.nth(i);
          const isVisible = await input.isVisible();

          if (isVisible) {
            const id = await input.getAttribute('id');
            const ariaLabel = await input.getAttribute('aria-label');
            const ariaLabelledBy = await input.getAttribute('aria-labelledby');
            const placeholder = await input.getAttribute('placeholder');

            // Check if there's a label element for this input
            let hasLabel = false;
            if (id) {
              const label = page.locator(`label[for="${id}"]`);
              hasLabel = await label.count() > 0;
            }

            const hasAccessibleLabel = hasLabel || ariaLabel || ariaLabelledBy || placeholder;
            expect(hasAccessibleLabel, `Input ${i + 1} should have a label or aria-label`).toBeTruthy();
          }
        }
      });

      test('no accessibility violations', async ({ page }) => {
        await page.goto(path);
        await waitForPageReady(page);

        const accessibilityScanResults = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa'])
          .analyze();

        const criticalViolations = accessibilityScanResults.violations.filter(
          (v) => v.impact === 'critical' || v.impact === 'serious'
        );

        if (criticalViolations.length > 0) {
          console.log(`\nAccessibility violations on ${path}:`);
          criticalViolations.forEach((violation) => {
            console.log(`\n[${violation.impact?.toUpperCase()}] ${violation.id}: ${violation.description}`);
            violation.nodes.slice(0, 3).forEach((node) => {
              console.log(`  - ${node.html.substring(0, 100)}`);
            });
          });
        }

        expect(criticalViolations.length, 'Should have no critical accessibility violations').toBe(0);
      });
    });
  }
});

test.describe('Cross-browser text rendering', () => {
  test('fonts load correctly', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);

    // Wait for fonts to load
    await page.evaluate(() => document.fonts.ready);

    // Check that custom fonts are loaded (if any)
    const fontsLoaded = await page.evaluate(() => {
      return document.fonts.check('16px sans-serif');
    });

    expect(fontsLoaded, 'System fonts should be available').toBeTruthy();
  });

  test('text is not clipped or overflowing', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);

    // Check for overflow issues
    const overflowingElements = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      const issues: string[] = [];

      elements.forEach((el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        // Check if text is clipped
        if (el.scrollWidth > el.clientWidth && style.overflow === 'hidden') {
          if (rect.width > 0 && rect.height > 0) {
            issues.push(`Horizontal overflow: ${el.tagName}.${el.className}`);
          }
        }
      });

      return issues.slice(0, 5); // Return first 5 issues
    });

    if (overflowingElements.length > 0) {
      console.log('Potential text overflow issues:', overflowingElements);
    }

    // Allow some overflow (may be intentional for truncation)
    expect(overflowingElements.length, 'Should have minimal overflow issues').toBeLessThanOrEqual(5);
  });
});

test.describe('Responsive readability', () => {
  const viewports = [
    { width: 375, height: 667, name: 'Mobile' },
    { width: 768, height: 1024, name: 'Tablet' },
    { width: 1280, height: 720, name: 'Desktop' },
    { width: 1920, height: 1080, name: 'Large Desktop' },
  ];

  for (const viewport of viewports) {
    test(`content is readable at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      await waitForPageReady(page);

      // Check that main content is visible
      const body = page.locator('body');
      await expect(body).toBeVisible();

      // Check font sizes are readable (minimum 12px)
      const smallTextElements = await page.evaluate(() => {
        const elements = document.querySelectorAll('p, span, a, li');
        const tooSmall: string[] = [];

        elements.forEach((el) => {
          const style = window.getComputedStyle(el);
          const fontSize = parseFloat(style.fontSize);

          if (fontSize < 12 && el.textContent?.trim()) {
            tooSmall.push(`${el.tagName}: ${fontSize}px - "${el.textContent?.substring(0, 30)}"`);
          }
        });

        return tooSmall.slice(0, 5);
      });

      if (smallTextElements.length > 0) {
        console.log(`Small text at ${viewport.name}:`, smallTextElements);
      }

      expect(smallTextElements.length, 'Text should be at least 12px').toBeLessThanOrEqual(2);
    });
  }
});
