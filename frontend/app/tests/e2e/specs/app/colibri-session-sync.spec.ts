import { type APIRequestContext, type BrowserContext, expect, type Page, request } from '@playwright/test';
import { backendUrl, colibriUrl } from '../../../../playwright.config';
import { isCoverageEnabled, startCoverage, stopCoverage } from '../../coverage';
import { test } from '../../fixtures/test-fixtures';
import { TEST_TIMEOUT_STANDARD } from '../../helpers/constants';
import { generateUsername } from '../../helpers/utils';
import { RotkiApp } from '../../pages/rotki-app';

// Core and colibri each hold their own view of the logged-in user, and colibri answers 400 to
// both of its own no-ops: locking while it holds nothing, and unlocking while it holds
// anything. Either one used to abort the flow that wraps it, stranding the app half-unlocked —
// logged into core with colibri locked, which is unrecoverable without restarting the backend.
//
// These drive the real UI against a real colibri, putting it into each state out of band first,
// because nothing in the app can produce them on demand.
test.describe.serial('colibri session sync', () => {
  test.setTimeout(TEST_TIMEOUT_STANDARD);

  let username: string;
  let sharedContext: BrowserContext;
  let sharedPage: Page;
  let apiContext: APIRequestContext;
  let app: RotkiApp;

  test.beforeAll(async ({ browser }) => {
    username = generateUsername();
    sharedContext = await browser.newContext();
    sharedPage = await sharedContext.newPage();

    if (isCoverageEnabled())
      await startCoverage(sharedPage);

    apiContext = await request.newContext();
    app = new RotkiApp(sharedPage, apiContext);
  });

  test.afterAll(async () => {
    if (isCoverageEnabled() && sharedPage)
      await stopCoverage(sharedPage);

    await apiContext?.dispose();
    await sharedContext?.close();
  });

  test('logs out of core when colibri holds no database', async () => {
    await app.createAccount(username);

    // Lock colibri behind the app's back, which is where a resumed session leaves it.
    const locked = await apiContext.post(`${colibriUrl}/user/logout`, { failOnStatusCode: false });
    expect(locked.status()).toBe(200);

    // Negative control: prove colibri really is locked now, so the logout below is exercising
    // the failing call rather than a colibri that would have answered 200 anyway.
    const alreadyLocked = await apiContext.post(`${colibriUrl}/user/logout`, { failOnStatusCode: false });
    expect(alreadyLocked.status()).toBe(400);
    expect((await alreadyLocked.json()).message).toBe('DB not unlocked');

    // Logout locks colibri before it logs out of core, so that 400 used to abort the whole
    // thing: core kept the session and the UI sat on "Logout failed". `logout` waits for the
    // login form, so it fails here if that happens again.
    await app.logout();

    const users = await (await apiContext.get(`${backendUrl}/api/1/users`)).json();
    expect(users.result[username]).toBe('loggedout');
  });

  test('logs in when colibri still holds a database from an earlier session', async () => {
    await app.login(username);

    // Log out of core only, leaving colibri's handle open — what a crash or a force-quit
    // leaves behind, since nothing then tells colibri to let go.
    await apiContext.patch(`${backendUrl}/api/1/users/${username}`, {
      data: { action: 'logout' },
      failOnStatusCode: false,
    });

    // Negative control: prove colibri is still holding one. This is itself a rejected unlock,
    // so it reads the state without changing it.
    const stillHeld = await apiContext.post(`${colibriUrl}/user`, {
      data: { username, password: '1234' },
      failOnStatusCode: false,
    });
    expect(stillHeld.status()).toBe(400);
    expect((await stillHeld.json()).message).toBe('The DB is already unlocked');

    // Logging in has to relock colibri and take it again, or the unlock is refused and the
    // login fails with core already logged in — after which the retry resumes and never
    // unlocks colibri at all.
    await app.visit();
    await app.login(username);

    // Colibri now serves this user rather than refusing every request.
    const ignored = await apiContext.get(`${colibriUrl}/assets/ignored`, { failOnStatusCode: false });
    expect(ignored.status()).toBe(200);

    await app.logout();
  });
});
