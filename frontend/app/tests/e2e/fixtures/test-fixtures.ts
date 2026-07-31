import { type APIRequestContext, test as base, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { isCoverageEnabled, startCoverage, stopCoverage } from '../coverage';
import { apiCreateAccount, apiDisableModules, apiLogout } from '../helpers/api';
import { apiConfigureRpcMocks, saveMockRpcCassette } from '../helpers/rpc-mock';
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
  /**
   * Name of the RPC mock cassette to use for this test suite.
   * Each test suite should use a unique name to avoid collisions.
   * If not provided, mock RPC will not be configured.
   */
  rpcMockCassette?: string;
  /**
   * Backend blockchain identifiers (e.g. 'ETH', 'SOLANA') that should be
   * routed through the mock RPC server. Only used when `rpcMockCassette` is set.
   * Defaults to ['ETH'].
   */
  rpcMockChains?: string[];
  /**
   * Logs in through the form instead of `fasterLogin`, which authenticates over the API first.
   * With the backend already holding that session the form submit does not take and the suite
   * sits on "Unlock account" - a failure that only shows up once the spec runs after others.
   *
   * Implied by `seed`, which needs the account created and released before login anyway.
   */
  formLogin?: boolean;
  /**
   * Writes fixture data straight into the user database.
   *
   * The callback runs after the account is created and logged back out, so nothing holds the
   * database open while it writes. The backend does not reliably see rows written into a user DB
   * it already has open, which is why the seam exists at all; anything the helpers in
   * `helpers/seed-db` write belongs here rather than after login.
   */
  seed?: (username: string) => void | Promise<void>;
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
 *   ctx = await createLoggedInContext(browser, request, {
 *     disableModules: true,
 *     rpcMockCassette: 'blockchain-balances',
 *   });
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

  if (options.seed || options.formLogin) {
    await apiLogout(request);
    await apiCreateAccount(request, username, '1234');

    // The mock has to be in place before login rather than after it: seeded tracked addresses make
    // the app query balances the moment it logs in, and against real nodes that query outlives the
    // test timeout.
    if (options.rpcMockCassette) {
      await apiConfigureRpcMocks(request, options.rpcMockCassette, options.rpcMockChains);
    }

    if (options.disableModules) {
      await apiDisableModules(request);
    }

    // Release the database so the seeding writes land somewhere the backend will read them back.
    await apiLogout(request);
    await options.seed?.(username);

    // Deliberately not `fasterLogin`, which authenticates over the API first: with the backend
    // already holding that session the form submit does not take and the suite sits on "Unlock
    // account". `checkGetPremiumButton` is the actual assertion that the app came up, since
    // `login()` assumes success when neither post-login dialog appears in time.
    await app.visit();
    await app.login(username, '1234');
    await app.checkGetPremiumButton();
  }
  else {
    await app.fasterLogin(username, '1234', options.disableModules ?? false);

    // Replace default RPC nodes with mock server (if cassette specified)
    if (options.rpcMockCassette) {
      await apiConfigureRpcMocks(request, options.rpcMockCassette, options.rpcMockChains);
    }
  }

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

  // Save mock RPC cassette if in record mode
  await saveMockRpcCassette();

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
