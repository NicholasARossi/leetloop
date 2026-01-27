import * as esbuild from 'esbuild';
import { copyFileSync, mkdirSync, existsSync, readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { config } from 'dotenv';

const __dirname = dirname(fileURLToPath(import.meta.url));
const isWatch = process.argv.includes('--watch');

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

// Get Supabase config from environment
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '__SUPABASE_URL__';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || '__SUPABASE_ANON_KEY__';

// Get API URL for routing submissions through backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || '';

console.log(`Supabase URL: ${SUPABASE_URL ? SUPABASE_URL.substring(0, 30) + '...' : 'not set'}`);
console.log(`API URL: ${API_URL || 'not set (will use direct Supabase)'}`);

// Ensure dist directory exists
if (!existsSync(join(__dirname, 'dist'))) {
  mkdirSync(join(__dirname, 'dist'), { recursive: true });
}

// Copy static files
const staticFiles = [
  'manifest.json',
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
    '__SUPABASE_URL__': JSON.stringify(SUPABASE_URL),
    '__SUPABASE_ANON_KEY__': JSON.stringify(SUPABASE_ANON_KEY),
    '__API_URL__': JSON.stringify(API_URL),
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
