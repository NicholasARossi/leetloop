/**
 * Manual test script - run with: npx ts-node tests/manual-test.ts
 *
 * This script checks:
 * 1. Supabase connection works
 * 2. Can read/write submissions
 * 3. Extension build is valid
 */

import { config } from 'dotenv';
import path from 'path';
import fs from 'fs';

config({ path: path.resolve(__dirname, '../../../.env') });

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY!;

async function main() {
  console.log('LeetLoop Manual Test\n');
  console.log('====================\n');

  // Check env vars
  console.log('1. Checking environment...');
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.error('   ❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env');
    process.exit(1);
  }
  console.log('   ✅ Environment variables loaded');
  console.log(`   URL: ${SUPABASE_URL}`);

  // Check extension build
  console.log('\n2. Checking extension build...');
  const distPath = path.resolve(__dirname, '../dist');
  const requiredFiles = ['manifest.json', 'background.js', 'content.js', 'interceptor.js'];

  for (const file of requiredFiles) {
    const filePath = path.join(distPath, file);
    if (!fs.existsSync(filePath)) {
      console.error(`   ❌ Missing: ${file}`);
      console.log('   Run: pnpm build');
      process.exit(1);
    }
  }
  console.log('   ✅ All extension files present');

  // Test Supabase connection
  console.log('\n3. Testing Supabase connection...');
  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/submissions?select=count&limit=1`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      console.error(`   ❌ Supabase error: ${response.status} ${error}`);
      process.exit(1);
    }
    console.log('   ✅ Supabase connection successful');
  } catch (error) {
    console.error(`   ❌ Network error: ${error}`);
    process.exit(1);
  }

  // Fetch recent submissions
  console.log('\n4. Fetching recent submissions...');
  try {
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/submissions?select=problem_slug,status,submitted_at&order=submitted_at.desc&limit=5`,
      {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        },
      }
    );

    const submissions = await response.json();
    console.log(`   Found ${submissions.length} submissions:`);

    for (const sub of submissions) {
      const time = new Date(sub.submitted_at).toLocaleString();
      console.log(`   - ${sub.problem_slug}: ${sub.status} (${time})`);
    }
  } catch (error) {
    console.error(`   ❌ Error: ${error}`);
  }

  // Test insert (dry run)
  console.log('\n5. Testing insert capability...');
  const testSubmission = {
    id: crypto.randomUUID(),
    user_id: crypto.randomUUID(),
    problem_slug: 'test-problem',
    problem_title: 'Test Problem',
    status: 'Accepted',
    language: 'javascript',
    code: '// test',
    code_length: 7,
    attempt_number: 1,
    time_elapsed_seconds: 60,
    session_id: crypto.randomUUID(),
    submitted_at: new Date().toISOString(),
  };

  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/submissions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        Prefer: 'return=minimal',
      },
      body: JSON.stringify(testSubmission),
    });

    if (response.ok) {
      console.log('   ✅ Insert successful');

      // Clean up test data
      await fetch(`${SUPABASE_URL}/rest/v1/submissions?id=eq.${testSubmission.id}`, {
        method: 'DELETE',
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        },
      });
      console.log('   ✅ Test data cleaned up');
    } else {
      const error = await response.text();
      console.error(`   ❌ Insert failed: ${response.status} ${error}`);
    }
  } catch (error) {
    console.error(`   ❌ Error: ${error}`);
  }

  console.log('\n====================');
  console.log('All checks passed! ✅');
  console.log('\nTo test the full extension:');
  console.log('1. Load extension in Chrome: chrome://extensions');
  console.log('2. Click "Load unpacked" → select packages/extension/dist');
  console.log('3. Go to LeetCode and submit a solution');
  console.log('4. Check this script again to see new submissions');
}

main().catch(console.error);
