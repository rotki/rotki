import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { LatestPricePage } from '../../pages/price-manager-page';
import { RotkiApp } from '../../pages/rotki-app';

/**
 * Back must dismiss what is covering the page before it leaves the page.
 *
 * No dialog is a history entry of its own, so before the overlay stack a back gesture
 * popped the entry underneath and navigated away with the dialog still open - from the
 * history events page mid-way through bridge matching, that landed the user on whatever
 * unrelated route they had visited earlier in the session.
 *
 * Driven here through the price manager because its add dialog is a `BigDialog`, the
 * wrapper 28 call sites share, and its dirty-form prompt is the case where getting this
 * wrong destroys the user's work rather than merely annoying them.
 */
test.describe('back navigation', () => {
  test.describe.serial('with an overlay open', () => {
    let ctx: SharedTestContext;
    let page: LatestPricePage;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request, { disableModules: true });
      page = new LatestPricePage(ctx.sharedPage);
      // A route to come back to, so "did not navigate" and "navigated" are distinguishable.
      await RotkiApp.navigateTo(ctx.sharedPage, 'accounts');
      await page.visit();
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('closes the dialog and stays on the page', async () => {
      const shared = ctx.sharedPage;
      const dialog = shared.locator('[data-testid=bottom-dialog]');
      await page.openAddDialog();
      const url = shared.url();

      await shared.goBack();

      await dialog.waitFor({ state: 'detached' });
      expect(shared.url()).toBe(url);
    });

    test('leaves the page once nothing is open, through the entry the aborted pop kept', async () => {
      const shared = ctx.sharedPage;
      await shared.goBack();

      await expect(shared).toHaveURL(/#\/accounts/);
    });

    test('closes the action centre and stays on the page', async () => {
      const shared = ctx.sharedPage;
      const menu = shared.getByRole('menu');
      await shared.getByTestId('actions-center-button').click();
      await expect(menu).toBeVisible();
      const url = shared.url();

      await shared.goBack();

      await expect(menu).toBeHidden();
      expect(shared.url()).toBe(url);
    });

    test('raises the discard prompt instead of leaving a dirty form', async () => {
      const shared = ctx.sharedPage;
      await page.visit();
      await page.openAddDialog();
      const dialog = shared.locator('[data-testid=bottom-dialog]');
      await shared.getByTestId('latest-price-value').locator('input').fill('42');
      const url = shared.url();

      await shared.goBack();

      // The form is still up, and the prompt is now the layer back is talking to.
      await expect(shared.locator('[data-testid=confirm-dialog]')).toBeVisible();
      await expect(dialog).toBeVisible();
      expect(shared.url()).toBe(url);
    });

    test('keeps the form when the discard prompt is declined', async () => {
      const shared = ctx.sharedPage;
      const confirmPrompt = shared.locator('[data-testid=confirm-dialog]');
      const dialog = shared.locator('[data-testid=bottom-dialog]');
      const url = shared.url();

      await confirmPrompt.getByTestId('button-cancel').click();
      await confirmPrompt.waitFor({ state: 'detached' });

      await shared.goBack();

      await expect(confirmPrompt).toBeVisible();
      await expect(dialog).toBeVisible();
      expect(shared.url()).toBe(url);
    });

    test('declines the discard prompt itself when back is pressed on it', async () => {
      const shared = ctx.sharedPage;
      const confirmPrompt = shared.locator('[data-testid=confirm-dialog]');
      const dialog = shared.locator('[data-testid=bottom-dialog]');
      const url = shared.url();
      await expect(confirmPrompt).toBeVisible();

      await shared.goBack();

      await confirmPrompt.waitFor({ state: 'detached' });
      await expect(dialog).toBeVisible();
      await expect(shared.getByTestId('latest-price-value').locator('input')).toHaveValue('42');
      expect(shared.url()).toBe(url);
    });
  });
});
