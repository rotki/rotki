import { expect } from '@playwright/test';
import { test } from '../../fixtures/test-fixtures';
import { mockLoginResult, submitLogin } from '../../helpers/mock-login';

// `test` comes from the fixtures module, which arms coverage on the `page` fixture.

/* The real login UI with the handshake intercepted, covering the response-to-error mapping the
   unit tests stub. These backend states are impractical to provoke against a real backend. */
test.describe('login error flows', () => {
  test('surfaces the premium sync-conflict alert when the login task reports a conflict', async ({ page }) => {
    await mockLoginResult(page, 'sync-conflict');
    await page.goto('/#/user/login?skip_update=1');
    await submitLogin(page);
    await expect(page.getByText('Sync conflict detected')).toBeVisible();
  });

  test('surfaces the incomplete-upgrade alert when the login task reports an incomplete upgrade', async ({ page }) => {
    await mockLoginResult(page, 'incomplete-upgrade');
    await page.goto('/#/user/login?skip_update=1');
    await submitLogin(page);
    await expect(page.getByText('Incomplete database upgrade detected')).toBeVisible();
  });

  test('shows a wrong-password error on the password field', async ({ page }) => {
    await mockLoginResult(page, 'wrong-password');
    await page.goto('/#/user/login?skip_update=1');
    await submitLogin(page);
    await expect(page.getByText('Wrong password given for user alice')).toBeVisible();
  });
});
