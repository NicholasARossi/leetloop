import * as esbuild from 'esbuild';
import { copyFileSync, mkdirSync, existsSync, readFileSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { config } from 'dotenv';
import { execSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const isWatch = process.argv.includes('--watch');
const skipValidation = process.argv.includes('--skip-url-validation');

// Load environment variables from .env file
// Check extension's .env first, then fall back to web's .env.local
const envPaths = [
  join(__dirname, '.env'),
  join(__dirname, '.env.local'),
  join(__dirname, '..', 'web', '.env.local'),
  join(__dirname, '..', 'web', '.env'),
];

let envLoaded = false;
for (const envPath of envPaths) {
  if (existsSync(envPath)) {
    config({ path: envPath });
    console.log(`Loaded env from ${envPath}`);
    envLoaded = true;
    break;
  }
}

if (!envLoaded) {
  console.warn('No .env file found, using placeholder values');
}

// Get API URL for routing submissions through backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || '';

// Get Web App URL for auth redirects and web-bridge content script
const WEB_APP_URL = process.env.WEB_APP_URL || process.env.NEXT_PUBLIC_WEB_APP_URL || 'http://localhost:3001';

console.log(`API URL: ${API_URL || 'not set'}`);
console.log(`Web App URL: ${WEB_APP_URL}`);

// Validate Cloud Run URLs if they look like production URLs
async function validateCloudRunUrls() {
  const isCloudRunUrl = (url) => url.includes('.run.app');

  // Extract the service name from a Cloud Run URL (e.g., "leetloop-api" from "https://leetloop-api-xxx.run.app")
  const getServiceName = (url) => {
    const match = url.match(/https?:\/\/([^-]+(?:-[^-]+)*?)-[a-z0-9]+-[a-z]{2}\.a\.run\.app/) ||
                  url.match(/https?:\/\/([^-]+(?:-[^-]+)*?)-\d+\.[^.]+\.run\.app/);
    return match ? match[1] : null;
  };

  if (!isCloudRunUrl(API_URL) && !isCloudRunUrl(WEB_APP_URL)) {
    console.log('Using localhost URLs, skipping Cloud Run validation');
    return;
  }

  if (skipValidation) {
    console.log('Skipping URL validation (--skip-url-validation flag)');
    return;
  }

  console.log('\nValidating Cloud Run URLs...');

  try {
    // Verify the URLs are reachable (simple health check)
    let hasWarning = false;

    if (isCloudRunUrl(API_URL)) {
      try {
        execSync(`curl -sf "${API_URL}/health" > /dev/null 2>&1`, { timeout: 5000 });
        console.log(`✓ API URL is reachable: ${API_URL}`);
      } catch {
        console.warn(`\n⚠️  WARNING: API_URL is not reachable!`);
        console.warn(`   URL: ${API_URL}`);
        console.warn(`   The service may not be deployed or URL may be wrong.\n`);
        hasWarning = true;
      }
    }

    if (isCloudRunUrl(WEB_APP_URL)) {
      try {
        execSync(`curl -sf "${WEB_APP_URL}" -o /dev/null 2>&1`, { timeout: 5000 });
        console.log(`✓ Web App URL is reachable: ${WEB_APP_URL}`);
      } catch {
        console.warn(`\n⚠️  WARNING: WEB_APP_URL is not reachable!`);
        console.warn(`   URL: ${WEB_APP_URL}`);
        console.warn(`   The service may not be deployed or URL may be wrong.\n`);
        hasWarning = true;
      }
    }

    if (hasWarning) {
      console.warn('\n🚨 URL validation failed! Auth sync between web app and extension may fail.');
      console.warn('   Run: make sync-urls  (to update .env with current Cloud Run URLs)\n');
    }
  } catch (err) {
    // Validation failed - just log and continue
    console.log('Could not validate Cloud Run URLs:', err.message);
  }
}

await validateCloudRunUrls();

// Ensure dist directory exists
if (!existsSync(join(__dirname, 'dist'))) {
  mkdirSync(join(__dirname, 'dist'), { recursive: true });
}

// Copy static files
const staticFiles = [
  'src/popup/popup.html',
  'src/popup/popup.css',
  'src/options/options.html',
  'src/options/options.css',
];

for (const file of staticFiles) {
  const src = join(__dirname, file);
  const dest = join(__dirname, 'dist', file.replace('src/', ''));
  const destDir = dirname(dest);
  if (!existsSync(destDir)) {
    mkdirSync(destDir, { recursive: true });
  }
  if (existsSync(src)) {
    copyFileSync(src, dest);
    console.log(`Copied ${file} -> dist/`);
  }
}

// Process manifest.json - replace localhost URLs with WEB_APP_URL
const manifestSrc = join(__dirname, 'manifest.json');
const manifestDest = join(__dirname, 'dist', 'manifest.json');
let manifestContent = readFileSync(manifestSrc, 'utf-8');
manifestContent = manifestContent.replace(/http:\/\/localhost:3001/g, WEB_APP_URL.replace(/\/$/, ''));
writeFileSync(manifestDest, manifestContent);
console.log(`Processed manifest.json -> dist/ (WEB_APP_URL: ${WEB_APP_URL})`);

// Build configuration
const buildOptions = {
  entryPoints: [
    'src/interceptor.ts',
    'src/content.ts',
    'src/background.ts',
    'src/popup/popup.ts',
    'src/options/options.ts',
    'src/web-bridge.ts',
  ],
  bundle: true,
  outdir: 'dist',
  format: 'esm',
  target: 'chrome110',
  sourcemap: true,
  minify: !isWatch,
  define: {
    '__API_URL__': JSON.stringify(API_URL),
    '__WEB_APP_URL__': JSON.stringify(WEB_APP_URL.replace(/\/$/, '')),
  },
};

if (isWatch) {
  const ctx = await esbuild.context(buildOptions);
  await ctx.watch();
  console.log('Watching for changes...');
} else {
  await esbuild.build(buildOptions);
  console.log('Build complete!');
}
