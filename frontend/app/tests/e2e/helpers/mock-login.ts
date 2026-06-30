import type { Page, Route } from '@playwright/test';
import { TIMEOUT_SHORT } from './constants';

export type LoginResult = 'sync-conflict' | 'incomplete-upgrade' | 'wrong-password';

async function fulfillJson(route: Route, result: unknown, status = 200): Promise<void> {
  await route.fulfill({
    body: JSON.stringify({ message: '', result }),
    contentType: 'application/json',
    status,
  });
}

// The login task outcome. statusCode 300 with a payload => SyncConflictError; with an
// empty result => IncompleteUpgradeError (modules/core/tasks/use-task-api.ts).
function loginTaskOutcome(kind: LoginResult): unknown {
  if (kind === 'wrong-password') {
    // a plain task failure: null result + a message the login form routes to the password field
    return { outcome: { message: 'Wrong password given for user alice', result: null }, status: 'completed' };
  }
  if (kind === 'incomplete-upgrade') {
    return {
      outcome: { message: 'Incomplete database upgrade detected', result: {} },
      status: 'completed',
      status_code: 300,
    };
  }
  return {
    outcome: {
      message: 'Sync conflict detected',
      result: { local_last_modified: 100, remote_last_modified: 200 },
    },
    status: 'completed',
    status_code: 300,
  };
}

/**
 * Intercepts just the login handshake so the unlock flow resolves to a specific backend
 * state that a real backend can't easily produce. Everything else falls through to the
 * real backend via `route.continue()` (same selective-mock convention as
 * `pages/api-keys-page.ts`). Pass `?skip_update=1` in the URL to skip the asset-update check.
 */
export async function mockLoginResult(page: Page, kind: LoginResult, username = 'alice'): Promise<void> {
  await page.route('**/api/1/users', async (route) => {
    if (route.request().method() === 'GET')
      await fulfillJson(route, { [username]: 'loggedout' });
    else
      await route.continue();
  });

  await page.route('**/api/1/users/*', async (route) => {
    if (route.request().method() === 'POST')
      await fulfillJson(route, { task_id: 1 });
    else
      await route.continue();
  });

  await page.route('**/api/1/tasks', async (route) => {
    if (route.request().method() === 'GET')
      await fulfillJson(route, { completed: [1], pending: [] });
    else
      await route.continue();
  });

  await page.route('**/api/1/tasks/*', async route => fulfillJson(route, loginTaskOutcome(kind)));
}

/**
 * Fills the login form and submits, handling both the autocomplete username field (normal
 * runs) and the plain field (`VITE_TEST=true`). Does NOT wait for a successful login — the
 * callers assert on an error alert instead.
 */
export async function submitLogin(page: Page, username = 'alice', password = 'a-password'): Promise<void> {
  const usernameField = page.locator('[data-cy=username-input]');
  const usernameInput = usernameField.locator('input');
  await usernameInput.waitFor({ state: 'visible' });

  const activator = usernameField.locator('[data-id=activator]');
  if (await activator.count() > 0) {
    await activator.click();
    const menu = page.locator('[role=menu]');
    await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
    await usernameInput.fill(username);
    const option = menu.getByText(username, { exact: true });
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
    await option.click();
  }
  else {
    await usernameInput.fill(username);
  }

  await page.locator('[data-cy=password-input] input').fill(password);
  await page.locator('[data-cy=login-submit]').click();
}
