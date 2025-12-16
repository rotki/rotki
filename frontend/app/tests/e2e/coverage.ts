import type { Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import process from 'node:process';

const APP_ROOT = join(import.meta.dirname, '../..');
const V8_COVERAGE_DIR = join(import.meta.dirname, '.v8-coverage');

/**
 * Check if coverage collection is enabled via environment variable.
 */
export function isCoverageEnabled(): boolean {
  return process.env.E2E_COVERAGE === 'true';
}

/**
 * Paths to exclude from coverage (similar to istanbul ignore file).
 */
const EXCLUDED_PATHS = [
  '/src/main.ts',
  '/src/router/index.ts',
];

/**
 * Check if a filename looks like a bundled/hashed file (e.g., utils-D1WHamuv.js)
 */
function isBundledFile(pathname: string): boolean {
  // Bundled files have pattern: Name-[hash].js or Name-[hash].css
  // Hash is typically 8 alphanumeric characters
  return /^\/[^/]+-\w{8}\.(js|css)$/.test(pathname);
}

/**
 * Convert a URL from the dev/preview server to a local file path.
 * Dev server: http://localhost:8080/src/App.vue -> /absolute/path/to/src/App.vue
 * Preview (bundled): http://localhost:8080/utils-D1WHamuv.js -> /absolute/path/to/dist/utils-D1WHamuv.js
 */
function urlToFilePath(url: string): string | null {
  try {
    const parsed = new URL(url);
    // Only process localhost URLs
    if (!parsed.hostname.includes('localhost'))
      return null;

    const pathname = parsed.pathname;

    // Skip node_modules and vite internals
    if (pathname.includes('node_modules') || pathname.startsWith('/@'))
      return null;

    // Skip excluded paths
    if (EXCLUDED_PATHS.some(excluded => pathname.endsWith(excluded)))
      return null;

    // For bundled assets (production/preview), map to dist directory
    // c8 will use source maps to resolve back to original source files
    if (isBundledFile(pathname))
      return join(APP_ROOT, 'dist', pathname);

    // For dev server, convert to source path
    return join(APP_ROOT, pathname);
  }
  catch {
    return null;
  }
}

/**
 * Start V8 coverage collection on a Playwright page.
 * Must be called before navigating to any pages.
 */
export async function startCoverage(page: Page): Promise<void> {
  if (!isCoverageEnabled())
    return;

  await page.coverage.startJSCoverage({
    resetOnNavigation: false,
  });
}

/**
 * Stop V8 coverage collection and save to temp directory.
 * Coverage files accumulate across tests and are converted to lcov
 * by running the test:e2e:coverage:report script after all tests complete.
 */
export async function stopCoverage(page: Page): Promise<void> {
  if (!isCoverageEnabled())
    return;

  const coverage = await page.coverage.stopJSCoverage();

  if (coverage.length === 0)
    return;

  // Ensure coverage directory exists
  if (!existsSync(V8_COVERAGE_DIR)) {
    mkdirSync(V8_COVERAGE_DIR, { recursive: true });
  }

  // Convert URLs to file paths and filter out non-source files
  const v8CoverageData = coverage
    .map((entry) => {
      const filePath = urlToFilePath(entry.url);
      if (!filePath)
        return null;

      return {
        scriptId: '0',
        url: `file://${filePath}`,
        functions: entry.functions,
      };
    })
    .filter(Boolean);

  if (v8CoverageData.length === 0)
    return;

  // Write V8 coverage data
  const coverageFile = join(V8_COVERAGE_DIR, `coverage-${randomUUID()}.json`);
  writeFileSync(coverageFile, JSON.stringify({ result: v8CoverageData }));
}
