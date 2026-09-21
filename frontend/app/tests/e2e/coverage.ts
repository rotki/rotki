import type { Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

const DIST_DIR = join(import.meta.dirname, '../../dist');

/** Raw V8 coverage waiting for `scripts/e2e-coverage-report.ts`, which reads it from here. */
const V8_COVERAGE_DIR = join(import.meta.dirname, '.v8-coverage');

/** How long a responsive page needs to hand over its coverage; well under the test timeout. */
const STOP_TIMEOUT_MS = 15_000;

/**
 * Check if coverage collection is enabled via environment variable.
 */
export function isCoverageEnabled(): boolean {
  return process.env.E2E_COVERAGE === 'true';
}

/**
 * Finds the bundle chunk in `dist/` that the preview server answered `url` with.
 *
 * @remarks
 * Only the preview bundle is covered: the report reads each chunk and its source map from disk.
 * The Vite dev server that interactive runs use serves modules that exist only as responses, so
 * their coverage is dropped here.
 */
function bundleChunkOf(url: string): string | undefined {
  const { hostname, pathname } = new URL(url);
  if (hostname !== 'localhost' && hostname !== '127.0.0.1')
    return undefined;

  const chunk = join(DIST_DIR, decodeURIComponent(pathname));
  return chunk.endsWith('.js') && existsSync(chunk) ? chunk : undefined;
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
 * Stop V8 coverage collection and save it for the report.
 *
 * @remarks
 * Coverage files accumulate across tests and are converted to lcov by the
 * `test:e2e:coverage:report` script after all tests complete.
 *
 * Stopping needs the page to answer, so a test that leaves its tab frozen would otherwise only
 * fail on the teardown timeout, with nothing pointing at the cause.
 */
export async function stopCoverage(page: Page): Promise<void> {
  if (!isCoverageEnabled())
    return;

  let timer: ReturnType<typeof setTimeout> | undefined;
  const unresponsive = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`Could not collect coverage: the page at ${page.url()} stopped responding`));
    }, STOP_TIMEOUT_MS);
  });
  const coverage = await Promise.race([page.coverage.stopJSCoverage(), unresponsive]).finally(() => {
    clearTimeout(timer);
  });

  const result = coverage.flatMap((entry) => {
    const chunk = bundleChunkOf(entry.url);
    return chunk ? [{ scriptId: '0', url: pathToFileURL(chunk).href, functions: entry.functions }] : [];
  });

  if (result.length === 0)
    return;

  mkdirSync(V8_COVERAGE_DIR, { recursive: true });
  writeFileSync(join(V8_COVERAGE_DIR, `coverage-${randomUUID()}.json`), JSON.stringify({ result }));
}
