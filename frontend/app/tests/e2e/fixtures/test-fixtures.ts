import path from 'node:path';
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
   * sits on "Unlock account" — a failure that only shows up once the spec runs after others.
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
 * Set by the auto fixture below whenever a test in the current file does not end in its
 * expected state, and cleared when a suite builds its context. `retain-on-failure` is a
 * per-test decision Playwright can only make for contexts it owns; a shared context spans the
 * whole file, so the file is the smallest unit we can decide on.
 */
let suiteHadFailure = false;

/**
 * The directory Playwright should record this suite's video into, or undefined when video is
 * off for the run.
 *
 * `use.video` is only applied to contexts Playwright builds itself for the `page`/`context`
 * fixtures. These suites build their own context in beforeAll so it can outlive a single
 * test, which silently opted every one of them out of video capture: the setting looked
 * repo-wide but only ever covered the specs driving the built-in fixture. Read the resolved
 * project setting and pass `recordVideo` by hand so the config means what it reads like.
 */
function videoRecordingDir(): string | undefined {
  const info = test.info();
  const video = info.project.use.video;
  const mode = typeof video === 'string' ? video : video?.mode;

  if (!mode || mode === 'off')
    return undefined;

  return path.join(info.project.outputDir, 'videos');
}

/**
 * Keeps the suite's video only when it is worth keeping, mirroring what `retain-on-failure`
 * does for fixture-owned contexts. Named after the spec file, since one video now covers the
 * whole file rather than a single test.
 */
async function retainSuiteVideo(sharedPage: Page): Promise<void> {
  const video = sharedPage.video();
  if (!video)
    return;

  const mode = test.info().project.use.video;
  const keepAlways = (typeof mode === 'string' ? mode : mode?.mode) === 'on';

  if (!keepAlways && !suiteHadFailure) {
    await video.delete();
    return;
  }

  const specName = path.basename(test.info().file).replace(/\.spec\.ts$/, '');
  const target = path.join(path.dirname(await video.path()), `${specName}.webm`);

  // saveAs waits for the recording to be fully written, which a plain rename would not.
  await video.saveAs(target);
  await video.delete();
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

  suiteHadFailure = false;

  const recordVideoDir = videoRecordingDir();
  const sharedContext = await browser.newContext(recordVideoDir ? { recordVideo: { dir: recordVideoDir } } : {});
  const sharedPage = await sharedContext.newPage();

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

  await saveMockRpcCassette();

  if (isCoverageEnabled() && sharedPage) {
    await stopCoverage(sharedPage);
  }

  await sharedContext?.close();

  // Only after close: the recording is not complete until the context that owns it is gone.
  if (sharedPage) {
    await retainSuiteVideo(sharedPage);
  }
}

/**
 * The base test with coverage armed on Playwright's own `page` fixture.
 *
 * A spec that drives `page` directly rather than building a context gets no coverage otherwise:
 * the arming lives in `createLoggedInContext`, which such a spec never calls. Overriding the
 * fixture here means a spec only has to import `test` from this module to be counted, and a spec
 * that does not touch `page` never instantiates it, so this costs those nothing.
 */
export const test = base.extend<{ trackSuiteFailures: void }>({
  page: async ({ page }: { page: Page }, use: (page: Page) => Promise<void>): Promise<void> => {
    if (isCoverageEnabled())
      await startCoverage(page);

    await use(page);

    if (isCoverageEnabled())
      await stopCoverage(page);
  },

  /**
   * Records whether anything in the file failed, so `cleanupContext` can decide in afterAll
   * whether the suite's video is worth keeping. Automatic because a spec cannot opt into it:
   * the tests that most need the video are the ones failing before they reach any fixture.
   */
  trackSuiteFailures: [async ({}, use: () => Promise<void>, testInfo): Promise<void> => {
    await use();

    if (testInfo.status !== testInfo.expectedStatus)
      suiteHadFailure = true;
  }, { auto: true }],
});
