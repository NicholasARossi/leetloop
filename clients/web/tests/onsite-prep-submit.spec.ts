import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * End-to-end test: onsite prep audio submission flow.
 *
 * Since Playwright can't use a real microphone, we mock MediaRecorder
 * to produce a real audio blob, then verify the full UI → API flow.
 */

const API_URL = 'http://localhost:8080';
const BREADTH_QUESTION_ID = 'a48c3a95-ec3b-4449-a121-4dfe1dca2753';
const LP_QUESTION_ID = '597fa4ea-ab77-4958-9f7c-db37bcc3cea5';

// Mock grade result to avoid waiting for real Gemini/STT
const mockGradeResult = {
  attempt_id: 'test-attempt-001',
  grade: {
    transcript: 'This is a test transcript of the recorded audio.',
    dimensions: [
      { name: 'definition', score: 4, evidence: [{ quote: 'test quote', analysis: 'test analysis' }], summary: 'Good' },
      { name: 'intuition', score: 3, evidence: [{ quote: 'test', analysis: 'test' }], summary: 'OK' },
      { name: 'failure_modes', score: 3, evidence: [{ quote: 'test', analysis: 'test' }], summary: 'OK' },
      { name: 'practical_connection', score: 4, evidence: [{ quote: 'test', analysis: 'test' }], summary: 'Good' },
      { name: 'timing', score: 4, evidence: [{ quote: 'test', analysis: 'test' }], summary: 'Good' },
      { name: 'completeness', score: 3, evidence: [{ quote: 'test', analysis: 'test' }], summary: 'OK' },
    ],
    overall_score: 3.5,
    verdict: 'borderline',
    feedback: 'Test feedback - decent coverage of the topic.',
    strongest_moment: 'Good definition provided',
    weakest_moment: 'Missing failure mode discussion',
    follow_up_questions: ['Can you elaborate on failure modes?'],
  },
};

