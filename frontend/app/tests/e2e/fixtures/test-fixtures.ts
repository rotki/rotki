import { type APIRequestContext, test as base, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { isCoverageEnabled, startCoverage, stopCoverage } from '../coverage';
import { generateUsername } from '../helpers/utils';
import { RotkiApp } from '../pages/rotki-app';

/**
 * Shared test context that is initialized once per test.describe.serial block.
 */
export interface SharedTestContext {
  sharedContext: BrowserContext;
  sharedPage: Page;
  sharedRequest: APIRequestContext;
  app: RotkiApp;
  username: string;
}

/**
 * Options for creating a logged-in test context.
 */
export interface LoginOptions {
  disableModules?: boolean;
}

/**
 * Creates a shared test context with a logged-in user.
 * Use this in beforeAll to set up shared state for serial tests.
 *
 * @example
 * ```ts
 * let ctx: SharedTestContext;
 *
 * test.beforeAll(async ({ browser, request }) => {
 *   ctx = await createLoggedInContext(browser, request);
 * });
 *
 * test.afterAll(async () => {
 *   await cleanupContext(ctx);
 * });
 *
 * test('my test', async () => {
 *   const { sharedPage, app } = ctx;
 *   // use sharedPage and app
 * });
 * ```
 */
export async function createLoggedInContext(
  browser: Browser,
  request: APIRequestContext,
  options: LoginOptions = {},
): Promise<SharedTestContext> {
  const username = generateUsername();

  // Create shared browser context and page
  const sharedContext = await browser.newContext();
  const sharedPage = await sharedContext.newPage();

  // Start coverage collection if enabled
  if (isCoverageEnabled()) {
    await startCoverage(sharedPage);
  }

  // Login once for all tests
  const app = new RotkiApp(sharedPage, request);
  await app.fasterLogin(username, '1234', options.disableModules ?? false);

  return {
    sharedContext,
    sharedPage,
    sharedRequest: request,
    app,
    username,
  };
}

/**
 * Cleans up a shared test context.
 * Use this in afterAll to clean up after serial tests.
 */
export async function cleanupContext(ctx: SharedTestContext | undefined): Promise<void> {
  if (!ctx)
    return;

  const { sharedContext, sharedPage } = ctx;

  // Stop coverage collection if enabled
  if (isCoverageEnabled() && sharedPage) {
    await stopCoverage(sharedPage);
  }

  await sharedContext?.close();
}

/**
 * Extended test fixture with shared context support.
 * Re-exports the base test for consistency.
 */
export { base as test };