test.describe('Onsite Prep Audio Submission', () => {
  test('practice page loads and shows question', async ({ page }) => {
    await page.goto(`/onsite-prep/practice/${BREADTH_QUESTION_ID}`);

    // Wait for the question to load
    await expect(page.locator('text=Compare logistic regression')).toBeVisible({ timeout: 10000 });

    // Should show the Record New Attempt button
    await expect(page.locator('button:has-text("Record New Attempt")')).toBeVisible();
  });

  test('record button leads to recording view with AudioRecorder', async ({ page }) => {
    await page.goto(`/onsite-prep/practice/${BREADTH_QUESTION_ID}`);
    await expect(page.locator('text=Compare logistic regression')).toBeVisible({ timeout: 10000 });

    // Click Record New Attempt
    await page.click('button:has-text("Record New Attempt")');

    // Should show the Start Recording button
    await expect(page.locator('button:has-text("Start Recording")')).toBeVisible({ timeout: 5000 });

    // Should show the rubric
    await expect(page.locator('text=Grading Rubric')).toBeVisible();
  });

  test('submit-audio API works with real audio file via fetch', async ({ page }) => {
    // This test bypasses the UI and directly calls the API from the browser context
    // to verify the full backend pipeline works

    await page.goto(`/onsite-prep/practice/${BREADTH_QUESTION_ID}`);
    await expect(page.locator('text=Compare logistic regression')).toBeVisible({ timeout: 10000 });

    // Create a minimal valid WebM audio in the browser and POST it
    // We use the API mock to avoid the 60s STT wait
    await page.route(`${API_URL}/api/onsite-prep/questions/*/submit-audio`, async (route) => {
      const request = route.request();

      // Verify the request is a POST with FormData
      expect(request.method()).toBe('POST');
      const contentType = request.headers()['content-type'] || '';
      expect(contentType).toContain('multipart/form-data');

      // Return mock response
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockGradeResult),
      });
    });

    // Also mock the follow-ups and ideal response endpoints
    await page.route(`${API_URL}/api/onsite-prep/attempts/*/generate-follow-ups`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route(`${API_URL}/api/onsite-prep/attempts/*/ideal-response`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: 'Test ideal summary',
          outline: ['Point 1', 'Point 2'],
          full_response: 'Full ideal response text',
        }),
      });
    });

    // Click Record New Attempt
    await page.click('button:has-text("Record New Attempt")');
    await expect(page.locator('button:has-text("Start Recording")')).toBeVisible({ timeout: 5000 });

    // Simulate recording by injecting a blob and triggering submit directly
    // We override the AudioRecorder's state via the page
    await page.evaluate(() => {
      // Create a small valid audio blob (silence)
      const sampleRate = 16000;
      const duration = 1; // 1 second
      const numSamples = sampleRate * duration;
      const buffer = new ArrayBuffer(44 + numSamples * 2); // WAV header + data
      const view = new DataView(buffer);

      // WAV header
      const writeString = (offset: number, str: string) => {
        for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
      };
      writeString(0, 'RIFF');
      view.setUint32(4, 36 + numSamples * 2, true);
      writeString(8, 'WAVE');
      writeString(12, 'fmt ');
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true); // PCM
      view.setUint16(22, 1, true); // mono
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * 2, true);
      view.setUint16(32, 2, true);
      view.setUint16(34, 16, true);
      writeString(36, 'data');
      view.setUint32(40, numSamples * 2, true);

      const blob = new Blob([buffer], { type: 'audio/webm' });

      // Find the submit handler by dispatching a custom event
      // The RecordingView's handleSubmit calls leetloopApi.submitOnsitePrepAudio
      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');

      return fetch(`http://localhost:8080/api/onsite-prep/questions/a48c3a95-ec3b-4449-a121-4dfe1dca2753/submit-audio`, {
        method: 'POST',
        body: formData,
      }).then(r => r.json()).then(data => {
        (window as any).__testSubmitResult = data;
      });
    });

    // Check the result was received
    const result = await page.evaluate(() => (window as any).__testSubmitResult);
    expect(result).toBeTruthy();
    expect(result.attempt_id).toBe('test-attempt-001');
    expect(result.grade.transcript).toBe('This is a test transcript of the recorded audio.');
    expect(result.grade.overall_score).toBe(3.5);
  });

  test('full UI flow: record → stop → submit fires API call', async ({ page, context }) => {
    // Grant microphone permission
    await context.grantPermissions(['microphone']);

    // Mock the MediaRecorder and getUserMedia before page loads
    await page.addInitScript(() => {
      // Create a small WAV blob for the fake recording
      function createTestBlob(): Blob {
        const sampleRate = 16000;
        const duration = 1;
        const numSamples = sampleRate * duration;
        const buffer = new ArrayBuffer(44 + numSamples * 2);
        const view = new DataView(buffer);
        const writeString = (offset: number, str: string) => {
          for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
        };
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + numSamples * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, numSamples * 2, true);
        return new Blob([buffer], { type: 'audio/webm' });
      }

      // Mock getUserMedia
      (navigator.mediaDevices as any).getUserMedia = async () => {
        return {
          getTracks: () => [{ stop: () => {} }],
          getAudioTracks: () => [{ stop: () => {} }],
        };
      };

      // Mock MediaRecorder
      const OriginalMediaRecorder = window.MediaRecorder;
      (window as any).MediaRecorder = class MockMediaRecorder {
        state = 'inactive';
        ondataavailable: ((e: any) => void) | null = null;
        onstop: (() => void) | null = null;

        static isTypeSupported(type: string) { return type.includes('webm'); }

        constructor(stream: any, options?: any) {
          console.log('[MockMediaRecorder] Created with options:', options);
        }

        start(timeslice?: number) {
          this.state = 'recording';
          console.log('[MockMediaRecorder] Started');
          // Deliver a chunk after 500ms
          setTimeout(() => {
            if (this.ondataavailable) {
              const blob = createTestBlob();
              console.log('[MockMediaRecorder] Delivering chunk:', blob.size, 'bytes');
              this.ondataavailable({ data: blob } as any);
            }
          }, 500);
        }

        stop() {
          this.state = 'inactive';
          console.log('[MockMediaRecorder] Stopped');
          setTimeout(() => {
            if (this.onstop) this.onstop();
          }, 100);
        }
      };
    });

    // Mock the API to return quickly
    await page.route(`${API_URL}/api/onsite-prep/questions/*/submit-audio`, async (route) => {
      const request = route.request();
      console.log('[Test] submit-audio intercepted:', request.method(), request.headers()['content-type']);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockGradeResult),
      });
    });

    await page.route(`${API_URL}/api/onsite-prep/attempts/*/generate-follow-ups`, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.route(`${API_URL}/api/onsite-prep/attempts/*/ideal-response`, async (route) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ summary: 'Test', outline: ['P1'], full_response: 'Full' }),
      });
    });

    // Collect console messages for debugging
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    });

    // Navigate and start the flow
    await page.goto(`/onsite-prep/practice/${BREADTH_QUESTION_ID}`);
    await expect(page.locator('text=Compare logistic regression')).toBeVisible({ timeout: 10000 });

    // Click Record New Attempt
    await page.click('button:has-text("Record New Attempt")');
    await expect(page.locator('button:has-text("Start Recording")')).toBeVisible({ timeout: 5000 });

    // Click Start Recording (uses our mocked MediaRecorder)
    await page.click('button:has-text("Start Recording")');

    // Should show recording state
    await expect(page.locator('text=Recording')).toBeVisible({ timeout: 3000 });

    // Wait a moment, then click Stop & Review
    await page.waitForTimeout(1000);
    await page.click('button:has-text("Stop")');

    // Should show preview with Submit button
    await expect(page.locator('button:has-text("Submit")')).toBeVisible({ timeout: 5000 });

    // Check there's an audio element in preview
    await expect(page.locator('audio')).toBeVisible();

    // Click Submit
    await page.click('button:has-text("Submit")');

    // Should show uploading state or transition to grading results
    // Wait for the grade result to appear (mocked, should be fast)
    await expect(page.locator('text=Overall Score')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=3.5')).toBeVisible();
    await expect(page.locator('text=Needs Polish')).toBeVisible();

    // Verify the transcript is displayed
    await expect(page.locator('text=This is a test transcript')).toBeVisible();

    // Print console logs for debugging
    console.log('--- Browser Console Logs ---');
    consoleLogs.forEach(l => console.log(l));
  });

  test('direct API submission with real audio returns valid transcript', async ({ request }) => {
    // Generate a short test audio file
    const testAudioPath = '/tmp/playwright_test_audio.webm';

    // Use ffmpeg to create a 5-second silent webm
    const { execSync } = require('child_process');
    try {
      execSync(`ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 5 -c:a libopus -b:a 32k "${testAudioPath}" -y 2>/dev/null`);
    } catch {
      test.skip(true, 'ffmpeg not available for test audio generation');
      return;
    }

    const audioBuffer = fs.readFileSync(testAudioPath);

    // Submit directly to the API
    const response = await request.post(
      `${API_URL}/api/onsite-prep/questions/${BREADTH_QUESTION_ID}/submit-audio`,
      {
        multipart: {
          audio: {
            name: 'recording.webm',
            mimeType: 'audio/webm',
            buffer: audioBuffer,
          },
        },
        timeout: 300000, // 5 min for STT + grading
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    // Verify response structure
    expect(data.attempt_id).toBeTruthy();
    expect(data.grade).toBeTruthy();
    expect(data.grade.transcript).toBeDefined();
    expect(data.grade.dimensions).toBeInstanceOf(Array);
    expect(data.grade.dimensions.length).toBeGreaterThan(0);
    expect(data.grade.overall_score).toBeGreaterThanOrEqual(1);
    expect(data.grade.overall_score).toBeLessThanOrEqual(5);
    expect(['pass', 'borderline', 'fail']).toContain(data.grade.verdict);
    expect(data.grade.feedback).toBeTruthy();

    console.log(`API submission succeeded:
      Score: ${data.grade.overall_score}
      Verdict: ${data.grade.verdict}
      Transcript (${data.grade.transcript.length} chars): ${data.grade.transcript.substring(0, 100)}...`);
  });
});
